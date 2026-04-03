# Re-evaluation & Fix Plan: Ingestion Edge Cases

**Original Report:** `code-reviewer-260227-1721-ingestion-edge-cases.md` (2026-02-27)
**Re-evaluated:** 2026-04-03
**Scope:** 6 edge cases across ingestion pipeline

---

## Re-evaluation Summary

| # | Edge Case | Original Status | Current Status | Verdict |
|---|-----------|----------------|----------------|---------|
| 1 | Cookie lock orphaned .tmp | ⚠️ Partial | ⚠️ Partial | **DEFER** — Low-frequency, self-healing on restart |
| 2 | Session expiry mid-paginated fetch | ⚠️ Partial | ⚠️ Partial | **FIX** — Single retry after refresh, no error guard |
| 3 | Empty page mid-pagination | ⚠️ Partial | ⚠️ Partial | **FIX** — Page skip on exception is silent data loss |
| 4 | Rate limit 429 not handled | ❌ Unhandled | ❌ Unhandled | **FIX** — Will exhaust retries under throttle |
| 5 | Pipeline state partial load | ⚠️ Partial | ⚠️ Partial | **DEFER** — dlt append is idempotent-ish, dedup downstream |
| 6a | GSheet marketing_spend bugs | ⚠️ Partial | ⚠️ Partial | **FIX** — `source_id` "nan" cast + hardcoded year + `campaign_id` KeyError |
| 6b | GSheet targets column checks | ⚠️ Partial | ⚠️ Partial | **LOW** — `_validate_rows()` covers most cases already |

### What changed since Feb 27?

**Nothing.** All 6 findings remain in the same state. No code changes addressed these issues.

### What to defer and why

- **#1 Cookie lock:** The orphaned `.tmp` risk is real but low-impact (forces re-login, ~30s delay). The fix (per-process temp file) adds complexity for a scenario that happens only on hard crash. Defer.
- **#5 Pipeline state:** dlt's append disposition means partial loads create duplicate envelopes, not data loss. Downstream dbt `stg_` models already deduplicate by `entity_id + payload_hash`. The `--full-refresh` flag is the manual recovery path. The `--limit` no-op is a nice-to-have. Defer.
- **#6b Targets columns:** `_validate_rows()` already validates `cycle_start_date`, `metric_code`, `target_value`, `cycle_type`, `repeat_until`, `staff_email`. The remaining gap (no schema-level check against downstream dbt expectations) is a schema contract issue better solved by dbt tests, not ingestion-side validation. Low priority.

---

## Fix Plan

### Phase 1: GSheet Marketing Spend — Critical Bugs (Quick Wins)

**File:** `ingestion/src/gsheet_marketing_spend.py`
**Priority:** HIGH — Active data corruption bugs

#### 1.1 Fix `source_id` NaN → "nan" string cast (line 158)

**Problem:** `df['source_id'].astype(str)` converts NaN to literal string `"nan"`, corrupting FK joins.

**Fix:**
```python
# Before: df['source_id'] = df['source_id'].astype(str)
# After:
df['source_id'] = df['source_id'].where(df['source_id'].notna()).astype('object')
```

Or more explicit: only cast non-null values to string, leave NaN as NaN (parquet handles null natively).

#### 1.2 Fix hardcoded year 2026 in `clean_date` (line 129)

**Problem:** `return f"{val}/2026"` will break on 2027-01-01.

**Fix:**
```python
# Before: return f"{val}/2026"
# After:
return f"{val}/{datetime.now().year}"
```

#### 1.3 Guard `campaign_id` in `cols_to_save` (line 176)

**Problem:** `cols_to_save` includes `campaign_id` but it's not in `required_cols` and may not exist in the DataFrame. This causes a `KeyError` crash.

**Fix:** Filter `cols_to_save` to only columns that exist:
```python
cols_to_save = ['date', 'spend_code', 'source_id', 'location_id', 'campaign_id', 'spend_amount', 'clicks', 'impressions', 'ingest_method', 'year', 'month']
cols_to_save = [c for c in cols_to_save if c in group.columns]
```

---

### Phase 2: Page Skip on Exception — Silent Data Loss

**Files:** `ingestion/src/sapo/orders.py`, `customers.py`, `accounts.py`
**Priority:** HIGH — Transient error silently skips a page of data

#### 2.1 Retry same page on exception instead of incrementing

**Problem (orders.py lines 257-263, customers.py 241-247, accounts.py 203-208):**
```python
except Exception as e:
    ...
    page += 1  # ← Skips failed page's data!
```

**Fix:** Remove `page += 1` from the exception handler. The `consecutive_errors >= MAX_ERRORS` guard already prevents infinite retry loops. On error, the next iteration retries the same page.

```python
except Exception as e:
    print(f"❌ Error at page {page}: {e}")
    consecutive_errors += 1
    if consecutive_errors >= MAX_ERRORS:
        print("Too many errors. Stopping.")
        break
    # Do NOT increment page — retry the same page
```

---

### Phase 3: Rate Limit 429 Handling

**Files:** `ingestion/src/sapo/orders.py`, `customers.py`, `accounts.py`
**Priority:** HIGH — Pipeline exhausts retries in <30s under throttle

#### 3.1 Add 429 detection before `raise_for_status()`

Add 429 handling in each `fetch_page_with_retry` function, after the 401/403 block and before `raise_for_status()`:

```python
if response.status_code == 429:
    retry_after = int(response.headers.get('Retry-After', 60))
    print(f"⏳ Rate limited (429). Waiting {retry_after}s...")
    import time
    time.sleep(retry_after)
    response = current_session.get(url, params=params, timeout=30)
```

This handles 429 inline with a single retry respecting `Retry-After`. If the second attempt also fails, `raise_for_status()` triggers tenacity's exponential backoff as before — but now with a proper cooldown.

**Alternative (extract to shared utility):** Since all 3 files have identical `fetch_page_with_retry` logic, consider extracting to a shared function in `client.py` or a new `ingestion/src/sapo/fetch_utils.py`. However, per YAGNI, the inline fix in each file is simpler and avoids refactoring scope creep.

---

### Phase 4: Session Refresh Error Guard (Optional)

**Files:** Same 3 files
**Priority:** MEDIUM — Confusing logs, not data loss

#### 4.1 Guard the post-refresh response

After `client.refresh_session(current_session)`, check if the retry also fails:

```python
if response.status_code == 401 or response.status_code == 403:
    print("🔄 Session expired, refreshing cookies...")
    client.refresh_session(current_session)
    response = current_session.get(url, params=params, timeout=30)
    if response.status_code in (401, 403):
        raise requests.HTTPError(f"Auth failed after refresh: {response.status_code}", response=response)
```

This prevents tenacity from re-triggering `refresh_session` 3 more times when credentials are wrong.

---

## Implementation Order

1. **Phase 1** (gsheet_marketing_spend.py) — 3 quick fixes, highest ROI
2. **Phase 2** (page skip) — 3 files, same 2-line change each
3. **Phase 3** (429 handling) — 3 files, same ~5-line block each
4. **Phase 4** (session guard) — Optional, nice-to-have

**Estimated total changes:** ~40 lines across 4 files.

---

## TODO Checklist

- [x] **1.1** Fix `source_id` NaN→"nan" in `gsheet_marketing_spend.py:158` ✅ 2026-04-03
- [x] **1.2** Fix hardcoded year 2026 in `gsheet_marketing_spend.py:129` ✅ 2026-04-03
- [x] **1.3** Guard `campaign_id` KeyError in `gsheet_marketing_spend.py:176-181` ✅ 2026-04-03
- [x] **2.1** Remove `page += 1` from exception handler in `orders.py:263` ✅ 2026-04-03
- [x] **2.2** Remove `page += 1` from exception handler in `customers.py:247` ✅ 2026-04-03
- [x] **2.3** Remove `page += 1` from exception handler in `accounts.py:208` ✅ 2026-04-03
- [x] **3.1** Add 429 handling in `orders.py` `fetch_page_with_retry` ✅ 2026-04-03
- [x] **3.2** Add 429 handling in `customers.py` `fetch_page_with_retry` ✅ 2026-04-03
- [x] **3.3** Add 429 handling in `accounts.py` `fetch_page_with_retry` ✅ 2026-04-03
- [x] **4.1** Guard post-refresh auth failure in all 3 files ✅ 2026-04-03

---

## Deferred Items (Backlog)

| Item | File | Reason to Defer |
|------|------|----------------|
| Per-process .tmp file | shared_cookie_manager.py | Low-frequency crash scenario, self-healing |
| Pipeline state rollback | pipeline_runner.py | dlt append + downstream dedup handles it |
| `--limit` flag implementation | pipeline_runner.py | CLI convenience, not data integrity |
| Schema contract validation | gsheet_targets.py | Better solved by dbt tests |

---

## Unresolved Questions

1. **Does Sapo API return `Retry-After` header on 429?** If not, the hardcoded 60s fallback is conservative but safe. Could test by intentionally triggering rate limit.
2. **Is `campaign_id` expected in the Google Sheet?** If yes, add to `required_cols`. If optional, the `cols_to_save` filter handles it. Need to check the actual sheet schema.
3. **Accounts API sort order** — still unknown. The full-scan behavior is acceptable given small dataset (<100 accounts).

# Code Review: Ingestion Data Integrity & Error Handling

**Date:** 2026-02-27
**Scope:** 6 targeted edge cases across ingestion pipeline files
**Reviewer:** code-reviewer agent

---

## Edge Case Findings

---

### 1. Cookie Lock File Not Released on Crash

**File:** `ingestion/src/utils/shared_cookie_manager.py`

**Status: ⚠️ Partial**

**Evidence:**

The write path uses try/finally correctly inside `_write_cookie_file` (lines 229–235):
```python
try:
    self._acquire_lock(f)
    json.dump(data, f, indent=2)
    f.flush()
    os.fsync(f.fileno())
finally:
    self._release_lock(f)
```

However, this lock is on the `.tmp` file, not on the final `.json` file. The `.tmp` file itself has no `with`-style context manager guard at the outer `open(temp_file, 'w') as f` level — if the OS kills the process after `open()` but before the `try` block, the lock is never acquired and the temp file is left as a 0-byte orphan.

More importantly, the **read path** (`_read_cookie_file`, lines 187–207) explicitly skips locking:
```python
# Simplified: Just read. If we get partial read, json load handles error.
```
This is fine only because of the atomic rename strategy, but the comment above it also states the rename can fail on Windows (lines 239–243) via a race condition, meaning a partial `.tmp` can survive.

For msvcrt (Windows): `msvcrt.LK_NBLCK` locks bytes, not the entire file handle, and it is **not automatically released on process crash** — the OS releases it only when the file descriptor is closed. Since Python's GC will close FDs on process exit, this is generally safe for clean exits. For hard crash (SIGKILL, power loss), the lock is released by the OS when the process dies, so the file lock itself is not permanently stuck.

The real residual risk is a stale **orphaned `.tmp` file** left behind if the process crashes after `open(temp_file, 'w')` but before `temp_file.replace(self.cookie_file)`. The next run will attempt to rename a possibly incomplete `.tmp` over the good `.json`.

**Impact: Medium** — Orphaned `.tmp` can corrupt the cookie file on the next run, forcing a full re-login. Not data-loss level, but can cause an unnecessary Playwright browser launch during a time-sensitive pipeline run.

---

### 2. Session Expiry Mid-Paginated Fetch

**Files:** `orders.py`, `customers.py`, `accounts.py`

**Status: ⚠️ Partial**

**Evidence (all three files follow the same pattern):**

```python
# orders.py lines 162–170, customers.py lines 158–166, accounts.py lines 125–128
if response.status_code == 401 or response.status_code == 403:
    print("🔄 Session expired, refreshing cookies...")
    client.refresh_session(current_session)
    response = current_session.get(url, params=params, timeout=30)

response.raise_for_status()
```

Session refresh logic exists and is triggered on 401/403. The `refresh_session` method in `client.py` (lines 92–100) calls `login_and_save_cookies()` and updates the session in-place.

**Issues:**

1. After the refresh, the **retry is only one attempt** with no further error check before `raise_for_status()`. If the refresh itself fails (network error, bad credentials), the exception from `login_and_save_cookies()` will bubble up unhandled within `fetch_page_with_retry`, bypassing tenacity's retry logic entirely — because tenacity only retries `requests.RequestException`, not arbitrary `Exception` from the login step.

2. The 401/403 handler fires **inside** `fetch_page_with_retry`, which is decorated with `@retry`. The manual retry-after-refresh is **not** counted by tenacity, meaning a 401 on page 50 during pagination correctly triggers a refresh, but if the refresh still results in a 401 (e.g., wrong password), it raises `HTTPError` via `raise_for_status()`, which **does not match** `retry_if_exception_type(requests.RequestException)` — `HTTPError` is a subclass of `requests.RequestException`, so it actually IS retried. This creates up to 3 additional logins in quick succession, which is wasteful but not catastrophic.

3. The `session` object is captured once before the loop (e.g., `orders.py` line 136: `session = client.session`). The `refresh_session` call mutates this object in-place (clears and updates cookies), so subsequent pages will use the refreshed cookies. This part is handled correctly.

**Impact: High** — If a session expires mid-pagination, the single in-function retry is reasonable, but the error propagation path is not clean and can produce confusing log output with repeated login attempts.

---

### 3. Empty Page Mid-Pagination (Premature Stop)

**Files:** `orders.py`, `customers.py`, `accounts.py`

**Status: ⚠️ Partial**

**Evidence:**

All three files treat any empty page as a terminal signal:
```python
# orders.py line 183-185, customers.py line 179-181, accounts.py line 141-143
if not orders_data:
    print(f"📭 Page {page}: Empty")
    break
```

**Issues:**

1. **Transient empty page is fatal.** If the API returns an empty list due to a transient server-side issue (e.g., timeout on the server's database query, which some APIs signal as `{"orders": []}` rather than a 5xx), the entire paginated fetch stops at that page. There is no retry for a "got empty but expected data" condition.

2. **accounts.py has no `consecutive_old_items` guard** — it reads all pages regardless and stops only on empty or `max_pages`. For a small dataset this is fine, but the comment in the code (lines 195–199) acknowledges the sort order uncertainty. If the API returns ASC order and the incremental check `item_modified_on > last_value` yields zero matches across an entire page, it does not stop — it continues to `max_pages`. This is correct behavior but means accounts does a full table scan every run.

3. **Off-by-one risk in orders/customers:** The loop condition is `while page <= max_pages`. On exactly `max_pages` pages with full data, the loop terminates normally after the last page is read but without yielding the next page (there is none). No off-by-one here. However, `page` is incremented even after an error (line 263 in `orders.py`), so an error on page N causes the pipeline to skip page N and try page N+1 — this silently skips data on transient errors.

**Impact: High** — Silent data skipping on transient API errors (error increments page without yield). Transient empty-page treated as hard stop (medium risk for orders/customers, low for accounts).

---

### 4. Rate Limit HTTP Codes Not Fully Covered by Tenacity Retry

**Files:** `orders.py`, `customers.py`, `accounts.py`, `client.py`

**Status: ❌ Unhandled**

**Evidence:**

Tenacity configuration in all three source files is identical:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.RequestException)
)
```

`response.raise_for_status()` is called after the 401/403 manual refresh block. A **429 (Too Many Requests)** response will cause `raise_for_status()` to raise `requests.exceptions.HTTPError`, which IS a subclass of `requests.RequestException`.

So 429 IS retried by tenacity — but with a fixed `wait_exponential(min=2, max=10)`, not respecting the `Retry-After` header that most APIs return with a 429. The max backoff is 10 seconds, which may be insufficient if the API requires a 60-second cooldown.

**Specific gaps:**

- **429 with `Retry-After` header:** Ignored. The 10s max backoff may cause 3 rapid re-retries that all fail, exhausting the retry budget.
- **503 Service Unavailable / 502 Bad Gateway:** Retried (subclass of `HTTPError` → `RequestException`) but same 10s max cap.
- **`retry_if_exception_type(requests.RequestException)`** covers network errors, timeouts, and HTTP errors — this is correct and broad enough.
- **No `retry_if_result`** to handle cases where the API returns 200 with an error payload (e.g., `{"error": "rate limited"}`).

No special handling exists in `client.py` for rate limiting. There is no `Retry-After` parsing anywhere.

**Impact: High** — Under heavy load or API throttle, the pipeline will exhaust 3 attempts in under 30s and fail, rather than waiting the required cooldown period. Given `request_delay=0.5s` and `page_size=250`, a 1000-page run fires ~2 req/s, which can trigger Sapo's rate limiter.

---

### 5. Pipeline State Corruption After Partial Load

**File:** `ingestion/src/utils/pipeline_runner.py`

**Status: ⚠️ Partial**

**Evidence:**

The runner (lines 82–100) wraps `pipeline.run(source)` in a retry loop with up to 3 attempts and exponential backoff:
```python
for attempt in range(max_retries):
    try:
        source = source_factory(**source_args)
        info = pipeline.run(source)
        ...
        return info
    except Exception as e:
        ...
        if attempt < max_retries - 1:
            time.sleep(wait_time)
        else:
            raise e
```

**Issues:**

1. **No state rollback between retries.** dlt pipelines update their internal state (last incremental value, loaded file references) as data is loaded. If `pipeline.run()` partially loads data and then raises, the next `source_factory(**source_args)` call on retry will create a new source with the partially-advanced incremental state. This means the retry does not start from the same position — it starts from where it left off, which could be correct (idempotent append) or incorrect (if the failure was mid-batch and the batch was not committed).

2. **dlt filesystem destination behavior:** For the filesystem destination with parquet, dlt writes files to a staging area and then moves them atomically. If the process is killed mid-write, the staging files may be orphaned. dlt does not provide automatic staging cleanup; a subsequent run will not re-write those files unless `--full-refresh` is used.

3. **`--full-refresh` drops state before running** (line 65: `pipeline.drop()`). This is the explicit recovery path, but it requires manual intervention.

4. **The `--limit` flag** is parsed but the body is a `pass` (lines 69–76). The comment says "rely on caller to use args.limit". This means the limit CLI argument is silently ignored — not a corruption risk but a reliability gap.

**Impact: Medium** — dlt's append write disposition means partial loads accumulate duplicate envelopes rather than causing data loss. The deduplication burden is pushed downstream. A full refresh is the only clean recovery path, and it requires a manual flag.

---

### 6. Google Sheets Empty/Malformed Data

**Files:** `gsheet_marketing_spend.py`, `gsheet_targets.py`

**Status: ⚠️ Partial**

**Evidence:**

**gsheet_marketing_spend.py:**

- Empty spreadsheet: `pd.read_csv(csv_url)` on an empty sheet returns a DataFrame with only a header row. `len(df) == 0` — the script proceeds to `df.groupby(['year', 'month'])` which yields nothing, and the function exits silently with "Ingestion Complete." No rows written is not flagged as an error. **Handled** (silent success).

- Missing required columns: Checked explicitly at lines 93–96:
  ```python
  required_cols = ['date', 'spend_category', 'target_channel', 'spend_amount']
  missing_cols = [c for c in required_cols if c not in df.columns]
  if missing_cols:
      raise ValueError(f"Missing required columns: {missing_cols}")
  ```
  **Handled.**

- Null values in `spend_code` / `source_id`: Not dropped. Lines 115–121 print warnings but do **not** stop the pipeline. Rows with null `spend_code` will be written to parquet with a null `spend_code` column — downstream models may fail or silently produce incorrect results.

- `cols_to_save` references `campaign_id` (line 176) but `campaign_id` is not in `required_cols`. If the sheet lacks this column, the `group[cols_to_save]` select will raise a `KeyError` and the entire run fails. **Unhandled.**

- `source_id` cast to string on line 158: `df['source_id'] = df['source_id'].astype(str)`. If `source_id` is `None` (NaN), this becomes the string `"nan"`, which will corrupt foreign key joins downstream. **Unhandled.**

- Hardcoded year in `clean_date` (line 129): `return f"{val}/2026"` — will break on January 1, 2027.

**gsheet_targets.py:**

- Missing required columns: No explicit check. `pd.read_csv` succeeds, then `if 'setup_date' in df.columns:` gracefully handles the missing column (lines 40–53) by falling back to current date. All other columns are written as-is. If downstream models expect specific columns, silent schema drift will occur with no warning. **Partial.**

- Empty spreadsheet: `pd.read_csv` returns 0 rows, `groupby` yields nothing, silent success. **Handled** (same as marketing spend).

- Null values: No null validation on any column. NaN values in numeric or ID columns pass through to parquet silently. **Unhandled.**

- No validation that `df.to_parquet(file_path, ...)` (line 72) succeeds with the full schema expected by downstream dbt models.

**Impact: High** — Null `spend_code`/`source_id` silently written to parquet will cause incorrect aggregations in dbt marketing models without any pipeline-level error. The `"nan"` string cast for `source_id` is a silent data corruption bug. The hardcoded `2026` in `clean_date` is a time-bomb.

---

## Summary Table

| # | Edge Case | Status | Severity |
|---|-----------|--------|----------|
| 1 | Cookie lock not released on crash | ⚠️ Partial | Medium |
| 2 | Session expiry mid-paginated fetch | ⚠️ Partial | High |
| 3 | Empty page mid-pagination | ⚠️ Partial | High |
| 4 | Rate limit 429 not properly handled | ❌ Unhandled | High |
| 5 | Pipeline state corruption after partial load | ⚠️ Partial | Medium |
| 6 | Google Sheets empty/malformed data | ⚠️ Partial | High |

---

## Priority Fixes

1. **[High / Quick Win]** `gsheet_marketing_spend.py` line 158: Change `df['source_id'].astype(str)` to handle nulls before casting — e.g., `df['source_id'].where(df['source_id'].notna()).astype('object')` or add a `fillna` guard before cast. Also add `campaign_id` to `required_cols` or guard the `cols_to_save` selection.

2. **[High / Quick Win]** `gsheet_marketing_spend.py` line 129: Remove hardcoded `2026` year. Use `datetime.now().year` instead.

3. **[High]** All three sapo source files: Add `Retry-After` header parsing for 429 responses before calling `raise_for_status()`. At minimum, detect 429 and sleep for `int(response.headers.get('Retry-After', 60))` seconds before retrying.

4. **[High]** `orders.py`, `customers.py` lines 258–263 / 241–247: On `except Exception` inside the page loop, do **not** increment `page` — retry the same page. Currently, a transient error silently skips that page's data.

5. **[Medium]** `gsheet_targets.py`: Add explicit column presence checks for columns referenced by downstream dbt models to surface schema drift early.

6. **[Medium]** `shared_cookie_manager.py`: Use a per-process temp file (e.g., `self.cookie_file.with_suffix(f'.{os.getpid()}.tmp')`) to avoid multiple-process collision on the `.tmp` file.

---

## Unresolved Questions

1. Does the Sapo API return a `Retry-After` header with 429 responses? If not, what is the documented rate limit (req/s) for the accounts/orders/customers endpoints?
2. For `accounts.py`: is the API sort order confirmed as ID-ascending or modified-ascending? The comment acknowledges uncertainty (line 117). Without DESC sort by modified_on, the incremental strategy will always do a full table scan.
3. For `gsheet_targets.py`: what is the expected schema (column list) that downstream dbt models require? There is no validation against this schema.
4. Is `pipeline.drop()` (full refresh) the accepted recovery procedure for partial load failures, or is there an expectation that retries should be transparent to operators?

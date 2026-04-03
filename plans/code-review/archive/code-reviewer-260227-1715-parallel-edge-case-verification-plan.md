# Fix Plan: Remaining Edge Cases from Feb 2026 Review

**Date:** 2026-04-03
**Source:** `code-reviewer-260227-1715-parallel-edge-case-verification.md`
**Re-evaluation:** `plans/reports/code-reviewer-260403-1354-re-evaluation-feb-review.md`

---

## Status Summary

| Original | Fixed | Partially Fixed | Still Open | Corrected |
|----------|-------|-----------------|------------|-----------|
| 27       | 15    | 5               | 6          | P9 → FIXED |

**Note:** P9 (dim_products null overwrite) was marked STILL OPEN in re-evaluation but `dim_products.sql:29` already has `AND product_name IS NOT NULL`. Actual remaining = **11 items**.

---

## Phase 1 — Webhook Data Integrity (High Priority)

**Files:** `ingestion/src/sapo/webhook_consumer.py`

### 1.1 Move ACK after successful load (U7 + P18 combined fix)
**Problem:** `ids_to_ack` populated at line 104 (before validation), ACK at line 209 (before dlt load completes). Two issues:
- Invalid/unparseable messages silently deleted (P18)
- Load crash = permanent data loss (U7)

**Fix:**
- Move `ids_to_ack.append(msg_id)` from line 104 to after envelope construction (line 187, before `yield`)
- Refactor ACK out of the generator; ACK after `pipeline.run()` succeeds in the caller
- Store `ids_to_ack` on `dlt.state()` or return from source for caller to ACK

**Implementation:**
```python
# In webhook_dispatcher(): remove ids_to_ack from generator
# Instead, yield (envelope, msg_id) pairs or use dlt.current.source_state()

# In caller (pipeline_runner or wherever pipeline.run is called):
load_info = pipeline.run(source)
if load_info.has_failed_jobs:
    raise Exception("Load failed, not ACKing")
# ACK only on success
client.batch_ack(successfully_loaded_ids)
```

### 1.2 Surface batch_ack failures (U3)
**Problem:** `batch_ack()` catches exceptions internally (line 53-56), caller never knows.

**Fix:** Re-raise after logging, or return boolean. Let caller decide retry/alert.
```python
def batch_ack(self, message_ids: list) -> bool:
    ...
    except requests.exceptions.RequestException as e:
        print(f"Error acknowledging messages: {e}")
        raise  # Let caller handle
```

### 1.3 Webhook dedup: append → merge (U2)
**Problem:** `write_disposition="append"` ignores `primary_key` in dlt. Duplicate webhook events produce duplicate rows.
**Mitigation:** Downstream SQL dedup in `src_sapo_orders` handles this, so this is **low urgency** but wastes storage.

**Fix (optional):** Change to `write_disposition="merge"` at line 65-66.
**Risk:** Merge may be slower; verify dlt merge behavior with `entity_id` primary key on DuckDB destination.

---

## Phase 2 — D1 Queue Safety (Medium Priority)

**File:** `webhook_receiver/cloudflareD1/src/index.ts`

### 2.1 Add queue depth guard (U4)
**Problem:** `handleWebhook()` (line 155-159) does straight INSERT with no depth check. Burst traffic = unbounded D1 growth.

**Fix:** Add depth check before INSERT:
```typescript
// Before INSERT
const { results } = await env.DB.prepare(
    "SELECT COUNT(*) as cnt FROM webhooks WHERE status = 'NEW'"
).all();
const queueDepth = results[0]?.cnt ?? 0;
if (queueDepth > 10000) {  // configurable threshold
    return new Response("Queue full", { status: 503 });
}
```

**Trade-off:** Extra SELECT per webhook. Acceptable since webhook volume is low (Sapo). Can cache count if needed.

---

## Phase 3 — Ingestion Resilience (Medium Priority)

**Files:** `ingestion/src/sapo/orders.py`, `customers.py`, `accounts.py`

### 3.1 Empty page retry (P3)
**Problem:** Empty API response → immediate `break`. Transient empty page (API hiccup) stops entire pagination.

**Fix:** Retry once on empty page before breaking:
```python
if not orders_data:
    if empty_retries < 1:
        empty_retries += 1
        print(f"⚠️ Page {page}: Empty, retrying once...")
        time.sleep(2)
        continue
    print(f"📭 Page {page}: Empty after retry, stopping.")
    break
```

Apply to all 3 source files.

---

## Phase 4 — Serving Layer Safety (Low Priority)

### 4.1 Fail serving asset on dbt errors (P12)
**File:** `orchestration/assets/serving.py:57-62`

**Problem:** Detects dbt errors in stdout but still returns success `Output(value="Serving DB Updated")`.

**Fix:** Raise exception when errors detected (not just warnings):
```python
if warnings:
    for w in warnings:
        context.log.warning(f"⚠️ {w}")
    if any("error" in w.lower() for w in warnings):
        raise Exception(f"Serving DB generation halted: {'; '.join(warnings)}")
```

### 4.2 Connection leak in generate_serving_db.py (P17)
**File:** `scripts/provisioning/generate_serving_db.py:77-152`

**Problem:** `con.close()` at line 151 not in `try/finally`. Exception in for-loop leaks connection.

**Fix:** Wrap main loop in `try/finally`:
```python
con = None
try:
    con = duckdb.connect(SERVING_DB_PATH)
    ...
    for table_name in subdirs:
        ...
finally:
    if con:
        con.close()
```

---

## Deferred / Won't Fix

| Item | Reason |
|------|--------|
| P4 (partial load state) | Mitigated by 7-day lookback window. Inherent to dlt state management. |
| P15 (env-var path in SQL) | Path from environment, not user input. Risk ≈ 0. |
| P19 (Parquet GC TOCTOU) | Already has retry + catch. Practical risk near-zero given dbt cadence. |
| P20 (query_lake.py raw SQL) | Dev-only CLI tool, never exposed externally. Add read-only mode if concerned. |

---

## Implementation Order

```
Phase 1 (Webhook Integrity) ──→ Phase 2 (D1 Safety) ──→ Phase 3 (Ingestion) ──→ Phase 4 (Serving)
     [HIGH]                         [MEDIUM]                [MEDIUM]               [LOW]
```

**Estimated scope:** ~100 LOC changes across 6 files.

## Todo

- [x] Phase 1.1: Move ACK to post-load in webhook_consumer.py — **DEFERRED** → `deferred-260403-webhook-ack-after-load.md`
- [x] Phase 1.2: Surface batch_ack failures — **DONE** (`webhook_consumer.py:58` raises on error)
- [x] Phase 1.3: Evaluate append → merge (optional) — **DEFERRED** → `deferred-260403-webhook-ack-after-load.md`
- [x] Phase 2.1: Add D1 queue depth guard — **DONE** (`index.ts:152-157`)
- [x] Phase 3.1: Add empty page retry to orders/customers/accounts — **DONE** (all 3 files)
- [x] Phase 4.1: Fail serving asset on dbt errors — **DONE** (`serving.py:57-61`)
- [x] Phase 4.2: Fix connection leak in generate_serving_db.py — **DONE** (`generate_serving_db.py:150-152`)

## Unresolved Questions

1. Is at-most-once acceptable for webhook data, or must we guarantee at-least-once? (Determines Phase 1.1 urgency)
2. What D1 row limit should trigger 503? (Determines Phase 2.1 threshold)
3. Does Sapo API ever return legit empty pages mid-pagination? (Determines Phase 3.1 necessity)

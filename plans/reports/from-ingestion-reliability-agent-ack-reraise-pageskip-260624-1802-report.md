# Ingestion Reliability Fixes — 3 Verified Bugs
Date: 2026-06-24 | Agent: ingestion-reliability

---

## FIX 1 — Hug Webhook ACK-before-load (data loss)

**Files changed:**
- `ingestion/src/hug/hug_webhook_consumer.py`
- `ingestion/run_hug_webhook_consumer.py`

**Root cause:** `hug_event_dispatcher` collected `ids_to_ack` and called `client.batch_ack()` at the end of the generator body — which dlt exhausts during the *extract* phase (before `pipeline.run()` commits the load). A load-phase failure after extraction would ack messages that were never persisted.

**Before → After (consumer):**
- Removed `ids_to_ack` list and `client.batch_ack()` from the old `hug_event_dispatcher` generator.
- Added `build_hug_webhook_source(worker_url, poll_limit) → (source, pending_ack)` — mirrors `build_sapo_webhook_source()` exactly.
- Added `@dlt.source _hug_webhook_source_internal` and `@dlt.resource _hug_event_dispatcher_internal` that accept `client, pending` and append to `pending.ids` (never calls ack).
- Retained `hug_webhook_source` / `hug_event_dispatcher` as legacy at-most-once entry points (with warning docstring), so any existing test imports don't break.
- Imported `PendingAck` from `sapo.webhook_consumer`.

**Before → After (runner `run_hug_webhook_consumer.py`):**
```python
# BEFORE
source = hug_webhook_source(worker_url=worker_url, poll_limit=args.poll_limit)
info = pipeline.run(source, loader_file_format="parquet")

# AFTER
source, pending_ack = build_hug_webhook_source(worker_url=worker_url, poll_limit=args.poll_limit)
info = pipeline.run(source, loader_file_format="parquet")
pending_ack.ack()   # ACK only after successful load
```

If `pipeline.run()` raises, `pending_ack.ack()` is skipped — messages stay in D1 for re-delivery.

**py_compile:** OK

---

## FIX 2 — Batch pipelines swallow exceptions (silent green)

**Files changed:**
- `ingestion/src/sapo/orders.py` (line ~279)
- `ingestion/src/sapo/customers.py` (line ~268)

**Root cause:** After `consecutive_errors >= MAX_ERRORS`, code printed a message and `break`-ed the while loop. Generator returned cleanly → Dagster saw success with partial/zero rows.

**Before:**
```python
if consecutive_errors >= MAX_ERRORS:
    print("Too many errors. Stopping.")
    break
```

**After (both files):**
```python
if consecutive_errors >= MAX_ERRORS:
    raise RuntimeError(
        f"Aborting {pipeline} pipeline after {MAX_ERRORS} consecutive errors on page {page}."
    ) from e
```

`raise … from e` propagates the original exception as cause, surfaces the error chain in Dagster logs, and marks the asset FAILED. Partial rows already yielded are preserved (generator had already yielded before the terminal error).

**py_compile:** OK (both)

---

## FIX 3 — history_log page skip on transient error

**File changed:** `ingestion/src/sapo/history_log.py` (line ~501)

**Root cause:** The `except` block incremented `page` unconditionally after logging the error — even on transient failures. This permanently skipped that page's records. `orders.py` and `customers.py` correctly had a comment "Do NOT increment page — retry the same page"; `history_log.py` did not follow that pattern.

**Before:**
```python
except Exception as e:
    print(f"❌ Error at page {page}: {e}")
    consecutive_errors += 1
    if consecutive_errors >= MAX_ERRORS:
        print("Too many errors, giving up.")
        break
    page += 1   # ← BUG: skips failed page
```

**After:**
```python
except Exception as e:
    print(f"❌ Error at page {page}: {e}")
    consecutive_errors += 1
    if consecutive_errors >= MAX_ERRORS:
        raise RuntimeError(
            f"Aborting history_log pipeline after {MAX_ERRORS} consecutive errors on page {page}."
        ) from e
    # Do NOT increment page — retry the same page
```

Also applies FIX 2's re-raise to `history_log` — same terminal path, same silent-green risk.

**Infinite-loop risk:** No. `consecutive_errors` keeps incrementing on each retry of the same page. After `MAX_ERRORS` attempts, `RuntimeError` is raised and the generator terminates. Bounded.

**py_compile:** OK

---

## Summary

| Fix | File(s) | Change | py_compile |
|-----|---------|--------|-----------|
| 1 — Hug ACK-before-load | `hug_webhook_consumer.py`, `run_hug_webhook_consumer.py` | Added `build_hug_webhook_source()` + `PendingAck`; runner ACKs after `pipeline.run()` | OK |
| 2 — Silent green on MAX_ERRORS | `orders.py`, `customers.py` | `break` → `raise RuntimeError(...) from e` | OK |
| 3 — history_log page skip | `history_log.py` | Removed rogue `page += 1` in except; added re-raise on MAX_ERRORS | OK |

## Unresolved questions

- `ingestion/tests/test_hug_webhook_consumer.py` likely tests the old `hug_webhook_source` entry point — it will still pass (legacy path preserved), but new tests covering `build_hug_webhook_source` + ACK-after-load are not written here (out of scope per constraints).
- `pending_ack.ack()` in the runner is NOT inside a `finally` block — on pipeline failure it correctly skips ack, which is the desired at-least-once behavior. If the ack itself fails after a successful load, messages would be re-delivered (duplicate ingest, deduped by `primary_key=entity_id`). This is acceptable and mirrors the sapo pattern.

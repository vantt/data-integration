# Deferred: Webhook ACK After Load (U7 + U2)

**Date:** 2026-04-03
**Deferred from:** `plans/code-review/archive/code-reviewer-260227-1715-parallel-edge-case-verification-plan.md`
**Priority:** Medium

---

## U7 — ACK After Successful dlt Load

**File:** `ingestion/src/sapo/webhook_consumer.py`

**Problem:** `batch_ack()` is called at the end of the `webhook_dispatcher` generator (extraction phase). dlt runs extraction first, then load. If load crashes after extraction completes, messages are already ACK'd and deleted from D1 — permanent data loss.

**Current state (after P18 fix):** Invalid/unparseable messages no longer get ACK'd (P18 fixed). But all successfully-extracted messages still get ACK'd before load completes (U7 remains).

**Required fix:** Move ACK to after `pipeline.run()` succeeds in the caller.

**Options:**
1. Store `ids_to_ack` in `dlt.current.source_state()` and read+ACK in a post-load hook
2. Return `ids_to_ack` alongside the source and ACK in the pipeline runner after `load_info` is confirmed
3. Use a dlt `on_load_complete` callback if supported

**Caller location:** Find `pipeline.run(sapo_webhook_source(...))` in `orchestration/` or `ingestion/` pipeline runner scripts.

**Implementation sketch:**
```python
# In pipeline runner:
source = sapo_webhook_source(worker_url=..., source_system=...)
load_info = pipeline.run(source)

if load_info.has_failed_jobs:
    raise Exception("Load failed, not ACKing")

# ACK only on full success
client = CloudflareWorkerClient(worker_url)
client.batch_ack(ids_from_state_or_source)
```

**Blocker:** Requires finding where `pipeline.run()` is called and restructuring to pass `ids_to_ack` out of the generator context.

**Unresolved question:** Is at-most-once acceptable for webhook data, or must we guarantee at-least-once? (Determines urgency)

---

## U2 — Webhook Dedup: append → merge

**File:** `ingestion/src/sapo/webhook_consumer.py:65-66`

**Problem:** `write_disposition="append"` ignores `primary_key` in dlt. Duplicate webhook events (e.g. Sapo retries) produce duplicate rows in the envelope table. Downstream `src_sapo_orders` SQL dedup handles this so functional impact is low, but wastes storage.

**Fix:** Change `write_disposition="append"` to `write_disposition="merge"` on the `webhook_dispatcher` resource.

**Risk:** Merge is slower than append; verify dlt merge behavior with `entity_id` primary key on DuckDB/Delta destination before enabling.

**Verdict:** Optional. Fix only if storage becomes a concern or dedup complexity increases.

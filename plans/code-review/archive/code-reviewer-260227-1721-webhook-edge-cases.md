# Code Review: Webhook Pipeline Edge Cases
Date: 2026-02-27 | Reviewer: code-reviewer

---

## Edge Case Verification

### 1. HMAC Verification with Missing/Empty Signature Header
**File:** `webhook_receiver/cloudflareD1/src/index.ts`

**Status: ✅ Handled**

**Evidence:**
- `index.ts:86` — `request.headers.get(headerName)` returns `null` for missing headers. The `if (signature)` guard at line 87 treats both `null` and empty string `""` as falsy, so the loop never sets `signatureFound = true`.
- `index.ts:120-123` — After the loop, `!signatureFound` triggers a `401` with message `"Missing signature header. Expected one of: ..."` and logs `HMAC_MISSING` to D1.

**Impact:** None — correctly rejects with 401 and logs the event.

**Caveat:** Only active when `CHECK_HMAC === 'true'` AND `secret` is set (`index.ts:77`). If either env var is missing/unset, the entire HMAC block is bypassed and all requests are accepted. This is an operational configuration risk, not a code bug.

---

### 2. Encoding Mismatch — "auto" Mode Silent Failure
**File:** `webhook_receiver/cloudflareD1/src/utils.ts`, `index.ts`

**Status: ⚠️ Partial**

**Evidence:**
- `config.ts:23` — Sapo is configured with `encoding: 'base64'` (explicit). `DEFAULT_CONFIG` uses `encoding: 'auto'`.
- `index.ts:90-117` — In `auto` mode, the heuristic is: if signature starts with `sha256=` → treat as hex; otherwise → assume base64.
- `utils.ts:35-37` — `atob()` failure on invalid base64 is caught, returns `false` (no silent crash).

**Failure scenarios:**
1. A Sapo request routed through `DEFAULT_CONFIG` instead of the `sapo` config (e.g., wrong URL path): the body would be assumed base64, HMAC would fail, and the request would be rejected with 401. Not silent — it rejects. But the log message says "Invalid signature" not "Encoding mismatch", making diagnosis harder.
2. A valid hex signature without `sha256=` prefix sent to `auto` mode: treated as base64, verification fails silently (returns `false`, logs `HMAC_INVALID`). No crash, but wrong rejection with no diagnostic indicator of the root cause.

**Impact:** Medium — misrouted sources or non-prefixed hex sigs will fail verification with opaque error messages. Sapo itself is explicitly configured (`base64`), so this doesn't affect normal flow.

---

### 3. Duplicate Webhook Events (No Deduplication)
**File:** `ingestion/src/sapo/webhook_consumer.py`

**Status: ❌ Unhandled**

**Evidence:**
- No deduplication check anywhere in `webhook_dispatcher()` (lines 82-209).
- `payload_hash` (MD5 of inner payload, line 166) is computed and stored in the envelope, but is never used to filter duplicates before `yield`.
- `primary_key="entity_id"` on the dlt resource (line 66) and `write_disposition="append"` (line 67) means dlt does NOT deduplicate on `entity_id`. It appends every yielded record.
- The D1 poll query (`index.ts:191-204`) uses a `PROCESSING` lock mechanism, but that only prevents the same message from being delivered twice in parallel. If Sapo sends two separate identical events, both get distinct `msg_id`s, are stored as separate D1 rows, and both pass through to the data lake.

**Impact:** High — duplicate records accumulate in the raw layer. Downstream dbt models that don't deduplicate will double-count orders, revenue figures, etc.

---

### 4. Batch ACK Partial Failure
**Files:** `webhook_consumer/cloudflared1_consumer/src/client.py`, `ingestion/src/sapo/webhook_consumer.py`

**Status: ❌ Unhandled**

**Evidence (receiver side):**
- `index.ts:255-259` — `handleBatchAck` executes a single `DELETE WHERE msg_id IN (...)`. This is atomic at the SQLite/D1 level — either all rows are deleted or none are (if the statement errors). There is no partial success at the SQL level.
- `index.ts:261-267` — Any exception returns `500`. The caller (Python) gets an exception from `raise_for_status()`.

**Evidence (consumer side):**
- `webhook_consumer.py:208-209` (and `client.py:38-44`) — `batch_ack()` catches `RequestException` and prints an error, but does NOT raise. The calling code in `webhook_dispatcher` does not check the return value of `batch_ack()`.
- On a `500` from the worker, `batch_ack` silently swallows the error and returns `None`. The pipeline completes normally, thinking everything succeeded.
- Messages that were processed (yielded to dlt) but not ACKed remain in D1 with status `PROCESSING`. After 60s lock timeout (`LOCK_TIMEOUT = 60000`, `index.ts:174`), they become eligible for re-poll and will be reprocessed.

**Impact:** High — on ACK failure: data is re-ingested after the lock timeout expires (at-least-once semantics in practice, but without visibility that it happened). No alert, no dead-letter tracking.

---

### 5. Consumer Crash Between Processing and ACK
**File:** `ingestion/src/sapo/webhook_consumer.py`

**Status: ⚠️ Partial (acknowledged but not mitigated)**

**Evidence:**
- `webhook_consumer.py:194-209` — The code comment (lines 194-207) explicitly documents the problem: ACK happens after all items are yielded to the dlt generator. If the pipeline load phase fails (after extraction but before load completes), messages have been ACKed but data was not persisted.
- The comment says: `"If pipeline.run crashes during load, we might have ACKed data that wasn't saved."` and marks it as `"IMPROVEMENT: Use dlt state or post-load hook"`.
- ACK is sent at the **end of the generator function**, which completes during dlt's extraction phase — before the load phase executes. This is effectively **at-most-once** on load failure.

**Impact:** High — data loss on pipeline crash during load. The lock timeout (60s) only helps if the crash happens before the generator finishes, not after. Once `batch_ack` is called, the D1 records are deleted regardless of load outcome.

---

### 6. D1 Queue Overflow / No Backpressure
**File:** `webhook_receiver/cloudflareD1/src/index.ts`

**Status: ❌ Unhandled**

**Evidence:**
- `index.ts:155-159` — `INSERT INTO webhooks ...` has no guard: no row count check, no max-queue-size enforcement, no queue depth query before insert.
- If D1 storage is full or hits Cloudflare's row/storage limits, the INSERT will throw an exception.
- `index.ts:162-167` — The outer `try/catch` catches this, logs `WEBHOOK_HANDLER_ERROR` to D1 (which will also fail if D1 is full), and returns `500` to Sapo.
- `logError` at `utils.ts:56` has a try/catch that falls back to `console.error` — so the error is not lost entirely.
- Sapo will receive `500` and will likely retry. With a full queue, all retries also get `500`, creating a retry storm with no self-healing.

**Impact:** High — no circuit breaking, no back-pressure signaling to Sapo. Under sustained high volume or a stalled consumer, the queue grows unbounded until D1 limits are hit. The system has no mechanism to shed load or alert on queue depth.

---

### 7. Unknown Entity Type — Dynamic Table Creation
**File:** `ingestion/src/sapo/webhook_consumer.py`

**Status: ✅ Handled (with caveats)**

**Evidence:**
- `webhook_consumer.py:110-118` — Unknown entity types fall through to `table_name = et_lower` (the raw lowercased entity type string).
- `webhook_consumer.py:188` — `dlt.mark.with_table_name(envelope, table_name)` dynamically routes to any table name dlt accepts.
- dlt will create the table if it doesn't exist, using the envelope schema defined at lines 69-80.

**Caveats:**
1. `et_lower` is user-controlled input (from Sapo webhook URL path). No sanitization before use as a table name. dlt likely sanitizes internally, but this is not verified here. A crafted `entity_type` like `'; DROP TABLE webhooks; --` or excessively long string could cause issues depending on dlt's internal handling.
2. All unknown types share the same envelope schema. If an unknown entity's `inner_payload` lacks an `id` field, `webhook_consumer.py:147-149` skips the message (safe), but the ID is silently collected in `ids_to_ack` at line 104 — it was appended before the `entity_id` check. So a message with no entity ID is ACKed and deleted from D1 even though it was never processed.

**Impact:** Medium — unknown entity types are silently discarded if they lack an ID field, with no alerting. The ACK-before-validation ordering means data can be lost without trace.

---

## Summary Table

| # | Edge Case | Status | Severity |
|---|-----------|--------|----------|
| 1 | Missing/empty HMAC signature header | ✅ Handled | — |
| 2 | Encoding mismatch in "auto" mode | ⚠️ Partial | Medium |
| 3 | Duplicate webhook events (no dedup) | ❌ Unhandled | High |
| 4 | Batch ACK partial failure | ❌ Unhandled | High |
| 5 | Consumer crash between processing and ACK | ⚠️ Partial | High |
| 6 | D1 queue overflow / no backpressure | ❌ Unhandled | High |
| 7 | Unknown entity type dynamic table creation | ✅ Handled (w/ caveats) | Medium |

---

## Unresolved Questions

1. Does dlt sanitize table names from `with_table_name()`? If not, edge case 7 is a SQL injection risk.
2. Is the 60s lock timeout (`LOCK_TIMEOUT`) calibrated against actual pipeline run times? If a run takes >60s, the same batch will be repolled while the first run is still loading.
3. Is there an existing dlt post-load hook or state mechanism planned for resolving the at-most-once gap in edge case 5?
4. What is the Cloudflare D1 storage/row limit for this deployment, and is there any alerting on queue depth?

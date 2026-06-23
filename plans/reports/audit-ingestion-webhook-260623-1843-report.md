# Audit: Ingestion + Webhook Receiver — 2026-06-23

Scope: `ingestion/` + `webhook_receiver/cloudflareD1/` + `webhook_consumer/cloudflared1_consumer/` (actually at `ingestion/src/sapo/webhook_consumer.py` and `ingestion/src/hug/`). Read-only. No code changed.

---

## CRITICAL

### C1 — Bare `"sapo"` in `source_system` across all batch pipeline sources
**Files:** `ingestion/src/sapo/orders.py:244,249`, `customers.py:235`, `accounts.py:201`, `history_log.py:437`, `products.py:215`, `sapo_v2_inventory_transactions.py:311`

All batch-sync and history_log pipelines write `"source_system": "sapo"` (bare) into `sync_metadata` JSON. Per project convention (MEMORY.md), the correct value is `"sapo_v2"` (or `"sapo_v2_mac"`). Downstream dbt models that filter on `source_system` (e.g. `source_system = 'sapo_v2'`) will silently miss all ingested rows from these pipelines.

Direction: replace bare `"sapo"` with `"sapo_v2"` in sync_metadata for all batch+history_log sources.

---

### C2 — Webhook consumer ACKs before dlt completes load (at-most-once risk)
**File:** `ingestion/src/sapo/webhook_consumer.py:211-212`

`ids_to_ack` list is built during `yield` inside the generator, then `client.batch_ack()` is called at the end of the generator function. However, `batch_ack` fires as soon as the generator is exhausted — i.e., after extraction but **before** the dlt load step writes parquet. If `pipeline.run()` fails during normalization or file write, those messages are permanently deleted from D1 (lost data). The code comment at line 199-209 acknowledges this: "If load fails later, we might lose data." This is the core at-most-once vs at-least-once risk.

Direction: move ACK to a post-load hook or dlt `on_load_success` callback, or store IDs in dlt state and ACK only on confirmed successful load.

---

### C3 — Lock timeout mismatch: D1 locks 60 s but consumer can hold batch far longer
**File:** `webhook_receiver/cloudflareD1/src/index.ts:216` + `ingestion/src/sapo/webhook_consumer.py`

D1 poll sets `LOCK_TIMEOUT = 60000` ms (60 s). A consumer batch of 100–1000 messages includes per-message JSON parsing, entity-fetch HTTP calls (history_log path adds Sapo API calls), and dlt pipeline write. Total time easily exceeds 60 s → lock expires → D1 re-releases locked rows → next consumer poll re-delivers them → duplicate rows in parquet (only caught by dedup in dbt, not prevented). Docs referenced "5 min TTL" but actual code is 60 s.

Direction: raise `LOCK_TIMEOUT` to 300 000 ms (5 min) in the Worker, or implement a lock-renewal heartbeat from the consumer.

---

## HIGH

### H1 — `"source_system": "sapo"` duplicate key in `orders.py` dict literal
**File:** `ingestion/src/sapo/orders.py:244,249`

The `sync_metadata` dict has `"source_system"` set **twice** (lines 244 and 249). Python silently takes the last value. The intermediate `"source": "batch_sync"` and commented-out code between them is dead/confusing. Risk: if a future edit adds a key between the two `source_system` lines, the behavior silently changes.

Direction: remove the first duplicate `"source_system"` key and the dead `"source"` key.

---

### H2 — Webhook consumer `CloudflareWorkerClient` uses bare `requests.get/post` with no User-Agent
**File:** `ingestion/src/sapo/webhook_consumer.py:29,51`

`requests.get(url, ...)` and `requests.post(url, ...)` use the default `requests` User-Agent (`python-requests/2.x`). Per MEMORY.md (Cloudflare Bot Fight Mode): the workers.dev + hug.fjp.vn worker returns 403 (error-1010) for Python-urllib/default UA. The `webhook_consumer.py` uses `requests` not `urllib`, but default UA still contains "python-requests" — Cloudflare Bot Fight Mode flags Python UA strings generically. The `hug_webhook_consumer.py` (reuses same `CloudflareWorkerClient`) has the same exposure.

Direction: set an explicit business-like User-Agent on the session/requests in `CloudflareWorkerClient.__init__` (e.g., `"DataIntegration-Worker/1.0"`).

---

### H3 — history_log pipeline name stability: `sapo_v2_history_log` is correct but source_system inconsistency means state orphan risk persists
**File:** `ingestion/run_sapo_v2_history_log.py:27`

Pipeline name is `"sapo_v2_history_log"` (stable, versioned). Good. However the cursor path is `"sync_metadata.event_timestamp"` (line 170 of `history_log.py`). The `source_system` inside `sync_metadata` is `"sapo"` (bare, per C1), and `occur_at` from the API is used as `event_timestamp`. If C1 is ever corrected and a dbt model's filter changes, the incremental cursor value `last_value` is an ISO string comparison (correct: `item_occur_at > last_value`). Cursor logic itself looks correct, but the cursor field path being nested (`sync_metadata.event_timestamp`) means dlt must support nested JSON path extraction — verify dlt version handles this or whether it silently falls back to no cursor.

Direction: verify dlt incremental nested path support; optionally flatten `event_timestamp` to root level as cursor.

---

### H4 — `datetime.utcnow()` (naive, deprecated) used for `processing_timestamp` across all sources
**Files:** `orders.py:251`, `customers.py:237`, `accounts.py:203`, `history_log.py:440`, `products.py:217`, `sapo_v2_inventory_transactions.py:279`, `webhook_consumer.py:158,160,183`

`datetime.utcnow()` is deprecated in Python 3.12+ and returns a **naive** datetime. The resulting ISO string has no `Z`/`+00:00` suffix (exception: `history_log.py:440` appends `"Z"` manually). dlt column type is `"timestamp"` (not `timestamptz`). Per MEMORY.md: naive TIMESTAMP drops timezone, causing wrong `date_key` for 0h–7h orders. While `processing_timestamp` is inside the `sync_metadata` JSON blob and not directly used for partitioning, storing it naive is inconsistent and may cause confusion in downstream transforms that inspect the field.

Direction: replace `datetime.utcnow()` with `datetime.now(timezone.utc)` uniformly.

---

### H5 — `ingestion/src/sapo/client.py:38` hardcoded fallback domain
**File:** `ingestion/src/sapo/client.py:38`

`base_url = "https://fwg.mysapogo.com/admin"` is a hardcoded fallback when neither `domain` nor `base_url` config is set. If credentials are missing from `.dlt/secrets.toml` and env, the code raises `ValueError` (line 59–61) — good. But if domain is missing but user+pass are present (e.g. wrong env), the pipeline silently connects to the production Sapo store using baked-in URL with those creds, which could leak auth to the wrong endpoint.

Direction: remove the hardcoded fallback; raise `ValueError("Missing 'domain' or 'base_url' in config")` instead.

---

## MEDIUM

### M1 — `orders.py` 429 handling re-uses the same response (no re-raise to tenacity)
**File:** `ingestion/src/sapo/orders.py:179-183`

After sleeping `retry_after` seconds, `orders.py` issues a second `session.get(...)` directly inside `fetch_page_with_retry` but does **not** raise if that second call also 429s — it calls `response.raise_for_status()` on it, but tenacity's retry decorator only kicks in on `RequestException`, not `HTTPError`. If the second attempt is also 429, the exception propagates out of tenacity without triggering a retry. Same pattern in `customers.py:174-180` and `inventory_transactions.py:181-186`.

Direction: after 429 sleep+retry, raise `requests.RequestException("429")` to let tenacity handle the retry loop, or restructure so 429 always raises.

---

### M2 — `webhook_dispatcher` in `webhook_consumer.py` skips messages without an `entity_id` but still processes next; skipped messages are NOT ACKed and NOT re-queued
**File:** `ingestion/src/sapo/webhook_consumer.py:146-149`

When `entity_id` is missing from inner payload, `continue` skips it — `msg_id` is not added to `ids_to_ack`. Good: it stays in D1. But since the lock expires in 60 s (see C3), it will be re-delivered on the next poll — infinitely. Poison message loop: malformed messages with no `entity_id` cycle forever, consuming poll quota.

Direction: after N failed deliveries, move to a dead-letter table or at minimum log with alert. Consider adding a `retry_count` column to D1 schema.

---

### M3 — Campaign cache in hug-handler is Worker-level global state — stale after cold start
**File:** `webhook_receiver/cloudflareD1/src/hug-handler.ts:100-102`

`_campaignCache` is a module-level variable. Cloudflare Workers can spawn many isolates in parallel; each isolate has its own fresh cache (TTL irrelevant across isolates). `invalidateCampaignCache()` only flushes the **current isolate's** cache. After an admin upsert that changes campaign targeting, other active isolates continue serving stale campaigns for up to 60 s. For most campaign changes this is acceptable, but quota enforcement (`quota_used < quota_total`) relies on stale data.

Direction: acceptable for current scale; document the known cross-isolate staleness; for quota accuracy, enforce at write time in D1, not at read time in cache.

---

### M4 — `handleBatchAck` in D1 worker unbounded bind parameters
**File:** `webhook_receiver/cloudflareD1/src/index.ts:296-298`

`ids.map(() => "?").join(", ")` with `env.DB.prepare(...).bind(...ids)` for up to 1000 IDs. SQLite default `SQLITE_MAX_VARIABLE_NUMBER` is 999 in older builds; D1 may differ. If caller sends > 999 IDs (consumer polls up to 1000), this can silently fail or truncate.

Direction: chunk ACK requests in batches of 500 in the consumer, or in the Worker split into multiple D1 statements.

---

### M5 — `shared_cookie_manager.py` TOCTOU on cookie validity check
**File:** `ingestion/src/utils/shared_cookie_manager.py:407-421`

`get_valid_cookies()` reads, checks `is_cookie_valid()`, then if invalid reads again (line 416-417) — two separate reads with no lock between. Concurrent processes (multiple Dagster assets running simultaneously) can both see expired cookies, both call `login_and_save_cookies()`, causing parallel Playwright browser sessions. The atomic write (line 241) prevents partial writes, but double-login wastes resources and can trigger Sapo account rate-limits or login CAPTCHAs.

Direction: add a file-based exclusive lock around the check-and-refresh cycle (similar to the lock already used in `_write_cookie_file`).

---

### M6 — `sapo_v2_inventory_transactions.py` source_system is `"sapo"` (bare) — same as C1
**File:** `ingestion/src/sapo/sapo_v2_inventory_transactions.py:311`

Redundant citation of C1 for completeness: this is the inventory-transactions pipeline, separate path from the standard batch pipelines but same bug.

---

### M7 — Customers pipeline sorts by `created_on` but tracks cursor on `modified_on`
**File:** `ingestion/src/sapo/customers.py:156,207`

API call sorts by `created_on desc` (documented in comment: "Sapo API doesn't support sort by modified_on"). But the incremental cursor tracks `modified_on` (line 207: `customer_modified_on = raw_customer.get("modified_on")`). In practice: a customer modified but not created recently will have `modified_on > last_cursor` but will appear late in the sorted DESC list → might never be fetched before early-stop (`consecutive_old_items >= min_overlap_items`). This is a known limitation (docs mention it) but the early-stop threshold of 500 items means updates can be silently missed if they appear after the 500-item window.

Direction: document clearly as a known gap; the history_log is the compensating channel per docs, but verify it's actually covering all update events.

---

### M8 — `run_sapo_v2_webhook_consumer.py` loop catches all exceptions and sleeps — masks crashes in non-`--once` mode
**File:** `ingestion/run_sapo_v2_webhook_consumer.py:74-79`

`except Exception as e: print(...); time.sleep(current_sleep)` in the continuous loop swallows any exception (OOM, DB corruption, config error) and retries silently. In Dagster `--once` mode this correctly re-raises; in standalone loop mode, a fundamental error (e.g. wrong `WORKER_URL`) loops indefinitely, consuming CPU and producing no useful signal.

Direction: add specific exception handling; unrecoverable errors (e.g. auth failure, config error) should break the loop and exit non-zero.

---

## LOW

### L1 — `ingestion/src/sapo/history_log.py` `entity_type` at root is set to `effective_entity_type` which for `customer_address` → `"customer"`, but `dlt.mark.with_table_name` routes to `table_name = get_table_name(env["entity_type"])` — double-lookup is redundant but harmless
**File:** `ingestion/src/sapo/history_log.py:423-425,469-471`

`effective_entity_type` is already the resolved table name. `get_table_name(env["entity_type"])` on line 470 re-looks it up, which returns the same value. No bug, but dead logic.

---

### L2 — `orders.py` `page_size` default is 100, `min_overlap_items` default is 500 — overlap > page size means at least 5 consecutive fully-old pages before early stop
**File:** `ingestion/src/sapo/orders.py:58,59`

With page_size=100 and min_overlap_items=500, the pipeline fetches up to 5 extra pages of already-seen orders every run. For a 10-min schedule with low order volume this is wasteful. Customers source has same configuration.

Direction: reduce `min_overlap_items` to `page_size * 2` (200) or document why 500 is needed.

---

### L3 — `ingestion/src/sapo/client.py:40` `login_url` defaults to orders page, not login page
**File:** `ingestion/src/sapo/client.py:40`

`login_url = f"{base_url}/orders"` — this is the orders list, not the Sapo login page. The actual login happens via Playwright in `shared_cookie_manager.py`, which navigates to this URL first. If Sapo changes their SSO flow, this could silently navigate to a wrong starting page. Low risk since the `sapo_login_strategy` waits for `**/admin**` redirect.

---

### L4 — `webhook_receiver/cloudflareD1/src/index.ts:186-189` queue depth guard counts only `'NEW'` rows — `'PROCESSING'` rows not counted
**File:** `webhook_receiver/cloudflareD1/src/index.ts:186-189`

Queue full guard: `WHERE status = 'NEW'`. Stuck PROCESSING rows (consumer crashed, lock expired but consumer died) don't count toward the 10 000 cap. In a stuck-consumer scenario, PROCESSING rows can grow unboundedly while NEW count stays below cap, allowing new inserts past the guard.

Direction: count `status IN ('NEW', 'PROCESSING')` for the depth guard.

---

### L5 — `hug-handler.ts` `handleHugCampaignPreview` full-table scan on `hug_customer` in JS loop
**File:** `webhook_receiver/cloudflareD1/src/hug-handler.ts:909-914`

Full table fetch then JS-side matching. Acceptable for 7.5k rows, but no pagination guard on the D1 fetch (always fetches all rows). If `hug_customer` grows beyond 50k rows this becomes an admin bottleneck (D1 result set limits).

Direction: acceptable now; add a guard note if hug_customer row count exceeds 20k.

---

### L6 — `shared_cookie_manager.py` screenshot on login failure writes to CWD with a predictable name
**File:** `ingestion/src/utils/shared_cookie_manager.py:396`

`page.screenshot(path=f"{self.source}_login_error.png")` — no directory, writes to process CWD. If multiple pipelines run concurrently and both fail login, they write to the same filename, last-write-wins (data loss). Also leaks a file into the repo directory.

Direction: write to a temp/logs dir with timestamp in filename.

---

### L7 — `msvcrt.locking` in `shared_cookie_manager.py` only locks 1 byte — may not prevent concurrent access on Windows
**File:** `ingestion/src/utils/shared_cookie_manager.py:22-28`

`msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)` locks only 1 byte. On Windows NTFS, multiple processes can still read or write outside the locked region. The atomic-rename strategy (`_write_cookie_file`) provides the primary safety; the lock is defense-in-depth but may not fully work as intended.

Direction: rely on atomic rename as primary concurrency guard; document that the msvcrt lock is best-effort on Windows.

---

## Unresolved Questions

1. **dlt incremental nested path** (`sync_metadata.event_timestamp`): does the installed dlt version (unverified) correctly extract nested JSON fields as incremental cursors, or does it silently fall back to no cursor? If broken, history_log re-fetches everything on each run.

2. **`source_system` in transformation/dbt filters**: confirmed via grep that `transformation/` models reference `sapo_v2` in comments only — no active `WHERE source_system = ...` SQL filters found. C1 fix is safe; no dbt models will break.

3. **Inventory transactions `source_system = "sapo"` in `sapo_v2_inventory_transactions.py`**: treated as a bug (consistent with user confirmation that bare `"sapo"` no longer exists); fixed to `"sapo_v2"`.

4. **`LOCK_TIMEOUT` in D1 documentation vs code**: resolved — code was 60 s (bug); fixed to 300 s (5 min) to match documented intent.

5. **Cloudflare Bot Fight Mode**: fixed (H2) — `requests.Session` now sends `DataIntegration-Worker/1.0` UA; re-test against workers.dev to confirm 403s resolved.

---

## FIXES APPLIED 260623

| Finding | Status | File(s) changed | Notes |
|---------|--------|-----------------|-------|
| C1 — bare `"sapo"` source_system | APPLIED | `orders.py:244-249`, `customers.py:235`, `accounts.py:201`, `history_log.py:437`, `products.py:215`, `sapo_v2_inventory_transactions.py:311` | All changed to `"sapo_v2"` |
| H1 — duplicate `source_system` key in orders.py | APPLIED | `orders.py:244-249` | Combined with C1: removed duplicate key and dead `"source"` key |
| H4 — `datetime.utcnow()` naive | APPLIED | All 6 batch sources + `webhook_consumer.py` | `datetime.now(timezone.utc)` throughout; `timezone` import added to each file |
| H2 — webhook consumer User-Agent | APPLIED | `webhook_consumer.py:15-20` | `requests.Session` with `User-Agent: DataIntegration-Worker/1.0`; both `poll_messages` and `batch_ack` use session |
| C2 — ACK before load completes | APPLIED | `webhook_consumer.py`, `run_sapo_v2_webhook_consumer.py` | Added `PendingAck` class + `build_sapo_webhook_source()` returning `(source, pending_ack)`; runner calls `pending.ack()` after `pipeline.run()` succeeds; legacy `sapo_webhook_source` + `webhook_dispatcher` kept for backward compat with explicit at-most-once warning |
| C3 — LOCK_TIMEOUT 60 s mismatch | APPLIED | `webhook_receiver/cloudflareD1/src/index.ts:216` | Raised to 300000 ms (5 min) to match documented intent |
| H5 — hardcoded fallback domain in client.py | APPLIED | `ingestion/src/sapo/client.py:37-38` | Hardcoded URL removed; raises `ValueError` when domain/base_url missing |
| M1 — 429 re-raise to tenacity | APPLIED | `orders.py`, `customers.py`, `sapo_v2_inventory_transactions.py` | After sleep, raise `requests.exceptions.RequestException` so tenacity retries; removed second inline GET |
| L4 — queue depth guard misses PROCESSING | APPLIED | `webhook_receiver/cloudflareD1/src/index.ts:186-188` | Changed `status = 'NEW'` → `status IN ('NEW', 'PROCESSING')` |
| L6 — screenshot overwrites on concurrent failure | APPLIED | `ingestion/src/utils/shared_cookie_manager.py:395-399` | Screenshot now written to `$TMPDIR/data_integration_logs/{source}_login_error_{ts}.png` |
| H3 — cursor path nested JSON support | DEFERRED | — | No code change; needs dlt version check at runtime. Document as known risk. |
| M2 — poison message dead-letter | DEFERRED | — | Requires D1 schema change (`retry_count` column) outside file-ownership scope; log already emitted; C3 fix reduces re-delivery frequency |
| M3 — campaign cache cross-isolate staleness | DEFERRED | — | Acceptable at current scale; documented in finding |
| M4 — unbounded D1 bind params (>999) | DEFERRED | — | Consumer poll limit is 100 by default; risk only at poll_limit > 999. Document; chunking can be added when limit is raised |
| M5 — TOCTOU on cookie validity | DEFERRED | — | Requires file-lock around check-and-refresh; non-trivial cross-platform change; atomic rename provides primary safety |
| M6 — inventory transactions source_system | APPLIED | (same as C1 for this file) | Combined with C1 |
| M7 — customers sort/cursor mismatch | DEFERRED | — | Known limitation (Sapo API constraint); compensated by history_log channel |
| M8 — loop swallows unrecoverable errors | DEFERRED | — | Low priority; Dagster `--once` mode re-raises correctly; standalone loop logging sufficient for now |
| L1 — redundant double-lookup in history_log | DEFERRED | — | Dead logic, harmless; not worth the churn |
| L2 — min_overlap_items > page_size waste | DEFERRED | — | Config tuning, not a correctness bug; note for next performance review |
| L3 — login_url defaults to orders page | DEFERRED | — | Low risk; SSO redirect handles it |
| L5 — full-table scan in campaign preview | DEFERRED | — | Acceptable at 7.5k rows; note for >20k |
| L7 — msvcrt.locking 1 byte on Windows | DEFERRED | — | Atomic rename is primary guard; document as best-effort |

**Compile check:** `python -m py_compile` on all 10 modified Python files → ALL OK (Python 3.14.2)
**TypeScript check:** `tsc --noEmit` in `webhook_receiver/cloudflareD1` → TSC OK

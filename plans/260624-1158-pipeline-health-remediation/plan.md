# Pipeline Health Remediation

**Created:** 2026-06-24 | **Branch:** main | **Source:** [audit report](../reports/full-stack-health-audit-datapipeline-to-crm-260624-1119-report.md)

Remediation backlog from the full-stack health audit (ingestion → CRM). Items added incrementally; execute only after per-phase approval.

## Done (2026-06-24)
- [x] **Retire `webhook_consumer/cloudflared1_consumer/`** — dead; D1 polling lives in Dagster `ingest_sapo_v2_webhook_consumer_asset` → `ingestion/`. Removed + `AGENTS.md` label fixed.
- [x] **Phase 01** — rename `sapo_assets.py` → `sapo_v2_assets.py` (key_prefix unchanged).
- [x] **Repo hygiene** — `.gitignore` += `check_*.py`, `rill/tmp/` (`*.duckdb` already present); untracked 9 root `check_*.py` via `git rm --cached` (local kept). No `.duckdb`/`rill/tmp` were tracked.
- [x] **`build_serving_db` duckdb_lock op_tag** added (`serving.py`).
- [x] **Hug asset → morning_digest** KNOWN_ASSETS + ASSET_DISPLAY (visibility). _Asset-checks (freshness/trend) still pending — needs Hug SLA thresholds in `ingestion_sla.yaml` first._
- [x] **SQLite conn leak** guarded with try/finally (`reconciliation.py`).
- [x] **YAML BOM** stripped from `ingestion_sla.yaml` (was breaking strict PyYAML).
- [x] **argparse `--debug` no-op** fixed (`run_sapo_v2_history_log.py`).
- [x] **Duplicate assignment** removed (`shared_cookie_manager.py`).
- [x] **Cookie naive-datetime** — tz-aware UTC fix applied (`shared_cookie_manager.py`), made robust to legacy naive files (load normalizes naive→UTC). User accepts forced re-login.
- [x] **Worker bearer-token DEPLOYED + ENFORCED** — `wrangler deploy` (v3d9e7d47) + `POLL_TOKEN` secret + `WORKER_POLL_TOKEN` in `.env.docker`; verified authed `/ack`→400, unauth→401. `data_platform` recreated to load env + Hug SLA.
- [x] **INCIDENT (pre-existing) resolved** — Sapo webhook ingestion stalled ~7h (zombie realtime run `35c42d4d` STARTED@09:45 blocked self-overlap guard; stuck-sensor missed it). Marked 3 zombies FAILURE → recovery confirmed (fresh realtime launches). Root-cause fix = Phase 05.
- [x] **Phase 05 — reliability fix DEPLOYED** — enabled Dagster `run_monitoring` (MonitoringDaemon now active, `max_runtime_seconds: 14400` coarse backstop) + hardened `stuck_run_alerter.py` (per-job max-runtime + `last_event_time=None` blind-spot). Worst-case stuck detection 7h→≤45min. Report: `plans/reports/from-reliability-agent-*-260624-1656-report.md`.
- [x] **dagster.yaml now version-controlled** — was gitignored (volume-only) → whole instance config (concurrency lock, run_monitoring, retention) would be silently lost on fresh deploy. Tracked `orchestration/dagster.yaml` as source + copy-if-absent at boot in `docker-compose.yml` (never clobbers live volume copy). Boot verified clean.

## Phases
| # | Phase | Priority | Status |
|---|-------|----------|--------|
| 01 | [Rename sapo_assets.py → sapo_v2_assets.py](phase-01-rename-sapo-assets-to-sapo-v2.md) | Low (consistency) | ✅ DONE |
| 02 | [Worker security: queue bearer-token + Sapo webhook HMAC](phase-02-sapo-webhook-hmac-enforce.md) | HIGH (security) | ✅ DONE — bearer-token + Sapo HMAC both ENFORCED |
| 03 | [Google Sheets via service account](phase-03-gsheets-service-account.md) | Medium (security) | ⬜ TODO (needs SA key) |
| 04 | [Corrected margin at order/CEO level](phase-04-order-level-corrected-margin.md) | Medium (BI correctness) | ✅ CLOSED — moot (order-level already H010-correct) |
| 05 | Run-monitoring + stuck-sensor reliability fix | HIGH (reliability) | ✅ DONE + deployed |
| 09 | Hug asset freshness SLA | Low (monitoring) | ✅ DONE + deployed |

## Decisions (from user, 2026-06-24)
- **Docker network is private** → Worker queue endpoints (`/poll`,`/ack`,`/release`) need a simple **bearer-token**, not HMAC (HMAC is for inbound Sapo `/webhook/*` only). CRM mutation-API auth = lower priority (private net).
- **Ports firewall check** → deferred.
- **Sapo `/webhook/*` HMAC** → prioritize: see Phase 02 (observe→confirm→enforce).
- **Google Sheets are public** → switch to a **service account** (share sheets to SA email, read via Sheets API) to remove public exposure; quick interim = stop tracking the IDs in `config.toml`.
- **Serving session TZ = ICT (target).** Verified: Evidence opens its own DuckDB copy with NO `SET TimeZone` → session = UTC default → existing `AT TIME ZONE 'Asia/Ho_Chi_Minh'` in `ceo-weekly-pulse` is CORRECT (not double-converting). No change needed.
- **`mart_hug_optin`** = warehouse-only by design (CRM reads warehouse directly) → `materialized='table'` is FINE, not a bug. **`fact_order_transitions`** has no consumer yet → leave; convert to external only when a BI card needs it.
- **`realized_margin_pct` NOT in `fact_order_economics`** (only `gross_margin_pct` at line 141; realized_* lives in SKU/product marts) → Evidence/detailView margin swap is NOT trivial; needs adding a realized margin to the order-level fact or re-sourcing — separate decision, not done.
- **Orphan src_ models** (`purchase_orders`, `stock_adjustments`) → keep for future integration (do NOT disable/delete).
- **Cookie tz** → fix now + force re-login (done).

## Remaining open work (prioritized) — as of 2026-06-24 end of session

### HIGH — reliability (silent data loss / silent green)
- [ ] **Webhook ACK-before-load** in `ingestion/src/hug/hug_webhook_consumer.py` — ACKs inside the dlt generator before load commits → at-most-once, Hug events lost on load failure. (Sapo webhook consumer already got the at-least-once fix 2026-06-23; Hug did NOT.) Apply the `PendingAck` pattern.
- [ ] **Batch pipelines swallow exceptions → Dagster green on failure** — `ingestion/src/sapo/{orders,customers,history_log}.py` break after MAX_ERRORS and return cleanly; Dagster marks asset success with 0 rows. Re-raise / `sys.exit(1)` after MAX_ERRORS.
- [ ] **`history_log.py:501`** advances `page` on transient error → permanently skips that page's records. Don't increment page on transient errors.

### MEDIUM — serving correctness
- [ ] **`fact_orders.time_key` UTC-hour bug** — uses `extract(hour from created_at)` (UTC) while `date_key` is ICT → ~30% of orders (17:00–24:00 ICT) get wrong `dim_time` join (business_hour/peak_hour). Wrap in `AT TIME ZONE 'Asia/Ho_Chi_Minh'`. (Cheapest high-value correctness fix left.)
- [ ] **`dim_customers` non-atomic `post_hook COPY`** — COPY failure on locked file leaves serving parquet stale but dbt marks SUCCESS. Convert to native `external` + `location=`.
- [ ] **detailView `order_cogs_items.sql` queries `int_*`** — violates "serving views only" contract; arch test doesn't catch it. Expose via a mart view.

### MEDIUM — security (private network lowers urgency)
- [ ] **CRM mutation APIs no auth** (`crm/.../inbound/http/*`) + Messenger ingest no HMAC. Add internal-token middleware. (Lower priority — Docker net private.)
- [ ] **Containers run as root** (all except metabase) — add non-root `USER` to Dockerfiles.
- [~] **Ports `0.0.0.0` bypass Caddy** — DEFERRED per user (firewall check).

### LOW — minor
- [ ] **Dynamic `_INGESTION_JOBS`** in `definitions.py` — manual list can drift; build from jobs with `concurrency_group=dbt_rw` so backup sensor never misses a new ingestion job.

### Done this session (was backlog)
build_serving_db duckdb_lock ✅ · quick-win gitignore/hygiene ✅ · Worker bearer-token + Sapo HMAC enforced ✅ · run_monitoring + stuck-sensor ✅ · dagster.yaml tracked ✅ · Hug in morning_digest ✅ · cookie tz ✅ · margin (moot, order-level already correct) ✅ · `fact_order_transitions`/`mart_hug_optin` (by-design, not bugs) ✅

## Open questions
- See audit report §"Unresolved questions" (8 items — webhook posture, LAN trust, realized_margin_pct availability, etc.).

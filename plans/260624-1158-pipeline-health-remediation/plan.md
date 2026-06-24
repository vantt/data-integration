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
| 03 | [Google Sheets via service account](phase-03-gsheets-service-account.md) | Medium (security) | ⏸️ DEFERRED (user, 2026-06-24) |
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

### HIGH — reliability (silent data loss / silent green) — ✅ DONE 2026-06-24
- [x] **Webhook ACK-before-load** — `hug_webhook_consumer.py` refactored to at-least-once (`build_hug_webhook_source` + `PendingAck`, ack after `pipeline.run()`); runner updated. py_compile OK.
- [x] **Batch pipelines swallow exceptions** — `orders.py`/`customers.py`/`history_log.py` now RE-RAISE after MAX_ERRORS → Dagster fails loudly instead of green.
- [x] **`history_log.py` page skip** — removed the rogue `page += 1` in the except branch (same page retried).
  Report: `plans/reports/from-ingestion-reliability-agent-ack-reraise-pageskip-260624-1802-report.md`. (Applies on next ingestion run — code volume-mounted.)

### MEDIUM — serving correctness — ✅ DONE + verified (deployed)
- [x] **`fact_orders`/`fact_sales` time_key UTC bug** → ICT (verified 0 serving mismatches).
- [x] **`dim_customers` non-atomic post_hook** → native `external`+`location=` (verified: dbt run SUCCESS, serving 7573 rows).
- [x] **`mart_sku_economics_monthly.gross_margin_pct`** (deprecated) → NULLed, 0 consumers (verified: serving non-null=0).
- [dropped] **detailView `order_cogs_items.sql` int_***  — detailView is being RETIRED (CRM replaces); no fix needed.

### MEDIUM — CRM data integrity — ✅ DONE (deployed, crm healthy)
- [x] **identity_resolver** watermark in-txn + Zalo-only dedup by `(token, zalo_uid)`.
- [x] **segment refresh** wrapped in single transaction (`replace_rule_members`).

### MEDIUM/HIGH — security
- [x] **CRM `/api` mutation auth — ENFORCED** — `X-CRM-Token` required on all `/api/*` mutation routes; `CRM_API_TOKEN` set in root `.env` + wired in compose. Verified: no-token→401, token→422(passes), read→200. Web UI (separate routes) + Dagster `/admin/refresh` (X-Refresh-Token) unaffected; messenger/ingest excluded. Zero internal `/api` callers confirmed.
- [x] **`CRM_REFRESH_TOKEN` now required** at compose level (`:?`), already set in `.env.docker`.
- [x] **`.env.docker` file-mount removed** from data_platform; **resource limits** added to all services (verified up).
- [partial] **Containers non-root** — `evidence` done (applies on next image rebuild); data_platform/crm/rill SKIPPED (named-volume write perms need a uid+ownership strategy).
- [⏸️] CRM Messenger HMAC · ports `0.0.0.0` — DEFERRED per user.

### LOW — ✅ DONE
- [x] `system_backup` pipe-deadlock → Popen line-iter · gsheet tz partition keys · `_INGESTION_JOBS` semi-dynamic · morning_digest sapo_inventory label · recon thresholds → ingestion_sla.yaml.

### Done earlier this session
build_serving_db duckdb_lock ✅ · gitignore/hygiene ✅ · Worker bearer-token + Sapo HMAC enforced ✅ · run_monitoring + stuck-sensor ✅ · dagster.yaml tracked ✅ · Hug SLA ✅ · cookie tz ✅ · ingestion reliability (ack/re-raise/page-skip) ✅ · margin moot ✅

### Truly remaining (deferred / needs decision)
- **non-root data_platform/crm/rill** (volume-ownership) · **apply evidence non-root** (image rebuild)
- Deferred: Phase 03 service-account · ports `0.0.0.0` · Messenger HMAC · Worker replay-protection · HUG_ZALO_OA_URL · config.toml sheet IDs · sheets `rows_written` · >200 LOC modularization

## Open questions
- See audit report §"Unresolved questions" (8 items — webhook posture, LAN trust, realized_margin_pct availability, etc.).

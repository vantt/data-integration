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

## Phases
| # | Phase | Priority | Status |
|---|-------|----------|--------|
| 01 | [Rename sapo_assets.py → sapo_v2_assets.py](phase-01-rename-sapo-assets-to-sapo-v2.md) | Low (consistency) | ✅ DONE |
| 02 | [Worker security: queue bearer-token + Sapo webhook HMAC](phase-02-sapo-webhook-hmac-enforce.md) | HIGH (security) | 🟡 bearer-token code done; HMAC + deploy pending |
| 03 | [Google Sheets via service account](phase-03-gsheets-service-account.md) | Medium (security) | ⬜ TODO (needs SA key) |
| 04 | [Corrected margin at order/CEO level](phase-04-order-level-corrected-margin.md) | Medium (BI correctness) | ⬜ TODO (research first) |
| 09 | Hug asset freshness SLA | Low (monitoring) | ✅ DONE |

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

## Audit backlog (not yet phased — pull into phases as prioritized)
**Reliability (high):** webhook ACK-before-load (`hug_webhook_consumer.py`); batch pipelines swallow exceptions → Dagster green on failure (`orders/customers/history_log`); `history_log.py:501` skips failed page.
**Serving correctness:** `fact_order_transitions` + `mart_hug_optin` `materialized='table'` (never served); `fact_orders.time_key` UTC-hour bug; `dim_customers` non-atomic post_hook COPY; detailView `order_cogs_items.sql` queries `int_*`.
**Concurrency:** `build_serving_db` missing `duckdb_lock` op_tag.
**Security:** Worker `/poll`/`/ack`/`/release` unauth + `CHECK_HMAC` off; CRM mutation APIs no auth; ports `0.0.0.0` bypass Caddy; containers run root.
**Human-facing margin:** `gross_margin_pct` (pre-H010) on Evidence CEO page + detailView → use `realized_margin_pct`.
**Quick wins:** gitignore `*.duckdb`/`rill/tmp/`/`check_*.py`; Hug asset in morning_digest; dynamic `_INGESTION_JOBS`.

## Open questions
- See audit report §"Unresolved questions" (8 items — webhook posture, LAN trust, realized_margin_pct availability, etc.).

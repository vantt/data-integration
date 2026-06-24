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
- [~] **Cookie naive-datetime** — DEFERRED: tz-aware fix changes cookie JSON format → invalidates existing files; do at next forced re-login.

## Phases
| # | Phase | Priority | Status |
|---|-------|----------|--------|
| 01 | [Rename sapo_assets.py → sapo_v2_assets.py](phase-01-rename-sapo-assets-to-sapo-v2.md) | Low (consistency) | ✅ DONE |

## Audit backlog (not yet phased — pull into phases as prioritized)
**Reliability (high):** webhook ACK-before-load (`hug_webhook_consumer.py`); batch pipelines swallow exceptions → Dagster green on failure (`orders/customers/history_log`); `history_log.py:501` skips failed page.
**Serving correctness:** `fact_order_transitions` + `mart_hug_optin` `materialized='table'` (never served); `fact_orders.time_key` UTC-hour bug; `dim_customers` non-atomic post_hook COPY; detailView `order_cogs_items.sql` queries `int_*`.
**Concurrency:** `build_serving_db` missing `duckdb_lock` op_tag.
**Security:** Worker `/poll`/`/ack`/`/release` unauth + `CHECK_HMAC` off; CRM mutation APIs no auth; ports `0.0.0.0` bypass Caddy; containers run root.
**Human-facing margin:** `gross_margin_pct` (pre-H010) on Evidence CEO page + detailView → use `realized_margin_pct`.
**Quick wins:** gitignore `*.duckdb`/`rill/tmp/`/`check_*.py`; Hug asset in morning_digest; dynamic `_INGESTION_JOBS`.

## Open questions
- See audit report §"Unresolved questions" (8 items — webhook posture, LAN trust, realized_margin_pct availability, etc.).

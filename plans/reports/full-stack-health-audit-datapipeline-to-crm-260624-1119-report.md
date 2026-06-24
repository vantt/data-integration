# Full-Stack Health Audit — Data Pipeline → CRM

**Date:** 2026-06-24 | **Mode:** read-only, 6 parallel Sonnet agents | **Scope:** ingestion, transformation, orchestration, serving/BI, CRM app, infra/security
**Method:** each subsystem scanned independently for correctness, reliability, security, cross-platform, maintainability. Findings cited `file:line`. Nothing modified.

---

## Executive Summary

System is broadly well-engineered: solid DuckDB single-writer discipline, ICT/VAT/COGS conventions mostly correct, hexagonal CRM, SQLite-WAL health DB, schedule overlap guards, **no committed secrets**. The risks that can bite later cluster in 5 themes:

1. **Silent data loss / silent green** — webhook consumers ACK before load; batch pipelines swallow exceptions → Dagster goes green on failure.
2. **Two marts never reach the serving layer** — `materialized='table'` → invisible to Metabase.
3. **One timezone bug in a hot path** — `fact_orders.time_key` uses UTC hour (~30% of orders mis-joined to `dim_time`).
4. **Unauthenticated surfaces** — public Cloudflare Worker queue endpoints, CRM mutation APIs, HMAC off-by-default; ports bypass Caddy.
5. **Uncorrected margin shown to humans** — `gross_margin_pct` (pre-H010) on CEO Evidence page + detailView.

Total: ~75 findings. The 12 below are the ones to act on first.

---

## TOP PRIORITY (fix before they bite)

### Data loss & silent failure (reliability)

| # | Sev | Location | Problem | Fix |
|---|-----|----------|---------|-----|
| 1 | CRIT | `ingestion/src/hug/hug_webhook_consumer.py:182` + legacy `webhook_consumer.py:96` | ACK fires inside the dlt resource generator (during extract), **before** `pipeline.run()` load commits → at-most-once, not at-least-once as documented. Load failure = lost Hug/webhook events. | Use the `PendingAck` pattern from `build_sapo_webhook_source()` (ack only after load success). |
| 2 | CRIT | `webhook_consumer/cloudflared1_consumer/src/client.py:18,35` + `main.py:65-79` | No `timeout=` on poll/ack HTTP (indefinite hang); no User-Agent (Cloudflare Bot-Fight 403 error-1010); ACK before `pipeline.run()` (data loss). Whole module is the un-fixed twin of `ingestion/`. | Add `timeout=30` + explicit UA; ack after load. **Confirm if this module is still live or retired** — if retired, delete. |
| 3 | HIGH | `ingestion/src/sapo/orders.py:276`, `customers.py:265`, `history_log.py:315,495` | Outer `except Exception` counts errors, breaks loop after MAX, returns cleanly → Dagster sees success with zero/partial rows. Persistent Sapo outage = green run, no data. | Re-raise (or `sys.exit(1)`) after MAX_ERRORS; log swallowed exceptions. |
| 4 | HIGH | `ingestion/src/sapo/history_log.py:501` | `page += 1` on transient error permanently **skips** the failed page's records (orders/customers correctly retry same page). | Don't advance page on transient errors. |

### Serving correctness

| # | Sev | Location | Problem | Fix |
|---|-----|----------|---------|-----|
| 5 | CRIT | `transformation/models/marts/sales/fact_order_transitions.sql:1` + `marts/customer/mart_hug_optin.sql:2` | `materialized='table'` (no `get_rolling_location()`) → stays in warehouse DB, never lands in rolling parquet; `bootstrap_serving_views.py` drops the view. Any Metabase card built on these goes dark. | Convert to `external` + `location="{{ get_rolling_location() }}"`, or explicitly document as non-serving. |
| 6 | HIGH | `transformation/models/marts/sales/fact_orders.sql:150` | `time_key` uses `extract(hour from created_at)` (UTC) while `date_key` correctly applies `AT TIME ZONE 'Asia/Ho_Chi_Minh'`. Orders 17:00–23:59 ICT (~30%/day) get wrong `dim_time` join (business_hour/peak_hour/day_period). | Apply `AT TIME ZONE 'Asia/Ho_Chi_Minh'` before extracting hour/minute. |
| 7 | HIGH | `transformation/models/marts/core/dim_customers.sql:1` | Exports via `post_hook COPY` (non-atomic, outlier pattern). COPY failure on a locked file leaves serving parquet stale but dbt marks SUCCESS. | Convert to native `external` + `location=` like every other dim. |
| 8 | CRIT | `detailView/.../duckdb/queries/order_cogs_items.sql:15` | Queries `int_order_cogs_reconciled` + `int_order_promo_goods_cost` (intermediate models) — violates "serving views only" contract; arch test only covers domain/app purity, not this. Any dbt int_ refactor = runtime binder error. | Expose via a mart view; repoint SQL. |

### Concurrency

| # | Sev | Location | Problem | Fix |
|---|-----|----------|---------|-----|
| 9 | CRIT/HIGH | `orchestration/assets/serving.py:102` (`build_serving_db`) | Writes `olap.duckdb` but lacks `op_tags={"dagster/concurrency_key":"duckdb_lock"}` that the two other DuckDB-writer assets have. Job-level `dbt_rw=1` covers scheduled runs, but a manual trigger can collide → lock storm. | Add the `duckdb_lock` op_tag. |

### Security / exposure

| # | Sev | Location | Problem | Fix |
|---|-----|----------|---------|-----|
| 10 | HIGH | `webhook_receiver/cloudflareD1/src/index.ts:46-53,98` | `/poll /ack /ack-batch /release` have **zero auth** on a public `workers.dev` URL (anyone can drain/delete the queue); `CHECK_HMAC` defaults **false** — if the wrangler secret was never set, `/webhook/*` accepts unauthenticated payloads. | Add bearer token on queue endpoints; set `CHECK_HMAC=true`; add startup posture log. |
| 11 | HIGH | CRM `conversation_handler.py:101` (no HMAC on Messenger ingest); all `inbound/http/*` mutation APIs no auth; `admin_handler.py:300` `CRM_REFRESH_TOKEN` optional | "LAN-trust" model leaves every mutation endpoint open to any container-network peer; forgotten token = open `/admin/refresh` ETL trigger. | Add shared internal-token middleware on mutations; make refresh token required (fail-fast). |
| 12 | MED-HIGH | `docker-compose.yml` (all ports `0.0.0.0`) + Dockerfiles run as **root** (except metabase) | Metabase admin / Dagster reachable on LAN bypassing Caddy auth; root + bind-mounted `app_data` = full host-volume write on any container RCE. | Bind app ports to `127.0.0.1`, expose only Caddy; add non-root `USER` to each Dockerfile. |

---

## SECONDARY (worth scheduling)

**Margin correctness (human-facing):**
- `evidence/pages/ceo-weekly-pulse/index.md:249,257` + detailView `order_header.sql:27`, `customer_value_metrics.sql:9`, `customer_order_history.sql:12` use `gross_margin_pct` (H010-uncorrected, ~5 SKUs ~2× too low) instead of `realized_margin_pct`. CEO sees inflated margin.
- `mart_sku_economics_monthly.sql:400` still physically materializes `gross_margin_pct` despite `meta.deprecated:true` → new BI cards can pick the wrong column. NULL it or suffix `_DEPRECATED`.

**Monitoring blind spots:**
- `orchestration/ops/morning_digest.py` KNOWN_ASSETS + `asset_checks/__init__.py` omit the Hug asset (runs every 3 min) → silent Hug failures invisible.
- `orchestration/definitions.py:299` `_INGESTION_JOBS` manually maintained → a new SYNC_TAGS job not added = backup can snapshot DuckDB mid-write. Build the list dynamically.
- `orchestration/ops/system_backup.py:35` `subprocess.run(capture_output=True)` — pipe-buffer deadlock if backup ever gets verbose (same class as the documented 16h hang). Use Popen line-iteration.

**Connection-leak / lock-storm risk:**
- `orchestration/assets/reconciliation.py:148` SQLite `conn` without try/finally — leaked WAL reader on query exception.
- `scripts/maintenance/sync_seeds.py:21`, `cleanup_and_verify.py:9` open DuckDB without `read_only=True` (relative paths) — lock risk if run while Metabase/dbt active.

**Timezone (lower frequency):**
- `ingestion/src/utils/shared_cookie_manager.py:297,381` naive `datetime.now()` cookie expiry — short-TTL cookies break under UTC container.
- `gsheet_team_config.py`, `gsheet_targets.py`, `gsheet_marketing_spend.py:152` naive `datetime.now().year/.month` partition keys — wrong partition at month/year rollover in UTC container.
- CRM `worklist_ranking.py:24` uses `timezone(timedelta(hours=7))` not `ZoneInfo` (safe today, VN has no DST — consistency only).

**Atomicity (CRM):**
- `identity_resolver.py:239` watermark saved after commit → crash re-processes; Zalo-only opt-ins (NULL scanner_phone) duplicate on re-run.
- `segment_repository`/`segment_service.py:146` delete-then-insert loop not in a transaction → partial segment on crash.
- `sync/reverse_etl_warehouse_to_crm.py:147` per-step commit, no batch transaction boundary.

**Cruft / governance:**
- `evidence/sources/datalake/olap-serving.duckdb` + `rill/tmp/*.db` are git-tracked binaries → repo bloat, stale-cache, data-in-history. Gitignore them.
- Root `check_*.py` (9 files) tracked, `_tmp_gift_check.py` untracked (ok) — gitignore `check_*.py` or move to `scripts/analysis/`.
- `ingestion/.dlt/config.toml` tracked with real Sapo domain + 3 Google Sheet IDs → move to untracked secrets; placeholder FB tokens invite accidental real-token commits.
- `docker-compose.yml:41` `.env.docker` bind-mounted into container (redundant with `env_file:`) → secrets readable at known path, larger blast radius.
- Orphaned dbt models: `src_sapo_v2_purchase_orders`, `src_sapo_v2_stock_adjustments` (zero refs); FB Ads/Messenger models disabled. Confirm intent or `enabled=false`/delete.
- No `mem_limit`/`cpus` on any compose service → one runaway dbt/Dagster job OOMs the whole VM.
- Floating image tags (`python:3.x-slim`, `node:20-slim`); only Rill pinned. Pin for reproducibility.

**In-flight plans (no half-done runtime risk, but stale):**
- `crm-tag-acl-sync` + `crm-i18n-json-locale` are 100% TODO — **no code written**, so no broken state. BUT tag-acl plan references migration `0022` which is **already taken** (`0022_hug_identity_link`); renumber to `0027+` before executing. ACL enforcement is absent until then.

---

## Quick wins (low effort, real value)
1. Gitignore: `*.duckdb`, `rill/tmp/`, `check_*.py`. (5 min)
2. Add `duckdb_lock` op_tag to `build_serving_db`. (1 line)
3. `fact_orders.time_key` → wrap in `AT TIME ZONE`. (1 line, re-run mart)
4. Swap `gross_margin_pct`→`realized_margin_pct` in Evidence CEO page + detailView. (few lines)
5. Add Hug asset to morning_digest KNOWN_ASSETS. (1 line)
6. Set `CHECK_HMAC=true` + bearer token on Worker queue endpoints.

---

## Unresolved questions (need user/ops input)
1. **Webhook consumer duplication** — is `webhook_consumer/cloudflared1_consumer/` still in production, or fully superseded by `ingestion/src/sapo/webhook_consumer.py`? If retired, delete (removes 3 findings).
2. **CHECK_HMAC posture** — is `CHECK_HMAC=true` actually set as a wrangler secret on the deployed Worker? Not verifiable from repo.
3. **LAN trust** — is the Docker/host network truly private (no untrusted devices)? Determines whether #10–12 are HIGH or acceptable. Are ports 3000–3007 firewalled on the host?
4. **Google Sheet IDs** in `config.toml` — are those sheets org-restricted or world-readable?
5. **Marts intent** — `fact_order_transitions` / `mart_hug_optin`: meant to be served (then fix #5) or warehouse-only by design?
6. **`realized_margin_pct` availability** — present in the serving `fact_order_economics`, or only warehouse? (gates the Evidence/detailView swap)
7. **Evidence DuckDB session TZ** — does Evidence inherit `SET TimeZone='Asia/Ho_Chi_Minh'` from the copied catalog, or open UTC? Determines if `ceo-weekly-pulse` `AT TIME ZONE` calls are correct or double-converting.
8. Orphan dbt models (`src_sapo_v2_purchase_orders`, `stock_adjustments`) — future integration or dead?

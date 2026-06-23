# Health Audit — Consolidated Executive Report

**Date:** 2026-06-23 · **Scope:** full monorepo (ingestion → transformation → orchestration → serving → CRM app → CRM sync → infra)
**Method:** 6 parallel read-only Sonnet audits, each pre-loaded with project landmine history. Two highest-stakes CRITICALs verified by hand.

Sub-reports (detail + file:line for every finding):
- `audit-ingestion-webhook-260623-1843-report.md`
- `audit-transformation-serving-260623-1843-report.md`
- `audit-orchestration-260623-1843-report.md`
- `audit-crm-app-260623-1843-report.md`
- `audit-crm-sync-migrations-260623-1843-report.md`
- `audit-infra-docker-config-260623-1843-report.md`

Raw totals: **10 CRITICAL · 29 HIGH · 36 MEDIUM · 29 LOW** (before dedup/verification).

---

## Verification corrections (don't act on these blindly)

| Finding | Agent severity | Verified status |
|---|---|---|
| Ingestion C1 — bare `"sapo"` source_system "breaks all dbt filters" | CRITICAL | **DOWNGRADE → LOW.** dbt hardcodes `'sapo_v2' as source_system` in every `std_*` model (verified `std_orders.sql:29`, `std_customers.sql:18`, +10 more); it ignores ingestion `sync_metadata.source_system`. No downstream data loss. Real issue is only cosmetic drift in raw metadata. |
| CRM C1 — campaign/segment service contract mismatch | CRITICAL | **CONFIRMED REAL.** `campaign_service.py:73 create_campaign(self, data: dict)` but screen calls with kwargs; `record_conversion/update_target_status/get_target` do not exist. Routes crash on first hit. |

---

## Cross-cutting themes (fix the pattern, not just instances)

1. **Timezone discipline is drifting in 3 subsystems** — naive `datetime.utcnow()` in ingestion (all sources), `date_key` derived without explicit ICT cast in `fact_orders`/`fact_sales`, and bare ICT timestamps (no `Z`/offset) written by CRM sync. Project convention is UTC TIMESTAMPTZ → display ICT. Each drift point silently mis-dates 0h–7h records.
2. **Swallowed exceptions masking failures** — ingestion, CRM app (the L140 empty-render class), and CRM sync (broad `OperationalError` catch). Same failure mode keeps recurring: error hidden → stale/empty output looks "successful".
3. **Secrets hygiene** — live token in plaintext backups + a `change-me` default token committed in `docker-compose.yml`. Highest real-world urgency, fastest to fix.
4. **DuckDB write-lock surface** — serving-build assets and backup op lack the `duckdb_lock` slot; metabase/rill mount `data_lake` read-write. Lock storms have bitten this project before.
5. **API contract mismatches in CRM web layer** — several screen→service calls don't match service signatures; pure runtime crashes waiting for the first request.

---

## CRITICAL — verify-then-fix first

| # | Area | Finding | Location |
|---|---|---|---|
| 1 | CRM app | Campaign routes crash — service methods missing / wrong call shape (VERIFIED) | `screen_management.py:295,310,311`; `campaign_service.py:73` |
| 2 | CRM app | `sqlite3` imported + raw SQL in application layer (hexagonal breach) | `application/segment_service.py:12`, `campaign_service.py:6` |
| 3 | CRM app | Unauthenticated FB Messenger webhook ingest (no HMAC) | `inbound/http/conversation_handler.py:104` |
| 4 | Infra | Live Cloudflare API token in plaintext backups (DNS-01 cert control) — **rotate if live** | `app_data/backups/202606*/config/.env.docker` |
| 5 | Infra | `CRM_REFRESH_TOKEN=change-me-crm-refresh` default committed | `docker-compose.yml:171` |
| 6 | Transformation | `std_payments.payment_method_type` hardcoded `'CASH'` → COD segmentation always wrong | `std_payments.sql:21` |
| 7 | Transformation | `int_customer_metrics` incremental watermark compares wrong columns → late order updates skip recompute | `int_customer_metrics.sql:36` |
| 8 | Ingestion | Webhook consumer ACKs D1 before dlt load completes → at-most-once, data loss on crash | `webhook_consumer.py:211-212` |
| 9 | Ingestion | D1 lock TTL 60s but consumer batch often exceeds it → duplicate parquet rows | `webhook_receiver/cloudflareD1/src/index.ts:216` |
| 10 | Orchestration | Backup op can `cp` a live DuckDB mid-write (serving assets hold no lock slot) | `definitions.py:94-99`, `serving.py:102-165` |

## HIGH — schedule next

- **Transformation:** `scope_retail` defaults unknown customers to RETAIL without `Đại Lý` exclusion (~92 dealers leak, inflates all retail KPIs) — `fact_orders.sql:184-187`. `date_key` ICT-cast reliance — `fact_orders.sql:147`, `fact_sales.sql:58`. Sentinel-row dup risk untested — `dim_customers_base.sql:68`.
- **Orchestration:** serving-build assets missing `duckdb_lock` key — `serving.py`. `dbt parse` runs outside the lock slot — `dbt.py:138`. File-drop sensor cursors grow unbounded — `file_drop_sensors.py:53-104`. Process-wide `os.chdir` — `sapo_assets.py:63-67`.
- **Ingestion:** consumer sends default `python-requests` UA (Cloudflare Bot Fight 403 risk) — `webhook_consumer.py:29,51`. Naive `utcnow()` everywhere.
- **CRM app:** `TaskQuerier` protocol param `party_id` vs `assignee_id` (L140 bug class) — `screen_worklist.py:41`.
- **CRM sync:** broad `OperationalError` swallow in column migrations — `sqlite_upsert.py:67-72`. `entrypoint.sh` serves on half-migrated DB — `entrypoint.sh:11-15`. FTS rebuild wipes with no rollback — `search_index.py:195-198`. Bare ICT timestamps — `duckdb_reader.py:323,413`.
- **Infra:** `CRM_DEV_RELOAD=1` + `dagster dev` in prod (`docker-compose.yml:45,174`); metabase/rill mount `data_lake` RW (`:64,85`).

## MEDIUM / LOW

See sub-reports. Themes: missing healthchecks/resource limits, loose throwaway scripts at repo root (`_tmp_gift_check.py`, `check_*.py`), files >200 LoC, N+1 queries in CRM screens, untested critical dbt models, `fact_payments` empty-assumption guards.

---

## Suggested action order

1. **Now (minutes):** rotate Cloudflare token; replace `change-me-crm-refresh`; remove `CRM_DEV_RELOAD`/`dagster dev` from prod compose. (Infra #4,#5, HIGH)
2. **This week:** fix CRM crashing routes (#1) + hexagonal breach (#2) + Messenger HMAC (#3); add `duckdb_lock` to serving/backup assets (#10).
3. **Data-correctness sprint:** `std_payments` CASH bug (#6), `int_customer_metrics` watermark (#7), `scope_retail` Đại Lý exclusion, webhook at-most-once + D1 TTL (#8,#9).
4. **Systemic hardening:** one timezone-helper pass across the 3 drift points; ban broad exception swallows (narrow + re-raise).

## Unresolved questions

1. Is the Cloudflare token in backups still the **live** one? (decides rotation urgency)
2. `profiles.yml` dbt `threads` value — if >1, concurrent DuckDB writes possible inside dbt itself (orchestration unresolved Q1).
3. Is `sync_metadata.source_system` read by ANY consumer (Metabase/CRM/detailView) directly? If no → ingestion bare-`sapo` is pure cosmetic; if yes → revisit.
4. Do serving-build scripts open DuckDB in write mode? (sets true severity of orchestration #10).
5. FB Messenger webhook — is it actually reachable from outside LAN, or Caddy-internal only? (sets severity of CRM #3).

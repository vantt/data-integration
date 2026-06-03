# Sapo Inventory Transactions v2 — Ingestion Pipeline

> New date-windowed ingestion for Sapo inventory in/out transactions, wired into dlt → dbt(src_) → Dagster (hourly + nightly), then full backfill, then data analysis → std_ design.

**Source endpoint:** `GET /admin/reports/inventories/transaction.json?page=N&start_date=...Z&end_date=...Z`
**Response:** `{ "metadata": {total,page,limit}, "items": [ {issued_at_utc, log_root_id, log_type(_name), trans_type(_name), trans_object_code, product_id, variant_id, sku, location_id, location_label, import_quantity, import_amount, export_quantity, export_amount, onhand, amount, mac, total_mac, source, ...} ] }` — sorted **newest-first**, 1 row per (document × product line).

## Key design decisions (confirmed)
- **Backfill:** all history — Phase 0 probes earliest date, then chunk backward per-day.
- **Hourly window:** current + previous hour (overlap for late/corrected rows). **Nightly:** full current ICT day re-fetch (final reconciliation).
- **Timezone:** window boundaries computed in **ICT (Asia/Ho_Chi_Minh, UTC+7)** then converted to **UTC** for `start_date`/`end_date`.
- **Verify:** after each step, manual-launch the relevant Dagster job in `data_platform` container, watch to SUCCESS, read logs. No errors tolerated before next step.
- **No incremental cursor:** the date window *is* the filter — fetch all pages in-window to exhaustion; append; dbt dedups.

## Naming (everything `v2`)
| Thing | Name |
|---|---|
| Source module | `ingestion/src/sapo/inventory_transactions_v2.py` (+ `_inventory_v2_window.py` helper) |
| Run script | `ingestion/run_inventory_transactions_v2_batch.py` |
| dlt pipeline | `sapo_inventory_transactions_v2_batch` |
| Table / dlt resource | `inventory_transaction_v2` |
| Parquet path | `app_data/data_lake/sapo_raw/inventory_transaction_v2/ingest_method=batch_sync/year=Y/month=M/` |
| dbt source table | `inventory_transaction_v2` (sources.yml → sapo_raw) |
| dbt src model | `src_sapo_inventory_transactions_v2.sql` |
| Dagster asset | `sapo_inventory_transactions_v2_asset` (group `sapo_ingestion`, prefix `sapo`) |
| Dagster job | `ingest_sapo_inventory_v2_hourly_job` |
| Dagster schedule | `ingest_sapo_inventory_v2_hourly_schedule` |

## Envelope schema (mirrors `products.py`, composite id)
- `entity_id` = md5(`{log_root_id}|{trans_type}|{product_id}|{variant_id}|{location_id}|{issued_at_utc}`) — stable line identity.
- `entity_type`="inventory_transaction"; `ingest_method`="batch_sync"; `event_type`=trans_type_name; `event_timestamp`=issued_at_utc; `payload_hash`=md5(sorted item) (catches onhand/mac recompute); `year`/`month` from issued_at_utc; `payload`=full item; `sync_metadata`={source_system:sapo, source_version:v2, window_start/end,…}.
- `write_disposition="append"`, `primary_key="entity_id"`, plain parquet (like orders/products).

## Phases (each = small step + Dagster verify)
| # | Phase | File | Verify gate |
|---|---|---|---|
| 0 | Live probe: response shape, `limit` param ceiling, earliest-data date | `phase-00-probe.md` | probe prints valid JSON, no auth error; report written |
| 1 | Ingestion source + run script + window logic; local test run | `phase-01-ingestion.md` | LoadInfo OK, parquet lands, rows>0, sample row inspected |
| 2 | dbt: sources.yml + `src_` model + schema.yml; build | `phase-02-dbt-src.md` | `dbt build` model SUCCESS, rows sane |
| 3 | Dagster: asset + translator + hourly job/schedule + nightly include | `phase-03-dagster.md` | `definitions validate` OK; **manual job launch → SUCCESS**, no errors, new parquet |
| 4 | Full backfill (all history), chunked per-day; src full-refresh | `phase-04-backfill.md` | backfill completes, all year/month partitions, counts vs metadata sampling |
| 5 | Analyze data nature → design `std_`/`stg_`/marts (own follow-up plan) | `phase-05-analyze-design.md` | analysis report; std design spec |

## Orchestration
- Implementation steps delegated to **sonnet `fullstack-developer`** agents (one focused phase/step at a time, strict file ownership).
- **Verification driven by main agent** via `docker exec data_platform …` (launch + watch + log read) — kept in controller per user's "wait for a new Dagster run, ensure no errors".
- Sequential: each phase's Dagster verify must pass before next phase starts.

## Constraints
- Container path = `/app/...`; host = `D:\vantt\app\data-integration\...`. dlt writes via `DESTINATION__FILESYSTEM__BUCKET_URL=file:///app/var/data_lake`.
- Ingestion assets get **NO** `duckdb_lock` (parquet writes); dbt assets keep it.
- Hourly schedule must yield to nightly/full-refresh (mirror existing `_long_dbt_rw_holder` guards) and use offset minute to avoid start-time races.
- Files <200 LOC → modularize window/date helpers.
- std_/marts design deferred until real data analyzed (Phase 5).

## Open questions
- `limit` param ceiling unknown (default 20) — resolved in Phase 0 probe.
- Whether `dagster job launch` CLI enqueues into the running `dagster dev` daemon — confirmed in Phase 3 (fallback: GraphQL trigger).

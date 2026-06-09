# Handoff — Order-P&L pipeline COMPLETE; next = detailView (phase-06) + refinements

> Paste to continue. Repo `D:\vantt\app\data-integration` (dlt+dbt+Dagster+DuckDB; Docker `data_platform`; Metabase; detailView FastAPI). Everything below committed+pushed to `main`. System healthy (containers up, schedules SUCCESS, tree clean).
> **Standing rules this workstream:** (1) delegate all implementation to **sonnet sub-agents** (orchestrator keeps: deciding/spec, Dagster verify, commit, relay). (2) **Verify every Dagster-affecting change with a real Dagster run, zero errors.**

## ✅ DONE (full per-order P&L waterfall, live + verified)
```
net_revenue − COGS = gross_profit − promo_goods_cost − platform/discount = channel_net_profit (DECISION)
                                                          − allocated_overhead = fully_loaded_net_profit (REPORT)
```
- **Đợt đầu**: BUG-1 (TK632 COGS filter) + phase-07 Shopee (service-fee de-dup, payment_fee, drift guard).
- **Phase-01** `std_misa_sales_lines` std-gate · **Phase-02** `int_order_cogs_reconciled` (Sapo-MAC vs MISA-632) · **Phase-03** `int_order_promo_goods_cost` + `int_promo_642_monthly_total`.
- **Phase-04 overhead** (this session):
  - MISA **account-ledger ingestion** (`Sổ chi tiết các tài khoản` 6421/6422): `ingestion/src/misa_amis/account-ledger-parser.py` (section-based, drops parent-rollup double-count, checksum, 911 guard) + `run-misa-account-ledger-file-drop.py` (UPSERT replace-touched-months) + Dagster asset/sensor/job (`ingest_filedrop_misa_account_ledger_job`, sensor watches `app_data/input_source/misa-account-ledger/`) + `src`/`std_misa_account_ledger` (grain account×month, net=Nợ−Có-excl-911). **Renamed** `misa-amis/` → `misa-sales-ledger/`.
  - **Classification gsheet ingestion** (nightly): `gsheet_overhead_classification.py` + `sheets_overhead_classification_asset` + `stg_overhead_account_classification` (in `_nightly_batch_selection`). Sheet `1fwdyzIdyXRkFva7FHgxwCPiQOY8s3m4MDATMsGY0YKM` (public). Seed/draft: `docs/architecture/order-pl/overhead-account-classification-seed.csv`.
  - **Allocation engine**: `int_overhead_pool_monthly` (Σ keep_* net_cost per pool×month) + `int_order_overhead_allocation` (pro-rata per order×pool by base; fulfilled = `first_shipped_at IS NOT NULL OR status='COMPLETED'`; source = **fact_orders** to avoid cycle) + closure test (Σ alloc==Σ pool, exact).
  - **Facts**: `fact_order_economics` += `allocated_overhead, is_overhead_estimated, fully_loaded_net_profit` (= channel_net_profit − overhead, conditional/NULL when no overhead), `fully_loaded_margin_pct`; `fact_order_costs` += OVERHEAD rows (`overhead_<pool_id>`). channel_net_profit UNCHANGED (tiers separate).
- **Decisions** Q1–Q5 + **TT133** (642 = 6421 bán hàng + 6422 G&A) + 3 treatments locked. Docs: `docs/architecture/order-pl/` — `overhead-cost-allocation-design.md` (§Quyết định Q1–Q5), `overhead-account-ledger-ingestion-design.md`, `overhead-allocation-and-classification-guide.md` (gsheet cột + công thức + ví dụ).

**Key numbers (current data ~2026-01..06):** account-ledger Σ debit 1,021,499,685; pool (keep) 767,042,390 = admin 641.8M + marketing 85.26M + selling 37.63M + handling 2.34M; 662 fulfilled orders get overhead; closure exact. `is_overhead_estimated`=FALSE everywhere (all actual).

**Classification (live gsheet → nightly):** 64211→keep_handling/handling/order_count · 64213→keep_admin · 64214→drop_promo_count_once (hàng tặng, count-once w/ promo) · 642172→keep_marketing · 642174/642176→drop_traceable (ship/sàn = tier-2) · 642175→keep_selling/selling · 642177/642178/6422→keep_admin. (admin/marketing/selling base=net_revenue; handling base=order_count.)

## ✅ Phase-06 — detailView Financial tab — COMPLETE
Commits 18af69c (2026-06-06) + dffdde4 (2026-06-07). All 5 zones implemented:
1. Verdict bar (margin verdict + source badge)
2. Composition bar (revenue breakdown)
3. P&L waterfall (gross_revenue → net_revenue → COGS → gross_profit → channel_net_profit → fully_loaded_net_profit)
4. Cost breakdown ledger (platform fees, overhead allocations, promo_goods_cost)
5. COGS reconciliation (Sapo-MAC vs MISA-632 comparison)

New financial fields confirmed live in `detailView/app/domain/order.py`: `promo_goods_cost`, `cogs_source`, `allocated_overhead`, `is_overhead_estimated`, `fully_loaded_net_profit`, `fully_loaded_margin_pct`.

## ⏭ NEXT — Pipeline refinements (optional, not blocking phase-06)

### Pipeline refinements (optional, not blocking phase-06)
- **P4-3 provisional estimate** (Q4-B): trailing-rate for the CURRENT unclosed month + flip `is_overhead_estimated`. Only matters live; all current data is actual.
- **P4-5 reconcile**: tie-out MISA 64214 (103M) vs sales-ledger-642 (1.08B) vs Sapo-MAC promo (`int_promo_642_monthly_total`) — confidence on count-once.
- **Phase-05 COGS repoint**: `fact_order_economics.cogs_amount` still uses the BUG-1 interim filter (`int_misa cost_account LIKE '632%'`), NOT yet repointed to `int_order_cogs_reconciled.cogs_goods_primary` (Sapo-MAC primary) + `cogs_source`. CONTRACT wants Sapo-MAC primary. Touches shared facts.
- **Metabase P&L dashboard** (phase-05 serving part).

## ⚠ Gotchas (operational — read before pipeline work)
- **NEW dbt node (model/test) → `docker restart data_platform`** before a Dagster run (manifest pre-parsed at startup, not hot-reloaded) else dagster-dbt KeyError reds the run. SQL edits to EXISTING models are live (volumes mounted). A NEW dependency EDGE (model A now refs model B) also needs a restart so `.downstream()` selection is correct.
- **NEW rolling model (marts/ or intermediate/ with `get_rolling_location()`) → serving SCHEMA_DRIFT** → `bootstrap_serving_views.py` with **Metabase + detail_view STOPPED** (`docker stop metabase detail_view` → bootstrap → `docker start`). Adding COLUMNS to an existing rolling fact also needs a bootstrap so the serving view exposes them. Direct `dbt build` of a NEW rolling model first needs the rolling dir: `mkdir -p export/marts/rolling/<model>` (the Dagster dbt asset auto-creates it, a direct build doesn't).
- **Warehouse single-writer**: direct `dbt build` fails with "Conflicting lock" while a Dagster run holds `sapo_warehouse.duckdb` — retry loop, or read rolling parquet directly. Read-only warehouse query: `duckdb.connect(path, read_only=True)`; schemas `main`/`main_marts`/`main_staging`.
- **File-drop UPSERT** (account-ledger): drop `.xlsx` in `misa-account-ledger/` → sensor (~5min tick) → upsert (replace touched months). MISA lists each txn under BOTH parent (64217) AND leaf (642174) accounts → parser drops parent-rollups (line-sum==Σ descendants). `write_partitioned_parquet` is append-only per-second-ts → re-ingest one file per process (memory: file-drop collision).
- **Shared facts** `fact_order_economics/costs` = concurrent-stream territory → `git pull --rebase` before editing; `git add` only your files.
- **DuckDB date_key** is INTEGER YYYYMMDD → `strptime(CAST(date_key AS VARCHAR),'%Y%m%d')::DATE` (plain CAST needs YYYY-MM-DD).
- **Cycle**: anything feeding the per-order facts must read the order base from `fact_orders` (upstream), NOT `fact_order_economics` (which consumes downstream models).
- Sapo VAT-inclusive (net=total−vat); ICT timezone; Sapo-MAC = COGS authority.

## Read to resume
`plans/260604-1030-unified-order-pl-cogs-overhead/plan.md`; `docs/architecture/order-pl/` (4 docs + README); `detailView/docs/design` (phase-06); `design-prompt-financial-tab.md`; this handoff.

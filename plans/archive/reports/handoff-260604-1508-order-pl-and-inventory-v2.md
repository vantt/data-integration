# Session Handoff — Sapo Inventory v2 + Unified Order-P&L

> Paste this to continue in a new session. Repo: `D:\vantt\app\data-integration` (dlt + dbt + Dagster + DuckDB; Docker container `data_platform`; Metabase; detailView FastAPI app). Everything below is committed & pushed to `main`.

## ✅ DONE this session

### 1. Sapo Inventory Transactions v2 — ingestion pipeline: BUILT, LIVE, verified
- New **date-windowed** dlt source (endpoint `/admin/reports/inventories/transaction.json`, ICT→UTC windows, `limit=250`), content-addressed `entity_id`. Files: `ingestion/src/sapo/inventory_transactions_v2.py` (+ `_inventory_v2_window.py`), `ingestion/run_inventory_transactions_v2_batch.py`. Table `inventory_transaction_v2`.
- **Backfilled all history 2021-05 → now = 32,957 rows** (matches probe exactly).
- dbt: `src_sapo_inventory_transactions_v2` → `std_inventory_movements` → marts `fact_inventory_movements` (31,533) + `fact_inventory_balance` (sparse effective-dated stock ledger, 17,616 rows — replaced a dense 1.9M-row daily snapshot that was 99% redundant).
- Dagster: `sapo_inventory_transactions_v2_asset` + `ingest_sapo_hourly_job`/schedule (`:25`, current+prev hour) + included in nightly full-day; all verified by real Dagster runs SUCCESS. Serving views bootstrapped (Metabase queries OK). **Schedules RUNNING.**
- Plan `plans/260603-2307-sapo-inventory-transactions-v2-ingestion/`; analysis `plans/reports/analysis-260604-0001-inventory-v2-data-nature.md`.
- Data facts: `trans_type=301`=sale fulfillment (the sales COGS); `onhand`=authoritative running balance; `mac`=moving-avg cost; `export_amount`=COGS; `document_code`↔`order_code`; promo/gift goods ride inside 301 (no separate trans_type).

### 2. Unified Order-P&L — DESIGNED & PLANNED ONLY (no code yet)
- Design docs consolidated: `docs/architecture/order-pl/` (README + cogs-reconciliation-design.md + overhead-cost-allocation-design.md + order-pl-schema-design.md + discount-classification.md). Cross-cutting `std-layer-conventions.md`/`naming-conventions.md` stay in `docs/architecture/`.
- Master plan + 7 phases: `plans/260604-1030-unified-order-pl-cogs-overhead/` (plan.md = the CONTRACT).
- **Locked decisions (CONTRACT):** P&L = `net_revenue − COGS = gross_profit − promo − fees − discount = channel_net_profit(★decision) − overhead = fully_loaded(report)`. COGS = **Sapo-MAC primary**, sold-lines only (**Option A**: gifts/revenue=0 → `promo_goods_cost`, NOT COGS), MISA-632 = reconciliation only. **COUNT-ONCE** for promo-642. Add `std_misa_sales_lines`. Closure test. Verify each phase via Dagster run.
- **Key findings:** MISA "Giá vốn" is mixed (95.2% TK632 + 4.8% TK642 promo-goods); cash overhead (real TK642/641/635) NOT ingested yet.

### 3. detailView Financial-tab redesign — prompt + mockup READY (not implemented)
- Mockup (current vs proposed): `plans/260604-1030-.../mockups/financial-tab-current-vs-proposed.html`.
- Design prompt: `plans/260604-1030-.../design-prompt-financial-tab.md` (EN labels + VN tooltips per `revenue_terminology.md`; keep VAT bridge; composition bar; decision-first; reuse macros; main-section only).
- Per-line COGS/margin → goes on Items tab (companion), not Financial.
- `revenue_terminology.md` §4 updated (COGS now available). Coordination report `plans/reports/coordination-260604-1435-order-pl-rename-sync.md`.

## ⏳ NEXT — nothing implemented yet; recommended order
1. **Tier-correctness FIRST (before overhead):**
   - **BUG-1** (phase-02): filter `cogs_account LIKE '632%'` in `fact_order_economics.sql:32` + `fact_order_costs.sql` (drops ~1.08B promo from COGS).
   - **phase-07**: Shopee fee fixes — BUG-2 (service-fee double-count: use F `order_service_fees` detail, drop D aggregate), BUG-3 (payment_fee column rename `Phí thanh toán`→`Phí xử lý giao dịch`), + schema-drift guard in `income-parser.py`.
2. **phase-01**: `std_misa_sales_lines` (faithful, keep accounts + `cost_account_group`); ingest MISA monthly overhead (`overhead_costs_monthly`) + gsheet `overhead_allocation_config`.
3. **phase-02**: `int_order_cogs_reconciled` (Sapo-MAC primary + MISA-632 variance).
4. **phase-03**: `promo_goods_cost` (revenue=0 split, incl gift-no-invoice) + count-once.
5. **phase-04**: `int_order_overhead_allocation` (closure-based) + `fully_loaded_net_profit`.
6. **phase-05**: unify `fact_order_economics`/`fact_order_costs` + serving + Metabase P&L.
7. **phase-06**: detailView P&L (apply design prompt) — **only after concurrent detailView stream merges.**

## ⚠ CRITICAL gotchas
- **CONCURRENCY:** another active workstream commits to `main` under the same git identity (P1/P2 renames, overhead design, detailView **customer** pages — e.g. cascade commit `997fc5c`). **Always `git pull --rebase origin main` before editing.** `fact_order_economics.sql`/`fact_order_costs.sql`/`detailView` are shared → coordinate; do NOT edit detailView until their stream merges. (Earlier their commits interleaved & knocked a staged deletion out of my index — re-verify after committing.)
- **Runtime:** Dagster in Docker `data_platform` (NOT `nu-*` containers — different system). Commands: `MSYS_NO_PATHCONV=1 docker exec ... data_platform ...` (Git-Bash mangles `/app/...` paths without the prefix). A scout hook blocks Bash paths containing `target`.
- **DuckDB single-writer:** pause the 3 dbt-writing schedules before direct `dbt build` (reset via GraphQL `resetSchedule`, or CLI), wait for active runs to drain, build, then resume (`startSchedule`). Verify via `dagster job launch -j <job> -f orchestration/definitions.py` then poll `DagsterInstance.get_run_by_id`.
- **Serving:** new marts → `ensure_dbt_directories.py` auto-creates rolling dirs (scans `marts/**`); run `refresh_rolling.py` (lock-free, updates `.known_tables.json` — else nightly serving asset FAILS on SCHEMA_DRIFT) + `bootstrap_serving_views.py` (needs olap.duckdb write lock; **Metabase holds it** → `docker stop metabase detail_view` briefly, bootstrap, restart).
- **Domain:** Sapo prices VAT-inclusive (`net_revenue = total − vat`); COGS on net (VAT-excluded) basis; ICT timezone for windows/date_key. **Verify every change with a real Dagster run, zero errors** (hard user requirement).

## ❓ Open decisions (need user)
- Overhead (phase-04 prereqs): MISA API vs export; pool scope (642 / +635 / +641-common); allocation base; realtime+true-up vs closure-only; do cancelled orders carry overhead?
- COUNT-ONCE: does the MISA monthly-642 export overlap the sales-ledger-642 promo? (needs a real Sổ cái TK642 export to confirm whether the deduction is a no-op).
- Shopee: confirm the 4 Apr-2026 orders in sheet D without sheet-F rows have `service_fee=0` before deploying phase-07.

## Read to resume
`plans/260604-1030-unified-order-pl-cogs-overhead/plan.md` → phase files; `docs/architecture/order-pl/README.md` + 4 design docs; the 3 analysis/coordination reports in `plans/reports/`; `AGENTS.md` + `transformation/AGENTS.md`.

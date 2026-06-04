# Session Handoff — Order-P&L phases 01–03 DONE + overhead decisions locked

> Paste to continue next session. Repo `D:\vantt\app\data-integration` (dlt+dbt+Dagster+DuckDB; Docker `data_platform`; Metabase; detailView). Everything below committed+pushed to `main`. **Blocker for next step (phase-04): waiting on a real MISA Sổ cái TK642 export (expected tomorrow).**

## ✅ DONE this session (8 commits pushed to main)

| Commit | Scope |
|---|---|
| `f4f5783` | **Đợt đầu**: BUG-1 (TK632 COGS filter in fact_order_economics/costs) + phase-07 Shopee (service-fee de-dup, payment_fee rename fix, schema-drift guard, guard test) + clean re-ingest (fixed pre-existing dup parquet months 2-4) |
| `62f2a96` | **Phase-01** std-gate: `std_misa_sales_lines` (faithful + `cost_account_group`) + repoint `int_misa_sales_lines` |
| `c1ce768` | **Phase-02**: `int_order_cogs_reconciled` (Sapo-MAC vs MISA-632 recon, var-driven `cogs_goods_primary`, default sapo_mac) |
| `ae03b58` | **Phase-03**: `int_order_promo_goods_cost` + `int_promo_642_monthly_total` (count-once helper) + fact_order_costs PROMO_GOODS rows + fact_order_economics `promo_goods_cost` col |
| `50d45c0`,`2503b74`,`5da5549` | **Overhead decisions Q1–Q5** locked in `docs/architecture/order-pl/overhead-cost-allocation-design.md` (full reasoning) |

Every code phase verified by a **real Dagster run, zero errors** (shopee/misa filedrop jobs) + dbt tests. Bugs caught during verify (not by agents): UNION alias drop, same-second parquet overwrite, NULL-propagation in return-netting, is_gift_no_invoice over-count — all fixed + re-verified.

## 🔒 Overhead decisions (CONTRACT for phase-04) — see design doc §Quyết định Q1–Q5
- **Q1 source:** MISA **export thủ công** Sổ cái TK642 (`source='misa_export'`); API=v2; estimate tạm allowed when no data.
- **Q2 pool scope:** **TK642 only** (net of 642-promo, count-once); −635 (lãi vay) **excluded**; +641-common **deferred v2** (TODO: map traceable vs common sub-accounts first).
- **Q3 base:** **2-pool ABC-lite** — handling pool→`order_count`, admin pool→`net_revenue`. Reject gross_profit base. Full-ABC deferred. v0 fallback = single net_revenue pool w/ "under-costs small orders" caveat.
- **Q4 timing:** **B = Closure-only + light provisional** — actual after MISA close; trailing-rate estimate for the open month flagged `is_overhead_estimated`, overwritten by actual on close (NO variance booking / restatement, ~1.2x not 2x).
- **Q5 cancelled/returned:** base = **fulfilled orders**; cancel-pre-fulfill excluded; returns keep their allocation (reverse cost stays tier-2 direct); RTO/cancel-post-fulfill included. Don't bury churn cost in overhead → separate KPI.

## 📋 Plan status (`plans/260604-1030-unified-order-pl-cogs-overhead/plan.md`)
- Phase 00 decisions ✅ · 01 ✅ · 02 ✅ · 03 ✅ · **04 ⏳ blocked on data** · 05 (waterfall repoint) waits 04 · 06 (detailView) waits concurrent detailView merge.

## ⏭ NEXT — Phase-04 (overhead allocation). BLOCKED until TK642 export arrives.
When the **MISA Sổ cái TK642 export** lands, do (per phase-04 file + Q1–Q5):
1. **Ingest `overhead_costs_monthly`** (file-drop pattern like `gsheet_marketing_spend.py`; `source='misa_export'`; partition year/month; schema in design §Phase-01).
2. **Count-once empirical check (THE critical step):** inspect whether the Sổ cái TK642 total INCLUDES the ~1.08B sales-ledger-642 promo (already in tier-2a `promo_goods_cost`). If YES → subtract `int_promo_642_monthly_total.sales_ledger_642_amount` from the pool. If the export's 642 is a distinct sub-account excluding promo → NO subtraction. **Do not apply the deduction blind.**
3. **Ingest `overhead_allocation_config`** gsheet (pool_id, account_pattern, base_metric, effective_*) — set up 2 pools per Q3 (handling→order_count, admin→net_revenue) IF the 642 pool can be split into handling vs admin via sub-accounts; else v0 single net_revenue pool + caveat.
4. **`int_order_overhead_allocation`** (closure-based): base = fulfilled orders (Q5); allocate pool per pool/base; closure dbt test `SUM(allocated)==pool_net`. Provisional trailing-rate for open month, flag `is_overhead_estimated` (Q4-B).
5. **Add `allocated_overhead` + `fully_loaded_net_profit`** to fact_order_economics + OVERHEAD rows to fact_order_costs (ADD only; keep channel_net_profit separate per CONTRACT §3).
6. **Verify with a real Dagster run, zero errors** (hard requirement).

Then **Phase-05** (do ONCE, after 04): repoint fact_order_economics waterfall — cogs_amount → `int_order_cogs_reconciled.cogs_goods_primary` (Sapo-MAC, removes BUG-1 interim filter); add `promo_goods_cost` + platform/discount + `allocated_overhead` into the waterfall (channel_net_profit then fully_loaded). Resolve the ~4 edge lines (revenue=0 but MISA-632-booked) during repoint. Then serving + Metabase P&L. **Don't do phase-05 piecemeal** — it touches the shared fact waterfall; one pass after 04 avoids editing it twice.

**Phase-06** detailView P&L: design prompt READY at `plans/260604-1030-.../design-prompt-financial-tab.md` + mockup `mockups/financial-tab-current-vs-proposed.html`. Do AFTER the concurrent detailView (customer pages) stream merges.

## ⚠ Gotchas (updated — read before touching pipeline)
- **NEW dbt node (model/test) → MUST `docker restart data_platform`** before a Dagster run, else dagster-dbt KeyErrors on the unknown node (manifest pre-parsed at startup, not hot-reloaded). SQL edits to EXISTING models are live (volumes mounted). [memory: feedback_dbt_node_needs_manifest_reload]
- **NEW rolling model (intermediate/ or marts/ with `get_rolling_location()`) → serving SCHEMA_DRIFT** → must `bootstrap_serving_views.py` with Metabase+detail_view STOPPED, else the `sapo_serving_db` asset raises. (dbt.py pre-creates a rolling folder for EVERY model in marts/+intermediate/, so even a plain `materialized='table'` there trips drift — just use the rolling-parquet config like siblings.)
- **File-drop re-ingest:** `write_partitioned_parquet` is append-only with per-SECOND filename ts → re-ingesting multiple files in one process to the same month silently overwrites. Re-ingest **one file per process** with a gap. [memory: project_filedrop_same_second_collision]
- **Shared fact files** `fact_order_economics.sql`/`fact_order_costs.sql` = concurrent-stream territory → `git pull --rebase` before editing; `git add` ONLY your specific files when committing (a concurrent commit knocked a report deletion / file mod into my working tree twice this session).
- **Warehouse reads:** `sapo_warehouse.duckdb` is single-writer; read-only connect fails while a Dagster run holds it — retry, or read the rolling parquet directly. Marts in schemas: `main`/`main_marts`/`main_staging`/`main_intermediate`.
- Domain: Sapo VAT-inclusive (net=total−vat); ICT timezone; Sapo-MAC = COGS authority (~100% coverage), MISA-632 = recon-only.

## 🩺 System state (left healthy)
- Shopee data re-ingested clean (171 orders, no dup, service_fee dropped, payment_fee present incl. May).
- All phase 01–03 rolling models built + serving views bootstrapped; Metabase + detail_view UP.
- `data_platform` restarted 3× this session; schedules resumed via cron (realtime/incremental/hourly firing normally; DAGSTER_HOME state persisted).
- `int_promo_642_monthly_total` Σ=1,076,303,444 (53 months) ready for phase-04 count-once.

## ❗ Loose ends / open items
- **Dangling working-tree mod (NOT mine):** `docs/analytics-handbook/blueprints/ceo_weekly_pulse.md` modified (date-window SQL logic, 82±). Likely concurrent stream or a restart's `bootstrap_reporting.py`. Left untouched — owning stream to resolve (don't blindly commit/revert).
- Phase-04 open Qs (in phase-03/04 files): (a) expense-ledger-642 overlap (the empirical check above); (b) `int_promo_642_monthly_total` period uses MISA `posting_date` — confirm matches the Sổ cái fiscal period; (c) ~4 edge lines revenue=0 but MISA-632-booked (resolve in phase-05 repoint).
- 641-common v2: map TK641 sub-accounts (traceable→already tier-2 vs common→pool) before including.

## Read to resume
`plans/260604-1030-unified-order-pl-cogs-overhead/plan.md` → `phase-04-overhead-allocation.md`; `docs/architecture/order-pl/overhead-cost-allocation-design.md` (§Quyết định Q1–Q5 + §Phase-01 schema); this handoff.

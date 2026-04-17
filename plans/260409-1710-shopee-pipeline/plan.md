# Plan: Shopee Income Pipeline Integration

**Created:** 2026-04-09 17:10 (Asia/Saigon)
**Branch:** main
**Source:** `app_data/input_source/shopee/Income.*.xlsx` (manual file drop)
**Skill:** `/data-pipeline` (dlt → dbt → serving → Dagster)
**Pattern:** **C — Local File Drop** (variant of Pattern A, no API auth, Excel parser instead of HTTP)

## Context links

- Data description: `docs/shopee-integration/data-source-description.md`
- Skill reference: `.skills/data-pipeline/SKILL.md`, `checklist.md`
- Analogous existing source: `ingestion/src/gsheet_marketing_spend.py` (pandas → parquet, no native dlt)
- Source registry: `transformation/models/sources.yml`

## Objective

Ingest Shopee **released-income** Excel exports end-to-end so that per-order revenue, fees, taxes, and shipping subsidies are queryable in Metabase as `int_shopee_order_fees` (intermediate enrichment layer). This is NOT a primary fact — all orders already exist in Sapo `fact_orders`. Shopee data enriches them with platform fee breakdowns. P1 will join this into `fact_order_economics` for unified P&L.

## Phases

| # | Phase | Status | Evidence |
|---|---|---|---|
| 0 | Design spec (detailed) | ✅ DONE | `design-spec.md` |
| 1 | Excel parser + file-drop ingestion | ✅ DONE | `ingestion/src/shopee/income-parser.py` + `ingestion/run-shopee-income-file-drop.py` (archive-after-ingest wired) |
| 2 | dbt src_/stg_ models (4 entities) | ✅ DONE | `src_/stg_shopee_order_{revenue,revenue_items,service_fees,adjustments}.sql` |
| 3 | dbt intermediate: fees + items + adjustments | ✅ DONE | `int_shopee_order_{fees,items,adjustments}.sql` + schema.yml tests |
| 4 | Serving layer verification | ✅ DONE | Rolling parquet emitted at `data_lake/export/marts/rolling/int_shopee_*` (ts 20260416154233); bootstrap_serving_views.py auto-discovers |
| 5 | Dagster asset + reactive sensor | ✅ DONE | `orchestration/assets/shopee_assets.py`, sensor `ingest_filedrop_shopee_sensor`, `dbt.py` upstream keys incl. `src_shopee_order_adjustments` |
| 6 | E2E verification + Metabase probe | ✅ DONE — all 10 criteria pass after formula fix (SUM(net_settlement)=123,381,631 = Shopee Summary, diff 0) | `plans/reports/verify-260416-2248-shopee-phase6.md` |
| 7 | Adjustment sheet (promoted from P1 → P0, 2026-04-16) | ✅ DONE | `phase-adjustment-sheet.md` all 8 steps implemented; `int_shopee_order_fees` gained `total_adjustment_amount` + `net_settlement_adjusted` |

## Key decisions (locked in design-spec.md)

1. **Source key:** `shopee_raw` in `sources.yml`; entities `order_revenue`, `order_revenue_items`, `order_service_fees`.
2. **File watch:** reactive sensor on `app_data/input_source/shopee/*.xlsx` (mirror the existing sheets sensor pattern).
3. **Natural key:** `order_code` (Shopee Order SN). `row_seq` dropped.
4. **Grain split:** one Excel sheet → two logical tables (Order rows vs Sku rows).
5. **Incremental cursor:** `payout_released_at`; 7-day lookback; dedup on `(order_code)` for order-level, `(order_code, product_code)` for items.
6. **Model layer: `int_` (intermediate enrichment, NOT primary fact — LOCKED 2026-04-10).** `int_shopee_order_fees` = revenue LEFT JOIN service_fees ON order_code, surrogate key + rolling location. Named `int_` because all orders already exist in Sapo `fact_orders`; Shopee data adds fee breakdowns only. Rolling location applied pragmatically for P0 Metabase access. P1 will join into `fact_order_economics`.
7. **No dlt SDK** — pandas direct to parquet (filesize <1 MB, Excel not in dlt verified sources). Mirror `gsheet_marketing_spend` pattern.
8. **Append-only parquet writes (LOCKED 2026-04-09).** Filename includes `ingested_at_ts`; existing files never overwritten. Dedup happens at read time in dbt src_ via `ROW_NUMBER() OVER (PARTITION BY <business_key> ORDER BY ingested_at DESC)`. See `design-spec.md` § 2.6.
9. **Drop scope = discrete / non-overlapping windows (LOCKED 2026-04-09).** User confirmed Shopee exports are ad-hoc per-period drops, not always-from-fiscal-start snapshots. Therefore: **append-only forever** for normal ingests; full-refresh is opt-in only via explicit `--full-refresh-touched-months` CLI flag (used quarterly at most). Automatic full-refresh is BANNED — would silently destroy data when a small corrective drop touches a partition with many untouched rows. See `design-spec.md` § 2.7.

## Dependencies

- Environment var `DBT_DATA_LAKE_PATH` already set (reused).
- No new secrets (file drop, no API).
- New dep: `openpyxl` — add to `ingestion/requirements.txt`.

## Success criteria

- `SELECT COUNT(*) FROM int_shopee_order_fees` matches distinct order rows in the Excel file.
- `SELECT SUM(net_settlement) FROM int_shopee_order_fees WHERE payout_released_at BETWEEN ...` matches Shopee Seller Center "Tổng phát hành" within ±1 VND rounding.
- Dropping a new `.xlsx` file triggers the sensor → ingestion → dbt → serving within one DAG run.
- No serving "Empty folder" errors; Metabase can query `int_shopee_order_fees` without lock contention.

## P1 vision: `fact_order_economics` (unified P&L)

> **Locked 2026-04-10.** Both Shopee and MISA pipelines deliver `int_` (intermediate enrichment) models at P0. The unified fact is P1 scope.

```
fact_order_economics (P1, rolling, serving → Metabase):
  = fact_orders                          ← Sapo order event (base grain: 1 row/order)
    LEFT JOIN int_shopee_order_fees      ← Shopee platform fees, shipping, vouchers
              ON order_code
    LEFT JOIN int_misa_sales_lines       ← MISA COGS per line (aggregate to order level)
              ON voucher_no
  → Computes: net_revenue, total_platform_fees, total_cogs,
              gross_profit, gross_margin_pct, net_settlement
```

**Why separate fact, not enrich `fact_orders`:**
- `fact_orders` is in production with existing Metabase dashboards — adding 40+ columns = break risk
- Not all orders have Shopee data (only ECOM channel) or MISA data → many NULLs
- Different update cadence: Sapo real-time, Shopee/MISA weekly/ad-hoc

**Pre-requisites for P1:**
- Both Shopee and MISA P0 pipelines deployed and verified (Phases 1–6)
- `voucher_no` cross-source join validated: MISA `SON07xxx` ↔ Sapo `order_code`, MISA `2YYMMDD{14alnum}` ↔ Shopee `order_code`
- Decide: aggregate MISA line-level COGS to order level (SUM) or keep line granularity (change fact grain)

## Open questions

See `docs/shopee-integration/data-source-description.md` § 7.

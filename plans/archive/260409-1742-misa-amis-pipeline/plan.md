# Plan: MISA AMIS Sales Ledger Pipeline Integration

**Status:** ✅ COMPLETE (2026-04-19)
**Created:** 2026-04-09 17:42 (Asia/Saigon)
**Branch:** main
**Source:** `app_data/input_source/misa-amis/So_chi_tiet_ban_hang_*.xlsx` (manual file drop)
**Skill:** `/data-pipeline` (dlt → dbt → serving → Dagster)
**Pattern:** **C — Local File Drop** (same pattern as Shopee pipeline, no API auth, Excel parser)

## Context links

- Data description: `docs/misa-amis/data-source-description.md`
- Skill reference: `.skills/data-pipeline/SKILL.md`, `.skills/data-pipeline/checklist.md`
- Sibling precedent (most similar): `plans/260409-1710-shopee-pipeline/` — copy its shape, single-sheet variant
- Analogous existing file-drop code: `ingestion/src/gsheet_marketing_spend.py`
- Source registry: `transformation/models/sources.yml`
- MISA Open API reference (future alternative): `docs/misa-amis/README.md`

## Objective

Ingest MISA AMIS **Sổ chi tiết bán hàng** Excel exports end-to-end so that **per-line COGS (giá vốn)** is queryable in Metabase as `int_misa_sales_lines` (intermediate enrichment layer). This is NOT a primary fact — all orders already exist in Sapo `fact_orders`. MISA data enriches them with cost-of-goods-sold. P1 will join this + `int_shopee_order_fees` into `fact_order_economics` for unified per-order P&L.

## Phases

| # | Phase | Status | File |
|---|---|---|---|
| 0 | Design spec (detailed) | ✅ done | `design-spec.md` |
| 1 | Excel parser + file-drop ingestion | ✅ done | `ingestion/run-misa-sales-file-drop.py`, `ingestion/src/misa_amis/sales-ledger-parser.py` |
| 2 | dbt src_/stg_ models (1 entity) | ✅ done | `src_misa_sales_lines.sql`, `stg_misa_sales_lines.sql`, staging `schema.yml` tests |
| 3 | dbt intermediate: `int_misa_sales_lines` + channel code seed | ✅ done | `int_misa_sales_lines.sql`, `schema.yml` tests, `ref_misa_channel_codes.csv` |
| 4 | Serving layer verification | ✅ done | `bootstrap_serving_views.py` auto-discovered; verified in olap.duckdb (2026-04-16) |
| 5 | Dagster asset + reactive sensor | ✅ done | `misa_amis_assets.py`, `file_drop_sensors.py`, `definitions.py`, upstream keys in `dbt.py` |
| 6 | E2E verification + reconciliation | ✅ done | All checks pass (2026-04-16): 471 rows, 344 vouchers, revenue/COGS match, dedup OK, serving OK |
| 7 | P1 `fact_order_economics` | ✅ done | See `plans/260411-fact-order-economics/plan.md` — implemented 2026-04-11, shared with Shopee |

## Key decisions (locked in design-spec.md)

1. **Source key:** `misa_raw` in `sources.yml`; single entity `sales_lines`.
2. **File watch:** reactive sensor on `app_data/input_source/misa-amis/*.xlsx` (same pattern as the Shopee + Sheets sensors).
3. **Natural key:** synthesized `(voucher_no, line_no)` where `line_no = cumcount() + 1` per voucher — raw file has no single-column PK.
4. **Grain:** 1 row / invoice-line. **No grain split** (unlike Shopee which has Order vs Sku rows).
5. **Incremental cursor:** `posting_date`. **View materialization in src_** (no lookback) — same rationale as Shopee: file drops have no per-row `updated_at`, tiny volume (~500 rows / file), full-scan dedup is cheap.
5b. **Append-only parquet writes (LOCKED 2026-04-09).** Filename includes `ingested_at_ts`; existing files never overwritten. Dedup happens at read time in dbt src_ via `ROW_NUMBER() OVER (PARTITION BY voucher_no, line_no ORDER BY ingested_at DESC)`. See `design-spec.md` § 2.6.
6. **Model layer: `int_` (intermediate enrichment, NOT primary fact — LOCKED 2026-04-10).** `int_misa_sales_lines` with surrogate key + rolling location. Named `int_` because all orders already exist in Sapo `fact_orders`; MISA data adds COGS only. Rolling location applied pragmatically for P0 Metabase access. Precomputes `gross_margin`, `gross_margin_pct`, `revenue_net_of_discount`. P1 will join into `fact_order_economics`.
7. **Promo lines preserved:** `is_promo_line = TRUE` rows (revenue=0, cogs>0) **must** flow into fact — critical for accurate margin.
8. **Channel dim via seed:** `seeds/ref_misa_channel_codes.csv` maps `DAILY/ECOM/CS/KHAC` → friendly names. Kept tiny to match Shopee's "no dims at P0" spirit.
9. **No dlt SDK** — pandas direct to parquet (single file, <1 MB); mirror `gsheet_marketing_spend` / upcoming `shopee_income` shape.
10. **Voucher pattern preserved verbatim** — do not normalize/strip leading zeros; it's the future join key to Shopee/Sapo.
11. **Drop scope = discrete / non-overlapping windows (LOCKED).** User confirmed 2026-04-09 that MISA exports are ad-hoc per-period drops, not always-from-fiscal-start snapshots. Therefore: **append-only forever** for normal ingests; full-refresh is opt-in only via explicit `--full-refresh-touched-months` CLI flag (used quarterly at most). Automatic full-refresh is BANNED — would silently destroy data when a small corrective drop touches a partition with many untouched rows. See `design-spec.md` § 2.7.

## Dependencies

- Environment var `DBT_DATA_LAKE_PATH` already set (reused).
- No new secrets (file drop, no API).
- Python deps: `openpyxl`, `pandas` — **already being added by Shopee pipeline plan**; confirm both plans share the same `requirements.txt` delta.
- Coordinates with `plans/260409-1710-shopee-pipeline/` — same file-drop infrastructure; implement MISA AFTER or ALONGSIDE Shopee to reuse the `ensure_dbt_directories.py` edit pattern, reactive-sensor template, and sources.yml block pattern.

## Success criteria

- `SELECT COUNT(*) FROM int_misa_sales_lines` = 471 for the 2026-01-06..04-09 sample (totals footer excluded).
- `SELECT SUM(revenue_gross) FROM int_misa_sales_lines WHERE is_promo_line = FALSE` matches **2,588,376,195 VND** (audit baseline, § 9 of data-source-description.md — original figure of 5.177B was wrong due to totals-row contamination).
- `SELECT SUM(cogs_amount) FROM int_misa_sales_lines` matches the `"Tổng cộng"` footer row of the Excel (pre-filter) — serves as load-completeness checksum.
- `SELECT COUNT(DISTINCT voucher_no) FROM int_misa_sales_lines` = 344.
- No duplicate `(voucher_no, line_no)` pairs (unique test passes).
- Dropping a new `.xlsx` triggers sensor → ingestion → dbt → serving within one DAG run.
- No serving "Empty folder" errors; Metabase can query `int_misa_sales_lines` with no lock contention.

## P1 — Moved to dedicated plan

> P1 `fact_order_economics` has been implemented and is now tracked in: `plans/260411-fact-order-economics/plan.md`

## Open questions

See `docs/misa-amis/data-source-description.md` § 10 and `open-questions.md` (to be created during implementation kickoff if answers diverge from the Shopee plan's resolutions).

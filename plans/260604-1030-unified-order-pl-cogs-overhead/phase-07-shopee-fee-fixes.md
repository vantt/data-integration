# Phase 07 — Shopee platform-fee fixes (service-fee double-count + payment-fee rename)

## Context Links
- Master: `plan.md` (tier-2 platform fees feed `channel_net_profit`)
- Analysis: `plans/reports/analysis-260604-1309-shopee-service-fee-detail.md`
- Schema: `docs/architecture/order-pl/order-pl-schema-design.md`
- Code: `ingestion/src/shopee/income-parser.py`, `transformation/models/staging/stg_shopee_order_revenue.sql`, `transformation/models/intermediate/shopee/int_shopee_order_fees.sql`, `transformation/models/marts/sales/fact_order_costs.sql`, `transformation/models/marts/sales/fact_order_economics.sql`

## Overview
- **Priority:** High (corrupts tier-2 `channel_net_profit` — the overhead base in phase-04; sibling to BUG-1).
- **Status:** TODO.
- Two data-correctness bugs in Shopee income ingestion, fixed together (they partially cancel → fixing one alone makes dashboards look worse).

## Key Insights (from analysis — verified on real data)
- **BUG-2 (double-count):** D col AB `Phí Dịch Vụ` (`service_fee`) = F (`infrastructure_fee` + `voucher_xtra_fee`) **exactly** (diff=0, 136 orders). But pipeline ingests BOTH and sums BOTH → service fee counted **2×** in `fact_order_costs` (`platform_service` + `platform_infra` + `platform_voucher_xtra`) and `fact_order_economics` (`total_platform_fees` already has service_fee, then +infra+xtra again). Over-count ~−2.76M (May, 3 shops).
- **BUG-3 (dropped column):** Shopee renamed D `Phí thanh toán` → `Phí xử lý giao dịch` (May 2026); parser maps only old key → `payment_fee` lost (~−4.6M).
- **ROOT CAUSE (systemic):** parser is a **whitelist rename** (`income-parser.py:150` `{k:v ... if k in df.columns}`); only **3 structural** headers are guarded (`REQUIRED_DOANH_THU_HEADERS:109` — keys/dates, NOT fees). So any fee column Shopee renames/adds/removes is **silently dropped** (not renamed → dbt selects the missing snake_case name → NULL → fee vanishes, no error). Already **3 drift cases** in ~1 month (payment_fee rename, new `NTTD` col ignored, `auto_topup` gone). **Fees WILL keep silently disappearing** without a drift guard.

## Requirements
- Service fee sourced **only from F** (`order_service_fees` detail); D aggregate dropped.
- `payment_fee` captured for both old + new Shopee column names.
- No double-count; `channel_net_profit` accurate. Keep F breakdown for reporting.
- **Schema-drift guard (prevent future silent fee loss):** parser must SURFACE any unmapped column (esp. ones containing `Phí`/`Thuế`/amounts) instead of silently dropping it; ideally a per-order payout reconciliation checksum.

## Architecture / data flow
`Doanh Thu`(D)→`order_revenue` (drop service_fee), `Service Fee Details`(F)→`order_service_fees` (sole service-fee source). Join key = order_code. Service fee = Σ F detail per order.

## Related Code Files (modify)
1. `ingestion/src/shopee/income-parser.py` — DOANH_THU_RENAME: remove `"Phí Dịch Vụ"`; add `"Phí thanh toán"` + `"Phí xử lý giao dịch"` → `payment_fee`; drop `Phí Dịch Vụ` col if present.
2. `transformation/models/staging/stg_shopee_order_revenue.sql` — remove `service_fee` from SELECT + from `total_platform_fees`.
3. `transformation/models/intermediate/shopee/int_shopee_order_fees.sql` — remove `rev.service_fee`.
4. `transformation/models/marts/sales/fact_order_costs.sql` — remove `platform_service` UNION-ALL arm + `service_fee` from `shopee_wide`.
5. `transformation/models/marts/sales/fact_order_economics.sql` — no structural change (formula becomes correct once service_fee leaves total_platform_fees); update line-99 comment.

## Implementation Steps
1. **PRE-REQ verify (open Q1):** confirm the 4 Apr-2026 orders in D-without-F have `service_fee=0`; else they'd lose service fee after the fix. Query both sheets.
2. Edit parser (step 1 above). Re-parse a sample file → confirm no `service_fee` col, `payment_fee` mapped for both naming eras.
2b. **Add schema-drift guard to parser** (prevents the NEXT silent fee loss): after reading each sheet, compute `unmapped = set(df.columns) − set(RENAME_DICT)`; if any unmapped column matches a fee/tax pattern (`Phí`/`Thuế`/numeric amounts) → emit a loud `[!] SCHEMA_DRIFT` warning (and record to monitoring / raise per policy). Optionally add a per-order payout reconciliation checksum (`revenue − Σfees − tax == seller-net-payout column`) like the MISA parser's "Tổng cộng" checksum — confirm which D column = seller net payout first.
3. Edit the 4 dbt files. `dbt parse` clean.
4. **Re-ingest ALL archived Shopee files** (delete existing shopee parquet, re-run file-drop asset) — existing parquet carries double-count + missing payment_fee.
5. `dbt build` shopee chain + the 2 marts (pause schedules; lock-safe).
6. **Verify (Dagster run SUCCESS):** `platform_service` cost_type = 0 rows; `platform_infra`+`platform_voucher_xtra` totals = `stg_shopee_order_service_fees` sums; `payment_fee` present for May files; `channel_net_profit` shifts by the corrected amount.
7. Serving refresh + Metabase spot-check.

## Todo
- [ ] Verify Apr-2026 4-orders service_fee=0 (pre-req)
- [ ] Parser: drop aggregate + add payment_fee aliases
- [ ] Parser: schema-drift guard (alert on unmapped Phí/Thuế columns) + optional payout reconciliation checksum
- [ ] stg/int/fact_order_costs edits + fact_order_economics comment
- [ ] Re-ingest all archived Shopee files
- [ ] Guard test `assert_shopee_no_platform_service_double_count`
- [ ] Dagster run green + Metabase verify

## Success Criteria
- `platform_service` rows = 0; service fee = F-only; payment_fee captured both eras; closure-safe; Dagster run SUCCESS; no double-count in tier-2.

## Risk Assessment
- **Concurrency:** `fact_order_costs.sql`/`fact_order_economics.sql` edited by concurrent overhead/P1 session → coordinate; avoid interleaved commits.
- Re-ingestion must cover all historical Shopee parquet (not just archived set) — confirm backfill scope.
- Fixing one bug alone makes numbers look worse (they cancel) → deploy both together.

## Security / Data-integrity
- Idempotent re-ingestion; no secrets touched. Guard test prevents regression.

## Next Steps
- Must precede phase-04 reliance on `channel_net_profit`. Pairs with BUG-1 (both correct tier-1/tier-2 before overhead allocation). Unresolved: see analysis report §"Unresolved questions".

# Shopee Service-Fee Detail vs Aggregate — Analysis

**Date:** 2026-06-04. Read-only analysis. Feeds Order-P&L platform-fee tier (tier-2 `channel_net_profit`).

## Issue
Shopee income Excel has 2 sheets: **`Doanh Thu` (D)** and **`Service Fee Details` (F)**.
- D col **AB "Phí Dịch Vụ"** (`service_fee`) = **aggregated** service fee per order.
- F = **line detail** (`Phí Hạ Tầng`/`infrastructure_fee` + `Voucher Xtra`/`voucher_xtra_fee`).
Goal: ingest service fee from **F detail only**, drop the D aggregate (avoid double-count + gain breakdown).

## 1. Verified: F sums to D exactly
`service_fee` (D) = `infrastructure_fee` + `voucher_xtra_fee` (F) — **diff = 0** for every order across all 4 archived files (136 orders). Sample (THU shop): each order D total = F.infra(−3,000) + F.xtra → 0 diff.

## 2. 🔴 Double-count CONFIRMED (both marts)
- **`fact_order_costs.sql`** `shopee_fees` CTE emits 3 rows: `platform_service`=ABS(D.service_fee) **AND** `platform_infra`=ABS(F.infra) **AND** `platform_voucher_xtra`=ABS(F.xtra). Since D=F.infra+F.xtra → service fee counted **2×**.
- **`fact_order_economics.sql`** `shopee_platform_fees` = `total_platform_fees` (already embeds service_fee) **+** infrastructure_fee + voucher_xtra_fee (added AGAIN) → 2×. `channel_net_profit` inherits (understated/too negative by ~1× service fee per order).
- Quantified: May 2026 (3 shops) over-count = **−2,760,772 VND**; Apr 2026 = **−4,421,687 VND**.

## 3. 🔴 Second bug — payment_fee dropped (May 2026)
Shopee renamed D column `Phí thanh toán` → `Phí xử lý giao dịch` between Apr→May 2026. Parser `DOANH_THU_RENAME` only has the old key → `payment_fee` unmapped → **lost** for all May files (**−4,637,516 VND** of `platform_payment` missing). The two bugs partially cancel numerically in May (so dashboards look "less wrong" than they are) → **fix both together** or numbers temporarily worsen.

## 4. Fee classification (which D columns have F detail)
| D column → field | Has F detail? | Action |
|---|---|---|
| `Phí Dịch Vụ`→`service_fee` | YES (=F.infra+xtra) | **DROP from D; use F only** |
| `Phí cố định`→`fixed_fee` | No | keep |
| `Phí thanh toán`/`Phí xử lý giao dịch`→`payment_fee` | No | **add new alias** |
| `affiliate_commission_fee`, `piship_service_fee`, `vat_tax`, `personal_income_tax` | No | keep |

## 5. Recommended fix
**Parser** `ingestion/src/shopee/income-parser.py`:
- Remove `"Phí Dịch Vụ": "service_fee"` from `DOANH_THU_RENAME` (stop ingesting aggregate); belt-and-suspenders `drop(columns=["Phí Dịch Vụ"])` if present.
- Add BOTH aliases → `payment_fee`: `"Phí thanh toán"` (old) + `"Phí xử lý giao dịch"` (new).

**dbt:**
- `stg_shopee_order_revenue.sql`: drop `service_fee` from SELECT + from `total_platform_fees` sum.
- `int_shopee_order_fees.sql`: drop `rev.service_fee`.
- `fact_order_costs.sql`: remove the `platform_service` UNION-ALL arm + `service_fee` from `shopee_wide`. F rows (`platform_infra`+`platform_voucher_xtra`) become the sole service-fee source.
- `fact_order_economics.sql`: no structural change once `service_fee` leaves `total_platform_fees` — the `+ infra + xtra` then becomes correct. Update the line-99 comment.

**Re-ingest** all 4 archived files (existing parquet carries the double-count). **Guard test:** `platform_service` cost_type must return 0 rows post-fix.

## Coordination
`fact_order_costs.sql` / `fact_order_economics.sql` are edited by the concurrent overhead/P1 session → coordinate before editing. This fix corrects the **tier-2 `channel_net_profit`** that overhead allocation (unified plan phase-04) uses as base → do BEFORE phase-04 relies on it (sibling to BUG-1).

## Unresolved questions
1. **Apr 2026: 90 D-rows vs 86 F-rows** — 4 orders in D, none in F. Confirm their `D.service_fee = 0` before deploy, else LEFT JOIN → those orders silently lose service fee.
2. New May col `Phí dịch vụ hiển thị NTTD` (all-zero now) + `auto_topup_amount` disappeared — preempt mapping or monitor?
3. Backfill scope: any Shopee files processed before `_archive/` set? Those parquet also double-counted.
4. Fix both bugs in ONE deployment (they partially cancel) to avoid dashboards looking worse mid-fix.

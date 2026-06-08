# Scout Report — scope_* / is_active_order Refactor

**Date:** 2026-06-08 | **Branch:** main

---

## 1. dbt Layer (Sub-agent A)

### fact_orders.sql (lines 181–189)
```sql
-- CŨ — cần sửa
COALESCE(ch.is_sales_channel, false)
    AND orders.status != 'CANCELLED'               AS scope_sales,
COALESCE(ch.is_sales_channel, false)
    AND orders.status != 'CANCELLED'
    AND COALESCE(cu2.customer_type, 'RETAIL') = 'RETAIL'           AS scope_retail,
COALESCE(ch.is_sales_channel, false)
    AND orders.status != 'CANCELLED'
    AND COALESCE(cu2.customer_type, 'RETAIL') IN ('WHOLESALE', 'PARTNER') AS scope_b2b
```
→ Thêm `is_active_order` column, tách `status != 'CANCELLED'` ra.

### fact_order_economics.sql (lines 25–27, 112–114)
- Chỉ pass-through scope columns — không cần sửa logic
- Cần thêm `is_active_order` vào SELECT nếu muốn expose

### transformation/AGENTS.md (lines 168–170)
- Docs định nghĩa scope_sales cần cập nhật

### transformation/models/marts/schema.yml (line 66)
- Description của scope_sales cần cập nhật

**is_active_order** — chưa tồn tại trong bất kỳ file nào.

---

## 2. Blueprint Classification (Sub-agent B)

### Blueprints có `scope_retail|scope_sales|scope_b2b`

| blueprint_file | card_name | group |
|---|---|---|
| sales_yesterday_operation.md | Revenue KPI cards | revenue |
| sales_yesterday_operation.md | Order Count, Orders by Channel/Staff | count_all |
| sales_yesterday_operation.md | Cancelled Orders | count_cancelled |
| sales_yesterday_operation.md | Total Discount, Discount Rate | revenue |
| order_listing.md | Net/Gross Revenue, Total Collected, Total Discount × 3 tabs | revenue |
| order_listing.md | Cancelled Orders × 3 tabs | count_cancelled |
| order_listing.md | Order Count × 3 tabs | count_all |
| sales_promotion_analysis.md | Revenue cards | revenue |
| sales_promotion_analysis.md | Order counts | count_all |
| sales_ops_monthly_summary.md | Revenue cards | revenue |
| sales_ops_monthly_summary.md | Order Count | count_all |
| sales_ops_monthly_summary.md | Cancelled/Cancellation cards (6) | count_cancelled |
| sales_ops_weekly_review.md | Revenue cards | revenue |
| sales_ops_weekly_review.md | Cancelled & Returns | count_cancelled |
| sales_ops_weekly_review.md | Order counts | count_all |
| marketing_weekly_tracker.md | Revenue cards | revenue |
| marketing_weekly_tracker.md | Customer/Order counts | count_all |
| marketing_monthly_analysis.md | Revenue cards | revenue |
| marketing_monthly_analysis.md | Brand Performance Summary, Top 15 Products | ambiguous |
| customer_retention_dashboard.md | Revenue/CLV cards | revenue |
| customer_retention_dashboard.md | Retention Rate, Customer Count | count_all |
| sales_daily_operation.md | Revenue cards | revenue |
| sales_daily_operation.md | Order/Staff counts | count_all |
| customer_operational_dashboard.md | Lifetime Value, Revenue cards | revenue |
| customer_operational_dashboard.md | Customer counts | count_all |
| customer_intelligence_monthly.md | AOV/Revenue trends (scope_sales) | revenue |
| customer_intelligence_monthly.md | Segment Size, Customer counts | count_all |
| customer_intelligence_monthly.md | Segment Lifecycle Flow | ambiguous |
| sales_monthly_review.md | Revenue KPIs (scope_sales) | revenue |
| sales_monthly_review.md | Return Count | ambiguous |
| finance_pl.md | Revenue cards (scope_sales) | revenue |
| finance_pl.md | COGS/Shopee Fee cards | ambiguous |
| finance_cost_ledger.md | Cost aggregations (scope_sales) | ambiguous |
| finance_cost_ledger.md | Order Count | count_all |
| finance_channel_pl.md | Net Revenue, Gross Profit (scope_sales) | revenue |
| finance_channel_pl.md | Loss Leader Channel Count | count_all |
| b2b_sales_daily.md | Revenue cards (scope_b2b) | revenue |
| b2b_sales_daily.md | Order/Customer counts | count_all |
| b2b_orders_tracking.md | Outstanding Amount (scope_b2b) | revenue |
| b2b_orders_tracking.md | Order counts | count_all |
| ceo_weekly_pulse.md | Revenue KPIs (scope_sales) | revenue |
| ceo_weekly_pulse.md | Cancelled Orders | count_cancelled |
| ceo_weekly_pulse.md | Đơn hàng tuần này | ambiguous |
| ceo_monthly_scorecard.md | Revenue KPIs (scope_sales) | revenue |
| ceo_monthly_scorecard.md | Return Count, Waterfall (-) Returns | ambiguous |
| sales_today_retail.md | Revenue KPIs (scope_retail) | revenue |
| sales_today_retail.md | Order/Customer counts | count_all |

### Inline status filters (cần xử lý riêng)

**`status NOT IN ('CANCELLED', 'Voided')` — removable sau refactor:**
- `order_listing.md` — 12 SQL blocks

**`status != 'CANCELLED'` — removable sau refactor:**
- `product_performance.md` — nhiều cards (Tab Tong quan + Tab Phan tich)

**`status = 'CANCELLED'` → đổi thành `AND NOT o.is_active_order`:**
- `sales_yesterday_operation.md`, `order_listing.md` × 3, `sales_ops_monthly_summary.md` × 6, `sales_ops_weekly_review.md`, `ceo_weekly_pulse.md`

**`status = 'COMPLETED'` ANOMALY (không dùng scope_sales) — out of scope cho refactor này:**
- `marketing_roi.md`, `order_profitability_all.md`, `finance_accounting_recon.md`

---

## 3. Semantic Docs (Sub-agent C)

### Files cần cập nhật

| File | Lines | What Changes |
|---|---|---|
| `semantic/segments.md` | 13 (hierarchy), 36–39 (scope_sales Rule), 62–63 (anti-pattern), 182–186 (Scope Matrix) | Replace `status NOT IN ('CANCELLED', 'Voided')` → reference `is_active_order` |
| `AGENTS.md` | 270 (template SQL), 348–349 (SQL Conventions), 455 (scope table filter desc) | Update raw status filter → `is_active_order` |
| `guides/report_segmentation.md` | 104–108, 125–130, 143–148 (scope SQL blocks) | Update raw SQL re-derivations |
| `semantic/rules.md` | 60–72 (Cancellation Convention), 79–81 (Applies To) | Update comment about scope already excluding CANCELLED |
| `transformation/AGENTS.md` | 168–170 (scope docs) | Update definitions |

### Rill YAMLs — KHÔNG cần sửa
- 4 files dùng `scope_sales/scope_retail/scope_b2b = true` as column references — vẫn valid sau refactor.

---

## 4. Ambiguous Cards — Default Decision

Per plan: **thêm `AND is_active_order`** cho các customer analytics cards (New/Returning Customers) vì thường chỉ tính đơn thực tế.

Cards cần human review (skip trong batch refactor):
- `order_listing.md` (recon tool, `WHERE 1=1` hoặc inline filters intentional)
- `marketing_roi.md`, `order_profitability_all.md` (dùng `status = 'COMPLETED'` — khác pattern)
- `shopee_channel_economics.md` (int_shopee_order_fees, out of scope)
- `finance_accounting_recon.md` (recon proxy, out of scope)
- Single-order lookup cards (`order_detail.md`)
- Rill metric files (unchanged)

---

## 5. Execution Plan

1. ✅ Scan complete
2. ⏳ Sửa `fact_orders.sql` → Dagster run fact_orders
3. ⏳ Check `fact_order_economics.sql` → thêm `is_active_order` → Dagster run
4. ⏳ Update all semantic docs (parallel): segments.md, AGENTS.md, rules.md, report_segmentation.md, transformation/AGENTS.md
5. ⏳ Update blueprints (batch)
6. ⏳ Deploy blueprints
7. ⏳ Verify end-to-end
8. ⏳ Commit

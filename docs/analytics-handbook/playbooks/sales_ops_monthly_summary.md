# Playbook: Sales Ops Monthly Summary

## Overview

- **Audience:** Sales Operator, Customer Support Lead, Operations Manager
- **Goal:** Monthly operational summary — order processing efficiency, quality analysis, social commerce results, channel & branch health, staff productivity, and payment reconciliation for the closed month.
- **Cadence:** 2nd-3rd of each month, reviewing the closed month.
- **Archetype:** Operational Cockpit (4 tabs)
- **Collection:** `Operations` > `Periodic Reviews`
- **Design Spec:** [Sales Ops Monthly Summary (Redesign)](../designs/sales_ops_monthly_summary.md)
- **Related:** [Sales Ops Weekly Review](./sales_ops_weekly_review.md), [Social Commerce Operations](./customer_support_social_commerce.md), [Orders Reconciliation](./orders_list_reconciliation.md)

## Key Questions

1. **Processing Efficiency:** Ty le hoan thanh don hang thang nay? Thoi gian xu ly trung binh cai thien hay te hon?
2. **Order Quality:** Return rate va cancellation rate thang nay ra sao? So voi thang truoc?
3. **Social Commerce Results:** Tong doanh thu social commerce thang nay? Moi nhan vien CS dong gop bao nhieu?
4. **Channel Operations:** Kenh nao chiem nhieu workload nhat? Kenh nao co ty le van de cao nhat?
5. **Branch Performance:** Chi nhanh nao xu ly nhieu don nhat? Chi nhanh nao can cai thien?
6. **Payment Reconciliation:** Tong thanh toan da thu vs pending? Phuong thuc nao pho bien nhat?
7. **Staff Productivity:** Nhan vien nao xu ly nhieu don nhat? AOV trung binh moi nhan vien?
8. **Margin Health:** Kenh nao co bien loi nhuan cao nhat? Co bao nhieu don lo trong thang?

## Filters

- **Date Range:** Default = Last Closed Month. Comparison = Previous Month.
- **Branch/Location:** Filter by `dim_branch_location`.

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql), [`fact_payments`](../../../transformation/models/marts/sales/fact_payments.sql), [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)
- **Dimensions:** `dim_channels`, `dim_staff`, `dim_branch_location`, `dim_customers`, `dim_payment_methods`, `dim_order_status`, `dim_products`

## Dashboard Structure (4 Tabs)

### Tab 1: Tong quan thang (Monthly Overview)

**Purpose:** Tong the thang — KPIs chinh, chat luong don hang, xu huong 6 thang.

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Total Orders** | Scalar + MoM Trend | [Total Orders](../domains/sales.md#4-total-orders) | Hero metric. MoM % change. |
| **Net Revenue** | Scalar + MoM Trend | [Net Revenue](../domains/sales.md#2-net-revenue) | MoM % change. Currency VND. |
| **AOV** | Scalar + MoM Trend | [AOV](../domains/sales.md#5-aov-average-order-value) | MoM % change. Currency VND. |
| **Completion Rate** | Gauge (3 zones) | _Derived_ | Green >=90%, Yellow 80-89%, Red <80%. |
| **Order Status Distribution** | Donut | _Derived_ | COMPLETED (green), OPEN (teal), CANCELLED (red), ARCHIVED (grey). |
| **Avg Time to Complete** | Scalar + MoM Trend | _Derived from `time_to_complete_hours`_ | Lower = better. MoM comparison. |
| **Cancelled & Returns Summary** | Formatted Table | _Derived_ | MoM % change. RED highlight if increasing. |
| **Cancellation Rate Trend (6M)** | Line Chart | _Derived_ | Goal line at 5%. Red series. |
| **Return Rate Trend (6M)** | Line Chart | [Return Rate](../domains/sales.md#3-return-rate--count) | Goal line at 3%. Yellow series. |
| **Top 10 Returned Products** | Formatted Table | _Derived_ | Product, Return Count, Return Revenue. |

### Tab 2: Kenh & Chi nhanh (Channels & Branches)

**Purpose:** Phan bo workload va hieu suat van hanh theo kenh va chi nhanh.

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Orders by Channel** | Horizontal Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Ranking by volume. |
| **Revenue by Channel** | Horizontal Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Ranking by revenue. Currency VND. |
| **Channel Operations Matrix** | Formatted Table | _Derived_ | Channel, Orders, Revenue, Completion %, Cancel %, Return %, Avg Complete hrs. Conditional: Completion <85% = red, Cancel >5% = red, Return >3% = yellow. |
| **Cancellation by Channel** | Horizontal Bar | _Derived_ | Red bars. Ranking by cancellation count. |
| **Cancellation Share by Channel** | Donut | _Derived_ | % contribution to total cancellations. |
| **Orders by Branch** | Horizontal Bar | _Derived_ | Ranking branches by volume. |
| **Branch Performance Table** | Formatted Table | _Derived_ | Branch, Orders, Revenue, Completion %, Cancel %. Conditional formatting same as channel matrix. |

### Tab 3: Doi ngu & Thanh toan (Team & Payments)

**Purpose:** Social commerce results, staff productivity toan kenh, doi soat thanh toan.

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Social Revenue** | Scalar + MoM Trend | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | MoM change. Currency VND. |
| **Social Orders** | Scalar + MoM Trend | [Social Order Count](../domains/customer_support.md#2-social-order-count) | MoM change. |
| **Social AOV** | Scalar + MoM Trend | _Derived_ | MoM change. Currency VND. |
| **Social Revenue by Platform** | Donut | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | Facebook vs Zalo monthly split. |
| **CS Staff Leaderboard** | Table | _Derived_ | Staff, Social Orders, Social Revenue, AOV, % Contribution. Ranked by Revenue DESC. |
| **Staff Revenue Distribution** | Horizontal Bar | _Derived_ | Revenue per staff (all channels). Identifies top performers. |
| **Staff Performance Table** | Formatted Table | _Derived_ | Staff, Orders, Revenue, AOV, Completion %. Conditional: >=95% = green, <80% = red. |
| **Payment Method Distribution** | Donut | [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution) | Transaction count by payment method. |
| **Payment Method Trend (6M)** | Stacked Area | [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution) | Monthly stacked by method. Shows shift in preferences. |
| **Payment Status Summary** | Formatted Table | [Payment Status](../domains/sales.md#12-payment-status) | Status, Orders, Amount, % of Total. Flag pending > 5% yellow. |

### Tab 4: Margin

**Purpose:** Bien loi nhuan theo kenh va canh bao don lo thang.

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Monthly Margin by Channel** | Formatted Table | `fact_order_economics.gross_profit / net_revenue` | Channel, Orders, Revenue, Gross Margin %, MoM Δ pp. Sorted Margin DESC. Red if Margin <20%, Yellow if MoM Δ<0. |
| **Loss-Order Alert (Monthly)** | Scalar + MoM Compare | `fact_order_economics.channel_net_profit < 0` | Count of loss-making orders. MoM comparison. Escalate if count rising. |

**Data Note:** Gross Margin % uses MISA COGS data. Orders without COGS match (`has_cogs = false`) will show gross_profit = net_revenue — check `misa_line_count` to verify coverage.

## Operational Actions

- **Completion Rate < 90%:** Deep dive into OPEN and stuck orders. Check fulfillment pipeline bottleneck.
- **Cancellation Rate > 5%:** Analyze top cancellation reasons by channel. If marketplace-heavy, check stock sync issues.
- **Return Rate > 3%:** Review top returned products. Escalate to product team if quality issue. Update product descriptions if mismatch issue.
- **Staff Productivity Imbalance (> 3x between highest and lowest):** Review order assignment fairness. Consider workload redistribution.
- **Pending Payments > 5%:** Escalate to finance team. Check bank transfer confirmation delays.
- **Branch Completion < 85%:** Investigate branch-specific issues — staffing, inventory, fulfillment delays.
- **Channel Gross Margin % < 20%:** Investigate pricing or COGS spike for that channel. Cross-check with MISA data.
- **MoM Margin Δ < -3 pp:** Rapid deterioration — check if new discount campaign or COGS increase hit within the month.
- **Loss-Order Count rising MoM:** Root-cause analysis required — check if pricing error, COGS data anomaly, or Shopee fee change.

## Implementation Notes

- **Differs from Sales Ops Weekly Review:** Weekly is a quick operational check (WoW). Monthly adds **6-month trends, branch analysis, staff leaderboard, and channel health matrix** for management decisions (MoM).
- **Differs from CEO Monthly Scorecard:** CEO sees strategic metrics (revenue, growth, segments). This shows **operational metrics** (completion rate, processing time, staff productivity, payment health).
- **4-tab design:** Tab 1 is the quick monthly pulse (5-7 min). Tabs 2-3 are deep-dives for specific audiences (channel managers, team leads, finance). Tab 4 (Margin) is for Operations Manager + Finance monthly review.
- **`time_to_complete_hours`:** Calculated in `fact_orders` as `DATEDIFF(hour, ordered_at, completed_at)`. NULL for non-completed orders — exclude from average.
- **Staff Data Caveat:** Not all orders have assigned staff (marketplace auto-orders). Filter to `seller_staff_key IS NOT NULL` for meaningful staff comparisons.
- **COGS Coverage Caveat (Tab 4):** `fact_order_economics` joins MISA via `order_code = voucher_no`. Orders without MISA match have `has_cogs = false` — gross_profit = net_revenue in those rows (overstated). Review monthly MISA sync health before relying on margin figures.
- Max ~43 visual elements across 4 tabs. Operations Manager reviews Tab 4 in 5-10 min after Tab 1 overview.

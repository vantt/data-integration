# Playbook: Sales Ops Weekly Review

## Overview

- **Audience:** Sales Operator, Customer Support Lead, Store Manager
- **Goal:** Weekly operational review — order processing health, channel workload, team performance, payment status, weekly margin. 4 tabs: Tong quan, Kenh & Chi nhanh, Doi ngu & Thanh toan, Margin.
- **Cadence:** Every Monday, reviewing previous Mon-Sun.
- **Archetype:** Operational Cockpit (3 tabs)
- **Collection:** `Operations` > `Periodic Reviews`
- **Design Spec:** [Sales Ops Weekly Review (Redesign)](../designs/sales_ops_weekly_review.md)
- **Related:** [Daily Sales Operations](./sales_daily_operation.md), [Social Commerce Operations](./customer_support_social_commerce.md), [Sales Ops Monthly Summary](./sales_ops_monthly_summary.md)

## Key Questions

1. **Order Volume:** Tuan nay xu ly bao nhieu don? So voi tuan truoc tang hay giam?
2. **Order Quality:** Ty le don hoan thanh vs huy vs tra hang? Co bat thuong khong?
3. **Channel Workload:** Don hang phan bo the nao giua cac kenh? Kenh nao tang/giam dot bien can dieu chinh nhan luc?
4. **Branch Performance:** Chi nhanh nao xu ly nhieu don nhat? Chi nhanh nao can chu y?
5. **Social Commerce:** Doanh thu tu Facebook/Zalo tuan nay? Nhan vien nao ban tot nhat?
6. **Payment Health:** Phuong thuc thanh toan nao pho bien? Co don nao pending payment lau khong?
7. **Margin Health:** Kenh nao co bien lo am hoac giam > 5pp WoW? Tuan nay co don hang am khong?

## Filters

- **Date Range:** Default = Last 7 Days (previous Mon-Sun). Comparison = Previous 7 Days.
- **Branch/Location:** Filter by `dim_branch_location`.

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_payments`](../../../transformation/models/marts/sales/fact_payments.sql), [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)
- **Dimensions:** `dim_channels`, `dim_staff`, `dim_branch_location`, `dim_customers`, `dim_payment_methods`

## Dashboard Structure (4 Tabs)

### Tab 1: Tong quan tuan (Weekly Overview)

**Purpose:** Tong the tuan — KPIs chinh, trang thai don hang, xu huong 14 ngay va gio cao diem.

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Total Orders** | Scalar + WoW Trend | [Total Orders](../domains/sales.md#4-total-orders) | Hero metric. WoW % change. |
| **Net Revenue** | Scalar + WoW Trend | [Net Revenue](../domains/sales.md#2-net-revenue) | WoW % change. Currency VND. |
| **AOV** | Scalar + WoW Trend | [AOV](../domains/sales.md#5-aov-average-order-value) | WoW % change. Currency VND. |
| **Completed %** | Gauge (3 zones) | _Derived_ | Green >=90%, Yellow 80-89%, Red <80%. |
| **Order Status Distribution** | Donut | _Derived_ | COMPLETED (green), OPEN (blue), CANCELLED (red), ARCHIVED (muted). |
| **Fulfilment Status Breakdown** | Horizontal Bar | _Derived_ | Ranking by fulfillment_status: DELIVERED, SHIPPING, PACKED, PENDING, RETURNED, CANCELLED. |
| **Cancelled & Returns** | Formatted Table | _Derived_ | Don huy + Don tra hang with WoW %. RED highlight if WoW >= 100% (tang > 2x). |
| **Daily Orders (14 Days)** | Combo Chart | [Total Orders](../domains/sales.md#4-total-orders) | Bars = daily order count (blue). Dashed line = AOV. 14-day window for day-of-week patterns. |
| **Peak Hour Heatmap** | Pivot Table (heatmap colors) | [Hourly Heatmap](../domains/sales.md#7-hourly-heatmap-day-of-week-analysis) | Hour x Day of Week. Conditional range coloring (white-to-blue). Plan shift scheduling. |

### Tab 2: Kenh & Chi nhanh (Channels & Branches)

**Purpose:** Phan bo workload va hieu suat van hanh theo kenh va chi nhanh.

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Orders by Channel** | Horizontal Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Ranking channels by order volume. |
| **Revenue by Channel** | Horizontal Bar | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Ranking channels by revenue. Currency VND. |
| **Channel Performance Table** | Formatted Table | _Derived_ | Kenh, Don hang, Doanh thu, AOV, Don WoW %, DT WoW %. Conditional: >=30% green, <=-30% red. |
| **Orders by Branch** | Horizontal Bar | _Derived_ | Ranking branches by order volume. |
| **Branch Performance Table** | Formatted Table | _Derived_ | Chi nhanh, Don hang, Doanh thu, WoW %. Conditional: positive green, negative red. |

### Tab 3: Doi ngu & Thanh toan (Team & Payments)

**Purpose:** Social commerce results, staff productivity toan kenh, doi soat thanh toan.

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Social Revenue** | Scalar + WoW Trend | [Social Sales Volume](../domains/customer_support.md#1-social-sales-volume) | WoW change. Currency VND. |
| **Social Orders** | Scalar + WoW Trend | [Social Order Count](../domains/customer_support.md#2-social-order-count) | WoW change. |
| **Social AOV** | Scalar + WoW Trend | _Derived_ | WoW change. Currency VND. So voi AOV chung. |
| **Staff Revenue (All Channels)** | Horizontal Bar | _Derived_ | Revenue per staff toan kenh. Ranking nhan vien theo doanh thu. |
| **Top Staff - Social Channels** | Formatted Table | _Derived_ | Nhan vien, Don hang, Doanh thu, AOV. Chi social channels. Ranked by Revenue DESC. |
| **Payment Method Distribution** | Donut | [Payment Method Distribution](../domains/sales.md#11-payment-method-distribution) | Transaction count by payment method. |
| **Payment Status Summary** | Formatted Table | [Payment Status](../domains/sales.md#12-payment-status) | Trang thai, Don hang, So tien, Ty le %. Flag pending > 5% yellow. |

### Tab 4: Margin

**Purpose:** Theo doi bien lo theo kenh tuan nay — phat hien kenh am loi nhuan va don hang co chi phi vuot doanh thu.

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
| :--- | :--- | :--- | :--- |
| **Weekly Margin by Channel** | Formatted Table | `fact_order_economics.gross_profit` | Kenh, Don hang, Doanh thu, Bien lo %, WoW Δ pp. Sort by Bien lo % DESC. RED row if Bien lo % < 0. YELLOW if WoW Δ pp <= -5. |
| **Loss-Order Alert** | Scalar | `fact_order_economics.channel_net_profit` | COUNT(orders WHERE channel_net_profit < 0) tuan nay. No WoW comparison display (plain scalar, v0.58.11 compat). |

## Operational Actions

- **Cancelled Orders Spike (WoW >= 100%):** Investigate root cause — stock-out? pricing error? system issue?
- **Returns Spike:** Identify top returned products. Check for quality or description mismatch.
- **Channel Volume Shift > 30%:** Notify team leads to adjust staffing. If marketplace order spike, check for flash sale events.
- **Pending Payments > 5%:** Follow up with payment provider. Check bank transfer orders awaiting confirmation.
- **Social Revenue Declining:** Coordinate with Marketing on posting schedule. Review CS team response time.
- **Completed % < 90% (Red Zone):** Deep-dive into OPEN and stuck orders. Check fulfillment pipeline bottleneck.
- **Loss-Order Count > 5:** Investigate root cause immediately — pricing error? COGS spike? Abnormal discount applied? Escalate to finance within the same day.
- **Margin Slip > 5pp WoW (any channel):** Review channel-level cost structure. Check for unusual returns, fee changes, or promo applied to low-margin products. Notify channel manager.
- **Gross Margin % < 0 (any channel):** Treat as P1 operational alert — channel is loss-making this week. Freeze additional volume until root cause identified.

## Implementation Notes

- **4-tab design:** Tab 1 is the quick weekly pulse (5 min). Tabs 2-4 are deep-dives for specific audiences (channel managers, team leads, finance, ops). ~10 cards per tab, ~35 total.
- **Differs from Daily Ops Dashboard:** Daily dashboard is **real-time/yesterday**. This is a **weekly aggregate** for trend spotting and team management.
- **Differs from CEO Weekly Pulse:** CEO version is strategic (revenue & growth). This version is **operational** (order processing, team performance, channel workload).
- **Differs from Monthly Summary:** Monthly adds **6-month trends, branch health matrix, staff leaderboard, cancellation analysis** for management decisions (MoM). This weekly version uses WoW for fast operational rhythm.
- **Staff Data Caveat:** `dim_staff` data comes from Sapo's assigned salesperson field. Not all orders have a staff assignment (especially marketplace orders). Filter to `seller_staff_key IS NOT NULL` for meaningful staff comparisons.
- **Incomplete Week Exclusion:** All queries use `order_timestamp < date_trunc('week', current_date)` to exclude the current incomplete week — ensures fair WoW comparison.

# Playbook: Sales Monthly Business Review (MBR)

## Overview

- **Audience:** Sales Director, CFO, Regional Managers
- **Goal:** Comprehensive review of last month's performance, variance analysis against targets, and strategic planning.
- **Collection:** `Executive`
- **Related Playbook:** [CEO Weekly Pulse](./ceo_weekly_pulse.md)

## Review Structure

The Monthly Business Review should follow this standard agenda:

1.  **Executive Summary:** High-level achievements and "Red Flags".
2.  **Financial Performance:** Revenue vs Target, Margin analysis.
3.  **Growth Drivers:** Channel & Store performance.
4.  **Operational Efficiency:** Returns, AOV, Discounts.
5.  **Action Plan:** Decisions made and owners assigned.

## 1. Financial Performance

> **Context:** Did we hit the top-line and bottom-line numbers?

| Metric                 | Reference                                                          | Analysis Question                                       |
| :--------------------- | :----------------------------------------------------------------- | :------------------------------------------------------ |
| **Net Revenue**        | [Net Revenue](../domains/sales.md#2-net-revenue)                   | What is the variance vs Target? What is the MoM growth? |
| **Gross Margin**       | [Gross Margin](../domains/sales.md)                                | Did heavy discounting impact our profitability?         |
| **Target Achievement** | [Achievement Rate](../domains/sales.md#15-target-achievement-rate) | Which regions missed the target significantly (< 80%)?  |
| **Variance**           | [Variance to Target](../domains/sales.md#16-variance-to-target)    | Absolute value gap to close.                            |

### Visualization Strategy

- **Waterfall Chart:** Showing bridge from Target -> Actual (Volume impact vs Price impact).
- **Trend Line:** 12-Month trailing revenue to see long-term trajectory.

## 2. Growth Drivers

> **Context:** Where is the growth coming from?

| Analysis Area         | Key Metrics                                                           | Drill-down Dimensions                                     |
| :-------------------- | :-------------------------------------------------------------------- | :-------------------------------------------------------- |
| **Channel Mix**       | [Sales by Channel](../domains/sales.md#8-sales-by-channel)            | Online vs Offline Growth.                                 |
| **Store Tiering**     | [Sales by Region](../domains/sales.md#15-sales-by-regionlocation)     | Comparison of "Flagship" vs "Standard" store performance. |
| **Customer Segments** | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Are we acquiring enough new customers to fuel growth?     |

## 3. Operational Health (Deep Dive)

> **Context:** Are we selling efficiently?

- **Discount Control**: Analyze [Discount Impact](../domains/sales.md#13-discount-impact).
  - _Flag:_ If Discount % > 15% of GMV, investigation is required.
- **Return Rate**: Analyze [Return Rate](../domains/sales.md#3-return-rate--count).
  - _Flag:_ Identify top 5 returned products and root causes.
- **Product Mix**: Analyze [Top Selling Products](../domains/sales.md#9-top-selling-products).
  - _Action:_ Identify slow-moving inventory for clearance.

## Action Plan Template

Use this format to document decisions during the meeting:

| Issue / Opportunity                              | Root Cause                 | Action Item                                | Owner          | Due Date     |
| :----------------------------------------------- | :------------------------- | :----------------------------------------- | :------------- | :----------- |
| _Example: Missed revenue target in North Region_ | _Stockout of top sellers_  | _Expedite transfer from Central Warehouse_ | _Ops Manager_  | _YYYY-MM-DD_ |
| _Example: High returns on Product X_             | _Sizing issue description_ | _Update product page sizing guide_         | _Content Team_ | _YYYY-MM-DD_ |

## Dashboard Reference

- **Design Spec:** [Sales Monthly Review Design](../designs/sales_monthly_review.md)
- **Dashboard:** Sales Analytics > Monthly Reports (TBD)

## Reading Flow

1. **CONTEXT** — MBR hop hang thang, review ket qua thang vua dong. Dashboard tra loi "Dat target chua?"
2. **KEY FINDING** — Bat dau o View 1: Hero card "Net Revenue vs Target" (progress-toward-goal) cho biet ngay achievement rate. Xanh = on-track, do = miss.
3. **EVIDENCE** — Supporting KPIs (Orders, AOV, New Customers) cho context. 12-Month Revenue Trend xac nhan trajectory.
4. **IMPLICATIONS** — Neu miss target: chuyen sang View 2 (Tai chinh) de xem branch nao miss, waterfall cho gap analysis. Neu on-track: chuyen sang View 3 (Tang truong) de hieu dong luc.
5. **ACTIONS** — View 4 (Van hanh) flag van de can xu ly: chiet khau > 15%, tra hang tang, san pham can clearance. Ghi action items vao Action Plan Template.

## Action Triggers

| Metric | Condition | Severity | Owner | Action |
|--------|-----------|----------|-------|--------|
| Target Achievement | < 80% | Red | Sales Director | Hop khan cap, root cause analysis, action plan 48h |
| Target Achievement | 80-90% | Warning | Regional Manager | Review branch-level performance, identify quick wins |
| Discount Rate % | > 15% GMV | Warning | Sales Director | Audit promo campaigns, review discount policy |
| Discount Rate % | > 20% GMV | Red | CFO | Freeze non-essential promotions, margin recovery plan |
| Return Rate | MoM > +50% | Warning | Ops Manager | Investigate top returned products, check quality/description |
| New Customers | MoM < -15% | Warning | Marketing Manager | Review acquisition channels, check marketing spend |
| Any Channel Revenue | MoM < -20% | Warning | Channel Owner | Channel-specific diagnosis: stock, marketing, competition |
| Branch Achievement | < 80% for 2+ months | Red | Regional Manager | Performance improvement plan, resource reallocation |

## 4. Monthly P&L

> **Context:** Are we growing profitably? Revenue without margin visibility leads to strategic blind spots.

| Metric | Reference | Analysis Question |
|:---|:---|:---|
| **Net Profit (MoM)** | `fact_order_economics.channel_net_profit` | Did profit grow in line with revenue? If revenue up but profit down, cost inflation or fee creep. |
| **Gross Margin % (MoM)** | `gross_profit / net_revenue` | Is margin trend stable? Decline over 2+ months triggers COGS/pricing investigation. |
| **Channel Profit Ranking** | Channel-level `channel_net_profit` | Which channels drive profit? Which are loss-making after COGS and platform fees? |

### Visualization Strategy

- **Scalar + MoM comparison:** Net Profit and Gross Margin % side-by-side — CFO reads both at a glance.
- **12-Month Line Chart:** Gross Margin % trajectory — reveals structural margin compression vs. one-off dip.
- **Channel Table (sorted by Net Profit DESC):** Red highlight on negative-profit channels. Top 10 only for focus.

### Action Triggers

| Metric | Condition | Severity | Owner | Action |
|:---|:---|:---|:---|:---|
| Gross Margin % | MoM drop > 3pp | Warning | CFO | Investigate COGS spike or platform fee increase |
| Gross Margin % | Negative for any channel | Red | Sales Director | Channel profitability review, consider delisting |
| Net Profit | MoM < -20% | Red | CFO | Emergency margin review before next month launch |
| Channel Net Profit | Any channel negative | Warning | Channel Owner | Channel P&L deep-dive (dashboard: Channel P&L Deep Dive) |

### Filter Applied

Cards in this tab filter: `is_sales_channel = true`, `status NOT IN ('CANCELLED', 'Voided')`, `has_cogs = true` (MISA COGS matched). Orders without COGS match are excluded to avoid understating profitability.

## Data Preparation Checklist

Before the MBR meeting, ensure:

1.  [ ] **Target Upload**: Verify next month's targets are loaded in `fact_targets`.
2.  [ ] **Cost Data**: Ensure COGS are updated for Margin calculation.
3.  [ ] **Data Completeness**: Check that all offline orders for the closed month are synced.
4.  [ ] **MISA Sync**: Confirm `int_misa_sales_lines` is refreshed — P&L tab requires `has_cogs = true` rows.

# Playbook: Sales Monthly Business Review (MBR)

## Overview

- **Audience:** Sales Director, CFO, Regional Managers
- **Goal:** Comprehensive review of last month's performance, variance analysis against targets, and strategic planning.
- **Metabase Collection:** `Sales Analytics` > `Monthly Reports`
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

### Visualization Strategy (Metabase)

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

## Data Preparation Checklist

Before the MBR meeting, ensure:

1.  [ ] **Target Upload**: Verify next month's targets are loaded in `fact_targets`.
2.  [ ] **Cost Data**: Ensure COGS are updated for Margin calculation.
3.  [ ] **Data Completeness**: Check that all offline orders for the closed month are synced.

# Playbook: Marketing ROI

## Overview

- **Audience:** CMO, Marketing Manager
- **Goal:** Evaluate real marketing effectiveness — not just revenue ROAS but profitable ROAS (gross profit per dollar of spend) by channel, over rolling 30-day windows.
- **Cadence:** Weekly or on-demand. Default window = last 30 days vs prior 30 days.
- **Archetype:** Operational Cockpit
- **Tool:** metabase
- **Collection:** `Marketing & Customers`
- **Blueprint:** [marketing_roi.md](../blueprints/metabase/marketing_roi.md)
- **Related:** [Marketing Monthly Analysis](./marketing_monthly_analysis.md), [Marketing Weekly Tracker](./marketing_weekly_tracker.md)

## Key Questions

1. **Spend Efficiency:** Tong chi phi marketing vs doanh thu tao ra — ROAS tong hop la bao nhieu?
2. **Profitable ROAS:** Sau khi tru COGS, kenh nao thuc su sinh loi? ROAS cao nhung bien lai thap la rui ro.
3. **Trend:** Profitable ROAS 30 ngay nay so voi 30 ngay truoc tang hay giam?
4. **Quadrant Alert:** Kenh nao co ROAS cao nhung bien lai thap (canh bao do)?

## Filters

- **Date Range** (`date_range`): Default = `past30days`. All queries scope against this.
- **Period Comparison:** Profitable ROAS table always compares current 30d vs prior 30d (hardcoded in SQL).

## Data Lineage

- **Core Models:**
  - [`fact_marketing_spend`](../../../transformation/models/marts/sales/fact_marketing_spend.sql) — spend_amount, channel_key, date_key
  - [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql) — net_revenue, gross_profit, channel_key, date_key, status
- **Dimensions:** `dim_channels`, `dim_date`
- **Join key:** `channel_key` (surrogate key shared across both facts)

## Metric Definitions

| Metric | Formula | Notes |
| :--- | :--- | :--- |
| **ROAS** | `net_revenue / spend` | Revenue return per dong chi phi. Does not reflect profitability. |
| **Bien lai gross (%)** | `gross_profit / net_revenue × 100` | COGS already deducted in `fact_order_economics.gross_profit`. |
| **Profitable ROAS** | `gross_profit / spend` | = ROAS × margin %. Reflects actual profit per dong spend. |
| **Delta** | `current_profitable_roas - prior_profitable_roas` | Negative = declining profitability per spend unit. |

> **Caveat:** Attribution dung channel-level join (channel_key). CAC/payback analysis chua co trong dashboard nay.

## Dashboard Structure

### Section 1: KPI Scalars (Row 0-4)

| Card | Type | Purpose |
| :--- | :--- | :--- |
| Chu ky bao cao | Scalar (text) | Shows current and comparison date windows |
| Tong chi phi | Scalar | Total marketing spend in selected window |
| Tong doanh thu | Scalar | Total revenue from sales channels in selected window |
| Blended ROAS | Scalar | Aggregate ROAS = total_revenue / total_spend |

### Section 2: Spend vs Revenue Trend (Row 5-11)

| Card | Type | Purpose |
| :--- | :--- | :--- |
| Spend vs Revenue Trend | Combo (bar+line) | Revenue (bar) vs spend (line) theo thang. Phat hien divergence. |

### Section 3: Channel ROAS (Row 12-26)

| Card | Type | Purpose |
| :--- | :--- | :--- |
| ROAS by Channel | Horizontal bar | Ranking nhanh kenh theo ROAS. Red if < 1, green if >= 3. |
| Channel Marketing Table | Table | Spend, revenue, orders, ROAS, CPC, CPM, clicks, impressions per channel. |

### Section 4: Profitable ROAS Analysis (Row 27-43)

| Card | Type | Purpose |
| :--- | :--- | :--- |
| Profitable ROAS by Channel | Table | Channel, spend, revenue, ROAS, margin %, profitable_roas, prior 30d profitable_roas, delta. **Main decision card.** |
| Channel ROI Quadrant | Scatter (optional) | X=ROAS, Y=margin %, bubble=spend. Quadrant analysis: red flag = top-right ROAS but bottom margin. |

## Operational Actions

### Profitable ROAS Table

| Condition | Signal | Action |
| :--- | :--- | :--- |
| `profitable_roas < 1.0` | Kenh dang lo — moi dong spend tao ra duoi 1 dong loi nhuan gross | Cut or pause channel spend immediately. Escalate to CMO. |
| `profitable_roas trending down 2 consecutive periods` | Dau hieu xoi mon bien lai | Review pricing, COGS changes, or channel fee increases. Set 1-week review gate. |
| `ROAS cao nhung margin % thap (< 15%)` | High-ROAS-Low-Margin trap | Do not scale spend. Investigate COGS or promotional discount eroding margin. |
| `delta < -0.5` | Profitable ROAS suy giam manh | Priority investigation: channel cost up? margin down? pricing slip? |
| `profitable_roas >= 2.0 va delta > 0` | Kenh hieu qua va cai thien | Candidate for increased spend allocation. |

### Blended ROAS Scalar

- **ROAS < 1.5:** Toan bo chi tieu marketing can xem lai — doanh thu khong bu chi phi.
- **ROAS 1.5–3.0:** Hop ly. Theo doi bien lai theo kenh de dam bao khong co kenh thua lo an vao tong.
- **ROAS > 3.0:** Hieu qua tot. Xem profitable ROAS de xac nhan loi nhuan thuc.

### Channel ROI Quadrant Interpretation

```
Quadrant (ROAS × Margin):

High ROAS / High Margin  → SCALE UP      (top-right, ideal)
High ROAS / Low Margin   → RED FLAG      (top-left: revenue but no profit)
Low ROAS  / High Margin  → OPTIMIZE      (bottom-right: small but healthy)
Low ROAS  / Low Margin   → CUT           (bottom-left: unprofitable)
```

## Implementation Notes

- **profitable_roas formula:** `gross_profit / spend` (equivalent to `ROAS × margin %`). NULLIF guards on spend = 0.
- **has_cogs caveat:** `fact_order_economics.has_cogs = FALSE` means MISA COGS not matched → gross_profit = net_revenue (100% margin, misleading). Orders without COGS inflate profitable ROAS. Monitor COGS coverage rate.
- **Scope:** Only completed orders (`status = 'COMPLETED'`) joined to channels with marketing spend. Non-spend channels excluded from profitable ROAS table.
- **No cross-collection dependency:** This playbook is self-contained. Marketing team does not need Finance dashboard access to use it.
- **Differs from Marketing Monthly Analysis:** Monthly Analysis covers CAC, LTV, cohort retention. This dashboard is spend-efficiency focused (ROAS + margin) with live 30-day rolling window.

# Playbook: Customer Operational Dashboard

## Overview

- **Audience:** Customer Success Manager, Sales Ops — daily operational check
- **Goal:** Monitor customer health, identify at-risk customers for proactive outreach, track acquisition quality, and prioritize reactivation efforts.
- **Metabase Collection:** `Marketing & Customers`
- **Cadence:** Daily check (Tab 1: 5 min), Weekly deep-dive (Tab 2-3: 15-20 min)

## Data Lineage

- **Core Model:** [`dim_customers`](../../../transformation/models/marts/core/dim_customers.sql)
- **Fact Tables:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
- **Dimensions:** `dim_channels`

## Dashboard Structure (3 Tabs)

### Tab 1: Tong quan (Overview)
- **Purpose:** Answer "Customer base khoe khong?"
- **Hero:** MAU with 30-day rolling comparison
- **Key visuals:** 4 KPIs (MAU, New, At Risk, Churned), status donut, segment donut, active rate gauge, New vs Returning stacked area, MAU trend line

### Tab 2: Kenh & Dia ly (Channels & Geography)
- **Purpose:** Answer "Khach moi den tu dau?"
- **Key visuals:** Acquisition combo chart with MoM% (6M), channel ranking (count + revenue), geographic distribution (count + LTV)

### Tab 3: Watchlist & Hanh dong (Action)
- **Purpose:** Answer "Ai can cham soc ngay?"
- **Key visuals:** RFM health matrix with conditional formatting, VIP watchlist with recency alerts, at-risk priority by LTV, churned high-value recovery list

## How to Read

1. **CONTEXT** — Dashboard theo doi suc khoe customer base hang ngay. Khong phai monthly report — la cong cu operational de biet ai can goi, ai sap mat.
2. **KEY FINDING** — Tab 1 KPI row: MAU trend len hay xuong? Bao nhieu At Risk? Status donut va gauge cho biet ty le Active.
3. **EVIDENCE** — New vs Returning stacked area cho thay growth quality. Neu Returning giam = retention co van de. MAU trend line cho thay momentum.
4. **IMPLICATIONS** — Neu At Risk tang manh, can tang cuong outreach truoc khi ho churn. Neu New Customers giam, review kenh acquisition.
5. **ACTIONS** — Tab 3 la noi hanh dong. VIP at-risk can goi ngay (sort by recency). At-Risk cao LTV can chien dich reactivation. Churned high-value can recovery campaign.

## Key Metrics Reference

| Metric | Definition | Source | Threshold |
|--------|-----------|--------|-----------|
| MAU | Customers with orders in last 30 days | fact_orders | — |
| Active | recency_days <= 30 | dim_customers | — |
| At Risk | recency_days 31-90 | dim_customers | Escalate if count trending up |
| Churned | recency_days > 90 | dim_customers | — |
| VIP | lifetime_value > 10M VND | dim_customers | Priority for retention |
| Loyal | lifetime_value 5M-10M VND | dim_customers | — |
| Regular | lifetime_value < 5M VND | dim_customers | — |

## Implementation Notes

- **Design Spec:** [designs/customer_operational_dashboard.md](../designs/customer_operational_dashboard.md)
- **Blueprint:** [blueprints/customer_operational_dashboard.md](../blueprints/customer_operational_dashboard.md)
- **Domain Reference:** [domains/customer.md](../domains/customer.md)

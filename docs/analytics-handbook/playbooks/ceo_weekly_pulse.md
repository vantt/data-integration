# Playbook: CEO Weekly Pulse

## Overview

- **Audience:** CEO, Co-Founders
- **Goal:** 5-minute weekly check-in — answer "Are we on track this week?" across Revenue, Channels, and Customer Health.
- **Cadence:** Every Monday morning, reviewing the previous Mon–Sun.
- **Archetype:** Operational Cockpit
- **Collection:** `Executive`
- **Design Spec:** [CEO Weekly Pulse (Redesign)](../designs/ceo_weekly_pulse.md)

## Key Questions

1. **Revenue:** Net Revenue va Gross Revenue tuan nay so voi tuan truoc? Dang on-track de dat target thang khong?
2. **Profitability:** Net Profit va Gross Margin % tuan nay la bao nhieu? Co kenh nao dang lo khong?
3. **Growth Drivers:** Kenh nao tang, kenh nao giam so voi tuan truoc? Cau truc Ecommerce/Offline thay doi the nao?
4. **Customer Health:** Bao nhieu khach moi? Ty le doanh thu tu khach cu co healthy (> 60%)?
5. **Operational Flags:** Co gi bat thuong can chu y (hoan tra tang dot bien, discount qua nhieu, don huy tang)?

## Dashboard Structure (3 Tabs)

### Tab 1 — Doanh thu & Target (Primary)
CEO mo tab nay dau tien — tra loi "tuan nay on khong?" trong 2 phut.

- **Hero:** Net Revenue voi WoW trend arrow
- **Supporting KPIs:** Gross Revenue, Total Orders, AOV — tat ca co WoW %
- **MTD Progress:** Progress bar visual — da dat bao nhieu % target thang
- **Pace Index:** Ahead/Behind indicator — so sanh toc do hien tai voi expected pace
- **14-Day Trend:** Area chart doanh thu 14 ngay — this week vs previous week
- **Profitability Row:** 3 scalars WoW — Net Profit, Gross Margin %, Loss-Making Channel Count (alert)

### Tab 2 — Kenh ban hang
CEO chuyen sang tab nay khi muon biet "kenh nao dang drive?"

- **Channel Mix Donut:** Online-Ecommerce / Offline / Internal — part-to-whole
- **WoW Comparison:** Grouped bar — so sanh truc tiep this week vs last week theo category
- **Top Channels:** Horizontal bar chart — ranking kenh theo revenue
- **Performance Table:** Chi tiet tung kenh voi WoW %, conditional formatting highlight bien dong lon

### Tab 3 — Khach hang & Canh bao
CEO chuyen sang tab nay khi muon kiem tra customer health va red flags.

- **New Customers:** So khach moi voi WoW trend
- **Returning Revenue %:** Gauge — healthy > 60%, warning 40-60%, alert < 40%
- **New vs Returning Trend:** Stacked bar 14 ngay — cau thanh don hang theo ngay
- **Red Flags Row:** Cancelled Orders, Returns, Discount Rate — co conditional coloring

## Filters

- **No interactive filters** — zero-interaction. CEO mo va doc.
- **Business constraint:** Loai bo don kenh US (internal, 100% discount).

## Visualizations

| Section | Domain | Type | Metric |
|:---|:---|:---|:---|
| Revenue KPIs | [Net Revenue](../domains/sales.md#2-net-revenue) | Scalar + WoW | Net Revenue, Gross Revenue, Orders, AOV |
| MTD Progress | [Target Achievement Rate](../domains/sales.md#15-target-achievement-rate) | Progress bar + Gauge | GMV vs Target, Pace Index |
| Revenue Trend | [Net Revenue](../domains/sales.md#2-net-revenue) | Area chart (14d) | Daily Net Revenue |
| **Profitability** | [Order Gross Profit](../domains/finance.md#9-order-gross-profit), [Channel Net Profit](../domains/finance.md#10-channel-net-profit-lãi-ròng-kênh) | Scalar + WoW / Alert | Net Profit WoW, Gross Margin % WoW, Loss-Making Channel Count |
| Channel Mix | [Sales by Channel](../domains/sales.md#8-sales-by-channel) | Pie, Bar, Table | Revenue split by channel |
| Customer Health | [New vs Returning](../domains/sales.md#10-new-vs-returning-customers) | Scalar + Gauge + Stacked Bar | Acquisition, retention rate |
| Operational Flags | — | Scalar + Gauge | Cancelled orders, Returns, Discount Rate |

## Data Lineage

- **Core Models:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql), [`fact_targets`](../../../transformation/models/marts/core/fact_targets.sql), [`fact_order_economics`](../../../transformation/models/marts/sales/fact_order_economics.sql)
- **Dimensions:** `dim_channels`, `dim_customers`

## How to Read This Dashboard

1. **CONTEXT:** Dashboard nay ton tai de CEO kiem tra suc khoe kinh doanh moi sang thu Hai. Tra loi: "Tuan qua co on-track khong?"
2. **KEY FINDING:** Nhin Net Revenue (Hero) va WoW arrow truoc. Xanh len = tot. Do xuong = can chu y.
3. **EVIDENCE:** MTD Progress bar cho biet dang ahead hay behind target thang. Pace Index > 1.0 = dang vuot toc do can thiet.
4. **IMPLICATIONS:** Neu behind target + kenh chinh giam → can tang marketing hoac khuyen mai.
5. **ACTIONS:** Neu Red Flags (Tab 3) co bat thuong → chuyen thong tin cho team lien quan xu ly trong tuan.

## Implementation Notes

- **Max ~26 visual elements** across 3 tabs (~10 per tab). CEO scans, doesn't drill.
- Use **"compare to previous period"** feature on all scalar KPIs for automatic WoW arrows.
- Consider **auto-subscription**: Email/Slack push every Monday 8:00 AM.
- This dashboard does NOT replace the daily ops dashboard — it provides the "so what?" summary.

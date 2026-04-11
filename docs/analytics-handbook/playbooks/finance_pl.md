# Playbook: Finance P&L Dashboard

## Overview

- **Audience:** CFO, Finance Managers, CEO
- **Goal:** Monthly Profit & Loss analysis: doanh thu (Sapo) vs giá vốn (MISA) vs chi phí sàn (Shopee). Drill-down theo kênh, sản phẩm, thời gian.
- **Collection:** `Executive`
- **Design Spec:** [designs/finance_pl.md](../designs/finance_pl.md) *(to be created)*

## Data Lineage

- **Revenue:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql) — Sapo order-level revenue
- **COGS & Margin:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql) — MISA invoice-line with COGS
- **Shopee Fees:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql) — Shopee platform economics
- **Dimensions:** [`dim_date`](../../../transformation/models/marts/core/dim_date.sql), [`dim_channels`](../../../transformation/models/marts/core/dim_channels.sql)

## Reading Flow

1. **KPI Overview** — Doanh thu thuần, COGS, Lãi gộp, Gross Margin %. On-track hay không?
2. **Trend** — Doanh thu vs COGS theo tháng, margin có duy trì?
3. **Channel breakdown** — Kênh nào biên lãi cao, kênh nào ăn mòn lợi nhuận?
4. **Shopee economics** — Phí sàn chiếm bao nhiêu % doanh thu Shopee?
5. **Action** — Tối ưu product mix cho kênh margin cao, đánh giá chi phí Shopee.

## Filters

- **Date Range:** Month-to-Date (MTD), Last Month, Year-to-Date (YTD).
- **Channel:** Filter by channel_name (MISA) or channel_category (Sapo).

## Action Triggers

| Metric | Threshold | Owner | Action |
|--------|-----------|-------|--------|
| Gross Margin % | < 25% tổng hoặc bất kỳ kênh nào | Finance | Review giá vốn, kiểm tra nhà cung cấp |
| Shopee Settlement Margin | < 60% | Marketing | Đánh giá lại chi phí quảng cáo sàn, giá bán |
| COGS Ratio | > 75% cho bất kỳ sản phẩm nào | Merchandising | Review giá bán hoặc tìm nguồn cung rẻ hơn |
| Monthly Revenue MoM | < -15% | CEO | Kiểm tra breakdown kênh + sản phẩm |

## Visualizations

### Tab 1: P&L Overview

| Chart Title              | Visualization Type | Metric Reference (Link to Domain)                                         | Notes/Config                              |
| :----------------------- | :----------------- | :------------------------------------------------------------------------ | :---------------------------------------- |
| **Net Revenue MTD**      | Scalar             | [Net Revenue](../domains/finance.md#2-net-revenue)                        | fact_orders, filter MTD. VND currency.    |
| **COGS MTD**             | Scalar             | [COGS](../domains/finance.md#4-cogs-giá-vốn-hàng-bán)                    | int_misa_sales_lines, filter MTD.         |
| **Gross Profit MTD**     | Scalar             | [Gross Profit](../domains/finance.md#5-gross-profit-lãi-gộp)             | revenue - COGS.                           |
| **Gross Margin %**       | Scalar             | [Gross Margin %](../domains/finance.md#6-gross-margin--biên-lợi-nhuận-gộp) | Threshold: green >40%, red <25%.       |
| **Revenue vs COGS Trend**| Combo Chart        | [Net Revenue](../domains/finance.md#2-net-revenue), [COGS](../domains/finance.md#4-cogs-giá-vốn-hàng-bán) | Line: Revenue & COGS by month. Bar: Gross Profit. |
| **Revenue Waterfall**    | Waterfall          | [Revenue Breakdown](../domains/finance.md#3-revenue-breakdown-waterfall-components) | Gross → Discounts → Tax → Net.   |

### Tab 2: Channel Profitability

| Chart Title               | Visualization Type | Metric Reference (Link to Domain)                                          | Notes/Config                              |
| :------------------------ | :----------------- | :------------------------------------------------------------------------- | :---------------------------------------- |
| **Margin by Channel**     | Horizontal Bar     | [Gross Margin by Channel](../domains/finance.md#7-gross-margin-by-channel) | int_misa_sales_lines. Sort by margin %.   |
| **Revenue vs COGS by Ch** | Stacked Bar        | [COGS](../domains/finance.md#4-cogs-giá-vốn-hàng-bán)                     | Revenue (blue) + COGS (red) per channel.  |
| **COGS Ratio Trend**      | Line Chart         | [COGS Ratio](../domains/finance.md#8-cogs-ratio-tỷ-lệ-giá-vốndoanh-thu)  | Monthly trend per channel.                |
| **Channel Mix (Revenue)** | Pie/Donut          | [Gross Margin by Channel](../domains/finance.md#7-gross-margin-by-channel) | Revenue share by channel_name.            |

### Tab 3: Shopee Economics

| Chart Title                 | Visualization Type | Metric Reference (Link to Domain)                                                 | Notes/Config                               |
| :-------------------------- | :----------------- | :-------------------------------------------------------------------------------- | :----------------------------------------- |
| **Shopee Settlement MTD**   | Scalar             | [Shopee Net Settlement](../domains/finance.md#12-shopee-net-settlement-tổng-phát-hành) | int_shopee_order_fees, filter MTD.    |
| **Settlement Margin %**     | Scalar             | [Shopee Settlement Margin](../domains/finance.md#15-shopee-settlement-margin-biên-lợi-nhuận-sàn) | Threshold: green >75%, red <60%. |
| **Platform Fee Rate %**     | Scalar             | [Shopee Platform Fee Rate](../domains/finance.md#13-shopee-platform-fee-rate-tỷ-lệ-phí-sàn) | Target: < 15%.                      |
| **Fee Breakdown**           | Horizontal Bar     | [Shopee Fee Breakdown](../domains/finance.md#14-shopee-fee-breakdown)             | Stacked or individual bars per fee type.   |
| **Settlement Trend**        | Line Chart         | [Shopee Net Settlement](../domains/finance.md#12-shopee-net-settlement-tổng-phát-hành) | Monthly trend: gross_revenue vs net_settlement. |
| **Revenue → Settlement Flow** | Waterfall        | [Shopee Fee Breakdown](../domains/finance.md#14-shopee-fee-breakdown)             | Gross Revenue → -Fees → -Tax → Settlement. |

## Implementation Notes

### Data Alignment Caveats

1. **Sapo vs MISA grain mismatch:** Sapo `fact_orders` is per-order; MISA `int_misa_sales_lines` is per-invoice-line. Aggregate to monthly level before comparing.
2. **Shopee overlap:** Shopee orders appear in both Sapo (as channel) and `int_shopee_order_fees`. Use Shopee fees model for economics; Sapo for top-line revenue.
3. **MISA channel mapping:** `channel_code` values are DAILY, ECOM, CS, KHAC. Use `channel_name` for display. `voucher_source_hint` (SAPO_DEALER, SHOPEE, AEON, OTHER) adds sub-channel detail.
4. **Promo lines:** Filter `WHERE NOT is_promo_line` for margin analysis to exclude gift/promo items with zero revenue.

### What's NOT Covered (Requires `fact_gl_entries`)

- Operating expenses (salaries, rent, marketing spend beyond Shopee fees)
- Operating Margin %, Net Margin %, EBITDA
- Full P&L statement format
- Balance Sheet metrics

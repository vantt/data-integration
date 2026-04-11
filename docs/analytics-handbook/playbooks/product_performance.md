# Playbook: Product Performance

## Overview

- **Audience:** Merchandising, Management
- **Goal:** Monitor sales velocity and revenue contribution by product.
- **Collection:** `Product Analytics`
- **Design Spec:** [designs/product_performance.md](../designs/product_performance.md)

## Data Lineage

- **Core Model:** [`fact_sales`](../../../transformation/models/marts/sales/fact_sales.sql) (velocity & revenue)
- **Profitability:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql) (COGS & margin)
- **Dimensions:** [`dim_products`](../../../transformation/models/marts/core/dim_products.sql), [`dim_product_types`](../../../transformation/models/marts/core/dim_product_types.sql)

## Reading Flow

1. **Tong quan** — Hero: Doanh thu san pham (MoM). On-track hay khong?
2. **Trend** — Doanh thu theo ngay co duy tri momentum?
3. **Category breakdown** — Loai SP nao drive tang truong, loai nao sut giam?
4. **Top/Bottom products** — San pham cu the nao dang ban chay, san pham nao can can thiep?
5. **Action** — Dieu chinh product mix, day kenh cho SP tiem nang, review SP sut giam.

## Filters

- **Khoang thoi gian:** Last 30 Days (default).
- **Loai san pham:** Filter by Product Type.
- **Kenh ban hang:** Filter by Channel.

## Action Triggers

| Metric | Threshold | Owner | Action |
|--------|-----------|-------|--------|
| Doanh thu san pham | MoM < -10% | Merchandising | Kiem tra breakdown theo loai SP va kenh ban hang |
| Doanh thu san pham | MoM > +20% | Management | Xac minh nguon tang — promotion hay organic growth |
| Tang truong loai SP | MoM < -15% cho bat ky loai nao | Merchandising | Review product mix, kiem tra ton kho |
| SP sut giam | MoM < -30% | Merchandising | Canh bao gap, kiem tra het hang hay trend thi truong |
| Daily velocity | < 1 unit/day cho SP chu luc | Merchandising | Review gia ban, vi tri trung bay, marketing |

## Visualizations

### Section 1: Sales Velocity

| Chart Title              | Visualization Type | Metric Reference (Link to Domain)                          | Notes/Config               |
| :----------------------- | :----------------- | :--------------------------------------------------------- | :------------------------- |
| **Revenue Contribution** | Horizontal Bar     | [Product Revenue](../domains/product.md#2-product-revenue) | Top 20 products by revenue. Replaced Treemap for readability. |
| **Top Movers**           | Horizontal Bar     | [Units Sold](../domains/product.md#1-units-sold)           | Top 20 products by volume. |

### Section 2: Category Analysis

| Chart Title            | Visualization Type | Metric Reference (Link to Domain)                          | Notes/Config                 |
| :--------------------- | :----------------- | :--------------------------------------------------------- | :--------------------------- |
| **Category Mix Trend** | Stacked Area       | [Product Revenue](../domains/product.md#2-product-revenue) | Group by Category Over Time. |
| **Category Growth MoM** | Horizontal Bar (conditional) | [Product Revenue](../domains/product.md#2-product-revenue) | MoM % change by category. |

### Section 3: Profitability (MISA COGS)

> **Status: Ready** — MISA sales ledger provides product-level COGS and gross margin.
> **Source:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql)

| Chart Title                    | Visualization Type | Metric Reference (Link to Domain)                                           | Notes/Config                                          |
| :----------------------------- | :----------------- | :-------------------------------------------------------------------------- | :---------------------------------------------------- |
| **Gross Margin %**             | Scalar             | [Gross Margin by Product](../domains/product.md#4-gross-margin-by-product)  | Overall margin %. Threshold: >40% healthy.            |
| **Top Products by Profit**     | Horizontal Bar     | [Gross Margin by Product](../domains/product.md#4-gross-margin-by-product)  | Top 20 products ranked by gross_profit (absolute).    |
| **Margin by Channel**          | Horizontal Bar     | [Gross Margin by Category/Channel](../domains/product.md#5-gross-margin-by-categorychannel) | Compare DAILY vs ECOM vs CS margin %. |
| **Low-Margin Products**        | Table              | [Product-Level COGS](../domains/product.md#3-product-level-cogs-giá-vốn-theo-sản-phẩm) | Products with margin < 30%. Alert list. |

### Section 4: Planned — Inventory-dependent (requires `fact_inventory`)

> **Status: Planned** — `fact_inventory` model does not exist yet. Metrics below will be added when inventory data pipeline is built.

| Chart Title            | Visualization Type | Metric Reference (Link to Domain)                                          | Notes/Config                            |
| :--------------------- | :----------------- | :------------------------------------------------------------------------- | :-------------------------------------- |
| **OOS Rate**           | Gauge              | [OOS Rate](../domains/product.md#10-out-of-stock-oos-rate)                 | Requires `fact_inventory`. Planned.     |
| **Inventory Turnover** | Single Value       | [Inventory Turnover](../domains/product.md#7-inventory-turnover)           | Requires `fact_inventory`. Planned.     |

## Implementation Notes

### Best Practices

1. **ABC Analysis**: Classify products (A=Top 20%, B=Next 30%, C=Bottom 50%) for inventory prioritization.
2. **Seasonality**: Compare velocity against the same period last year.
3. **Bundling**: Analyze "frequently bought together" patterns for upsell opportunities.
4. **Historical Stock**: Snapshot inventory levels daily to enable trend analysis.

### Common Pitfalls

- Ignoring returns when calculating net product revenue.
- Calculating days of supply based on average instead of peak demand.
- Not differentiating new product launches from slow movers in analysis.

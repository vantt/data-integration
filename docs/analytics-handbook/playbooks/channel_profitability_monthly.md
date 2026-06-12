# Playbook: Channel Profitability Monthly

## Overview

- **Audience:** CEO, Finance, Sales Director
- **Goal:** So sánh biên lợi nhuận gộp giữa các kênh bán hàng (DAILY, ECOM, CS, KHAC) dựa trên dữ liệu MISA. Xác định kênh nào tạo margin cao nhất và kênh nào đang ăn mòn lợi nhuận.
- **Tool:** metabase
- **Collection:** `Analytics`
- **Design Spec:** [designs/channel_profitability_monthly.md](../designs/channel_profitability_monthly.md)

## Data Lineage

- **Primary:** [`int_misa_sales_lines`](../../../transformation/models/intermediate/misa/int_misa_sales_lines.sql) — per-invoice-line with COGS, margin, channel enrichment
- **Domain:** [Finance > COGS & Margin](../domains/finance.md#context-cogs--margin--misa-sales-ledger), [Product > Gross Margin](../domains/product.md#4-gross-margin-by-product)

## Reading Flow

1. **Tổng quan margin** — Gross Margin % tổng. Kỳ này biên lợi nhuận có đạt target?
2. **So sánh kênh** — Kênh nào margin cao nhất? Kênh nào thấp nhất? Gap bao nhiêu?
3. **Trend** — Margin từng kênh thay đổi thế nào qua các tháng?
4. **Product drill-down** — Sản phẩm nào đang kéo margin xuống?
5. **Action** — Điều chỉnh product mix, chính sách giá theo kênh, hoặc đánh giá lại kênh margin thấp.

## Filters

- **Thời gian:** Filter by posting_date. Default: Last 3 Months.
- **Kênh:** Filter by channel_name (optional).
- **Loại trừ promo:** `WHERE NOT is_promo_line` (business constraint).

## Action Triggers

| Metric | Threshold | Owner | Action |
|--------|-----------|-------|--------|
| Gross Margin % tổng | < 25% | Finance | Kiểm tra giá vốn tăng hay giá bán giảm. Review nhà cung cấp. |
| Gross Margin % kênh | Chênh lệch > 15 điểm % giữa kênh cao nhất và thấp nhất | Sales Director | Đánh giá chiến lược kênh: đẩy traffic sang kênh margin cao hơn? |
| Gross Margin trend | Giảm > 5 điểm % MoM cho bất kỳ kênh nào | Finance | Deep dive: sản phẩm nào gây sụt giảm? COGS tăng hay discount nhiều? |
| Product margin | < 15% cho sản phẩm chiếm > 5% doanh thu | Merchandising | Review giá bán, tìm nguồn cung rẻ hơn, hoặc giảm promotion cho SP đó |
| ECOM vs DAILY gap | ECOM margin < DAILY margin - 10 điểm % | Sales Director | Phí sàn ăn mòn quá nhiều? Xem dashboard Shopee Channel Economics. |

## Visualizations

### Tab 1: Channel Overview

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
|:---|:---|:---|:---|
| **Gross Margin %** | Gauge | [Gross Margin %](../domains/finance.md#6-gross-margin--biên-lợi-nhuận-gộp) | Zones: green >40%, yellow 25-40%, red <25%. Hero. |
| **Total Revenue** | Scalar | Revenue from int_misa_sales_lines | revenue_net_of_discount, VND. MoM comparison. |
| **Total COGS** | Scalar | [COGS](../domains/finance.md#4-cogs-giá-vốn-hàng-bán) | cogs_amount, VND. MoM comparison. |
| **Total Gross Profit** | Scalar | [Gross Profit](../domains/finance.md#5-gross-profit-lãi-gộp) | gross_profit, VND. MoM comparison. |
| **Margin by Channel** | Horizontal Bar | [Gross Margin by Channel](../domains/finance.md#7-gross-margin-by-channel) | Sorted by margin %. Color: conditional (green >40%, red <25%). |
| **Revenue vs COGS by Channel** | Grouped Bar | [COGS](../domains/finance.md#4-cogs-giá-vốn-hàng-bán) | Revenue (blue) vs COGS (red) per channel. Side-by-side. |

### Tab 2: Trends & Product Detail

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
|:---|:---|:---|:---|
| **Margin Trend by Channel** | Multi-Line Chart | [Gross Margin by Channel](../domains/finance.md#7-gross-margin-by-channel) | Monthly margin % per channel_name. 3-5 series. |
| **Revenue Mix Trend** | Stacked Bar (Time) | Revenue by channel | Monthly stacked bars: share of each channel. |
| **Top Products by Profit** | Horizontal Bar | [Gross Margin by Product](../domains/product.md#4-gross-margin-by-product) | Top 15 products by absolute gross_profit. |
| **Low-Margin Products** | Table (Formatted) | [Product-Level COGS](../domains/product.md#3-product-level-cogs-giá-vốn-theo-sản-phẩm) | Products with margin < 25%, sorted ASC. Highlight < 15% red. Filter: revenue > threshold. |

## Implementation Notes

### Data Caveats

1. **MISA vs Sapo grain:** MISA is per-invoice-line; Sapo is per-order. Do not cross-join directly. Aggregate to monthly/channel level for comparison.
2. **Channel mapping:** `channel_code` values: DAILY (bán lẻ), ECOM (thương mại điện tử), CS (công sở/B2B), KHAC (khác). Use `channel_name` for display.
3. **Voucher source hint:** `voucher_source_hint` adds sub-channel detail (SAPO_DEALER, SHOPEE, AEON, OTHER) but is heuristic — not 100% accurate.
4. **Promo lines:** Always filter `WHERE NOT is_promo_line` to exclude gift/promo items with zero revenue that distort margin.
5. **Cross-reference:** For Shopee-specific fee analysis, link to [Shopee Channel Economics](shopee_channel_economics.md) dashboard.

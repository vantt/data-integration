# Playbook: Shopee Channel Economics

## Overview

- **Audience:** Sales Ops, CS Lead, Finance
- **Goal:** Giám sát chi phí bán hàng trên Shopee — phí sàn, phí vận chuyển, thuế, và tỷ lệ tiền thực nhận (settlement margin). Giúp tối ưu hóa lợi nhuận kênh Shopee.
- **Collection:** `Operations > Periodic Reviews`
- **Design Spec:** [designs/shopee_channel_economics.md](../designs/shopee_channel_economics.md)

## Data Lineage

- **Primary:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql) — per-order fee breakdown with net_settlement
- **Product detail:** [`int_shopee_order_items`](../../../transformation/models/intermediate/shopee/int_shopee_order_items.sql) — per-order × product SKU line items
- **COGS/Economics:** [`fact_order_economics`](../../../transformation/models/mart/fact_order_economics.sql) — MISA-matched COGS, gross_profit, channel_net_profit. JOIN via order_code.
- **Domain:** [Finance > Shopee Platform Economics](../domains/finance.md#context-shopee-platform-economics)

## Reading Flow

1. **Settlement overview** — Gross Revenue vs Net Settlement, Settlement Margin %. Shopee đang giữ lại bao nhiêu %?
2. **Fee breakdown** — Loại phí nào chiếm nhiều nhất? Service fee, payment fee, hay phí hạ tầng?
3. **Trend** — Settlement margin đang cải thiện hay xấu đi theo thời gian?
4. **Product detail** — Sản phẩm/đơn hàng nào có tỷ lệ settlement thấp nhất?
5. **P&L Cascade** — True margin sau khi trừ cả COGS. Đơn hàng nào thực sự lỗ?
6. **Action** — Tối ưu giá bán, giảm phí không cần thiết, đánh giá lại chiến lược Shopee.

## Filters

- **Payout period:** Filter by payout_released_at. Default: Last 30 Days.
- **Order type:** Filter by order_type (optional).

## Action Triggers

| Metric | Threshold | Owner | Action |
|--------|-----------|-------|--------|
| Settlement Margin % | < 60% tổng | Sales Ops | Review giá bán, kiểm tra các khoản phí bất thường |
| Platform Fee Rate | > 20% | Sales Ops | Liên hệ Shopee xác minh mức phí, kiểm tra tier/chương trình |
| Single order settlement | < 50% | CS Lead | Kiểm tra đơn hàng cụ thể — có hoàn hàng, voucher lớn? |
| Settlement margin MoM | Giảm > 5 điểm % | Finance | Phân tích nguyên nhân: phí tăng hay doanh thu giảm? |
| Infrastructure + Xtra fee | > 5% doanh thu | Sales Ops | Đánh giá lại đăng ký dịch vụ Shopee (quảng cáo, Xtra) |

### Shopee P&L Cascade Triggers

| Metric | Threshold | Owner | Action |
|--------|-----------|-------|--------|
| True Margin % (nhóm < 100K) | < 0% | Finance / Ops | Nhóm đơn nhỏ đang lỗ thật sau COGS — xem xét tăng giá tối thiểu hoặc tắt flash sale cho SKU có giá thấp |
| True Margin % (tổng) | < 10% | Finance | Biên lợi nhuận thực mỏng — cần rà soát COGS và chiến lược giá trên Shopee |
| Orders Below Breakeven count | > 5% tổng đơn | Finance / Ops | Hơn 5% đơn đang lỗ — kích hoạt review sản phẩm, giá bán, và chương trình voucher |
| COGS % of Net Revenue | > 70% | Finance | Chi phí hàng hóa chiếm quá lớn — rà soát supplier pricing hoặc product mix |
| Service Fee % of Net Revenue | > 10% | Sales Ops | Phí dịch vụ Shopee quá cao — kiểm tra tier hoa hồng, đàm phán lại nếu có thể |

## Visualizations

### Tab 1: Settlement Overview

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
|:---|:---|:---|:---|
| **Settlement Margin %** | Gauge | [Shopee Settlement Margin](../domains/finance.md#15-shopee-settlement-margin-biên-lợi-nhuận-sàn) | Zones: green >75%, yellow 60-75%, red <60%. Hero card. |
| **Gross Revenue** | Scalar | [Gross Revenue](../domains/finance.md#1-gross-revenue-gmv) | Shopee gross_revenue, VND. vs prev period. |
| **Net Settlement** | Scalar | [Shopee Net Settlement](../domains/finance.md#12-shopee-net-settlement-tổng-phát-hành) | net_settlement, VND. vs prev period. |
| **Platform Fee Rate %** | Scalar | [Shopee Platform Fee Rate](../domains/finance.md#13-shopee-platform-fee-rate-tỷ-lệ-phí-sàn) | Total fees / gross_revenue. vs prev period. |
| **Fee Breakdown** | Horizontal Bar | [Shopee Fee Breakdown](../domains/finance.md#14-shopee-fee-breakdown) | Ranked by amount: service_fee, payment_fee, etc. |
| **Revenue → Settlement Waterfall** | Waterfall | [Shopee Fee Breakdown](../domains/finance.md#14-shopee-fee-breakdown) | Gross Revenue → -Service Fee → -Payment Fee → ... → Net Settlement. |

### Tab 2: Trends & Details

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
|:---|:---|:---|:---|
| **Settlement Margin Trend** | Line Chart | [Shopee Settlement Margin](../domains/finance.md#15-shopee-settlement-margin-biên-lợi-nhuận-sàn) | Monthly trend. Reference line at 75%. |
| **Fee Composition Trend** | Stacked Bar (Time) | [Shopee Fee Breakdown](../domains/finance.md#14-shopee-fee-breakdown) | Monthly stacked bars by fee type. |
| **Orders with Lowest Settlement** | Table (Formatted) | [Shopee Net Settlement](../domains/finance.md#12-shopee-net-settlement-tổng-phát-hành) | Bottom 20 orders by settlement %. Highlight < 50% red. |
| **Product Settlement Summary** | Table | Product-level settlement | Group by product, show revenue, settlement, margin %. Sort by margin % ASC. |

### Tab 3: Shopee P&L Cascade

| Chart Title | Visualization Type | Metric Reference | Notes/Config |
|:---|:---|:---|:---|
| **Shopee Margin vs COGS Scatter** | Scatter (Bubble) | true_margin = (net_settlement - cogs_amount) / gross_revenue | Bubble size = order count per bucket. Breakeven ref line at 0%. Only MISA-matched orders have COGS. |
| **Cost Waterfall % of Net Revenue** | Horizontal Bar | % của net_revenue: COGS, service_fee, payment_fee, etc. | Chỉ trên tập has_cogs=TRUE. Hiện rõ loại chi phí nào "cắn" margin nhiều nhất. |
| **Orders Below Breakeven** | Table (Formatted) | true_profit = net_settlement - cogs_amount | Top 50 đơn lỗ nhất. Highlight đỏ toàn hàng. |

## Implementation Notes

### Data Caveats

1. **Payout timing:** Orders appear in data only after payout is released. Recent orders may not be included yet.
2. **Fee signs:** Most fee fields are negative in source data. Use `ABS()` for display, keep sign for waterfall.
3. **Refund orders:** Refund amounts reduce gross_revenue. Settlement margin may appear inflated for periods with many refunds (denominator shrinks).
4. **Infrastructure + Xtra fees:** Come from a separate sheet (Service Fee Details). LEFT JOIN — some orders may not have these fees.
5. **P&L Cascade — COGS join caveat:** Tab 3 joins `int_shopee_order_fees` (Shopee fees) with `fact_order_economics` (MISA COGS). Only orders with `has_cogs=TRUE` have real COGS data. Orders without MISA match show `true_margin` inflated (no COGS deducted). The scatter and cost waterfall filter to `has_cogs=TRUE` to avoid misleading analysis. Coverage % displayed as "Don co COGS (MISA)" column in scatter chart.

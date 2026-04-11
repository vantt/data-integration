# Playbook: Shopee Channel Economics

## Overview

- **Audience:** Sales Ops, CS Lead, Finance
- **Goal:** Giám sát chi phí bán hàng trên Shopee — phí sàn, phí vận chuyển, thuế, và tỷ lệ tiền thực nhận (settlement margin). Giúp tối ưu hóa lợi nhuận kênh Shopee.
- **Collection:** `Operations > Periodic Reviews`
- **Design Spec:** [designs/shopee_channel_economics.md](../designs/shopee_channel_economics.md)

## Data Lineage

- **Primary:** [`int_shopee_order_fees`](../../../transformation/models/intermediate/shopee/int_shopee_order_fees.sql) — per-order fee breakdown with net_settlement
- **Product detail:** [`int_shopee_order_items`](../../../transformation/models/intermediate/shopee/int_shopee_order_items.sql) — per-order × product SKU line items
- **Domain:** [Finance > Shopee Platform Economics](../domains/finance.md#context-shopee-platform-economics)

## Reading Flow

1. **Settlement overview** — Gross Revenue vs Net Settlement, Settlement Margin %. Shopee đang giữ lại bao nhiêu %?
2. **Fee breakdown** — Loại phí nào chiếm nhiều nhất? Service fee, payment fee, hay phí hạ tầng?
3. **Trend** — Settlement margin đang cải thiện hay xấu đi theo thời gian?
4. **Product detail** — Sản phẩm/đơn hàng nào có tỷ lệ settlement thấp nhất?
5. **Action** — Tối ưu giá bán, giảm phí không cần thiết, đánh giá lại chiến lược Shopee.

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

## Implementation Notes

### Data Caveats

1. **Payout timing:** Orders appear in data only after payout is released. Recent orders may not be included yet.
2. **Fee signs:** Most fee fields are negative in source data. Use `ABS()` for display, keep sign for waterfall.
3. **Refund orders:** Refund amounts reduce gross_revenue. Settlement margin may appear inflated for periods with many refunds (denominator shrinks).
4. **Infrastructure + Xtra fees:** Come from a separate sheet (Service Fee Details). LEFT JOIN — some orders may not have these fees.

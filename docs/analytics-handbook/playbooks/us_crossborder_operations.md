# Playbook: US CrossBorder Operations [US]

## Overview

- **Audience:** US Operations, Sales Ops Lead
- **Goal:** Theo dõi hàng ngày các đơn hàng US CrossBorder Fulfillment — doanh thu, trạng thái đơn, fulfillment pipeline, và cảnh báo SKU thiếu giá.
- **Tool:** metabase
- **Collection:** `Operations > US CrossBorder`
- **Cadence:** Daily (default: this month)
- **Archetype:** Operational Monitor
- **Blueprint:** [blueprints/us_crossborder_operations.md](../blueprints/metabase/us_crossborder_operations.md)

## Key Questions

- Kỳ này có bao nhiêu đơn US? Doanh thu và AOV so với kỳ trước?
- Phân bổ trạng thái đơn (order status) và fulfillment status hiện tại ra sao?
- Xu hướng doanh thu và số đơn theo ngày trong kỳ có đột biến không?
- Đơn nào đang có SKU thiếu giá trong price list US?
- SKU nào cần bổ sung vào price list ngay?

## Reading Flow

1. **KPI bar** — Doanh thu US, tổng số đơn, AOV, số khách hàng (so sánh kỳ trước).
2. **Order Status / Fulfillment Status** — Phân bổ trạng thái đơn. Có đơn stuck không?
3. **Revenue & Orders Trend** — Combo chart: doanh thu (bar) + số đơn (line) theo ngày. Phát hiện ngày bất thường.
4. **US Orders List** — Danh sách chi tiết từng đơn: click mã đơn để xem detail view.
5. **Cảnh báo thiếu giá** — Số đơn có SKU chưa có giá + bảng SKU cần bổ sung vào price list.

## Data Lineage

- **Primary:** `fact_us_shipment_economics` — P&L và revenue per US order (total_us_revenue_excl_vat, has_unpriced_sku)
- **Supporting:** `fact_orders` (status, fulfillment_status, payment_status), `dim_channels` (channel_name = 'US'), `dim_customers` (full_name)
- **Price alerts:** `int_us_shipment_line_prices` (is_price_missing per SKU)
- **Scope:** `channel_name = 'US'` — đơn export/arrangement, không phải sales thường; excluded from all revenue dashboards
- **Caveat:** Dùng channel filter (`channel_name = 'US'`), không dùng `customer_type = 'CROSSBORDER'`

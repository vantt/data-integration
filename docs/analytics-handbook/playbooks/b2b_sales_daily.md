# Playbook: B2B Daily Sales

## Overview

- **Audience:** B2B Account Manager
- **Goal:** Daily monitoring of B2B sales performance (WHOLESALE, PARTNER) — doanh thu hôm nay, AOV, top accounts, phân bổ theo loại khách và kênh.
- **Collection:** `Operations > B2B Operations`
- **Cadence:** Daily (today vs yesterday)
- **Blueprint:** [blueprints/b2b_sales_daily.md](../blueprints/b2b_sales_daily.md)

## Key Questions

- Doanh thu B2B hôm nay đạt bao nhiêu so với hôm qua?
- AOV hôm nay là bao nhiêu? Có bất thường so với hôm qua không?
- WHOLESALE và PARTNER đóng góp bao nhiêu vào doanh thu hôm nay?
- Kênh nào đang tạo ra nhiều doanh thu B2B nhất?
- Những khách hàng nào đặt nhiều/lớn nhất hôm nay?

## Reading Flow

1. **Tab: Tong quan** — Nhìn 4 scalar đầu (Net Revenue, Total Orders, AOV, Khach B2B) để nắm pulse ngày hôm nay. So sánh với hôm qua ngay trên từng card.
2. **Phan bo theo loai khach va kenh** — Xem bar chart WHOLESALE vs PARTNER để xác định nhóm nào dẫn dắt doanh thu. Kiểm tra row chart kênh để thấy khách B2B đặt hàng qua đâu.
3. **Top Customers** — Xem bảng top 10 khách theo doanh thu. Khách quen không xuất hiện = tín hiệu cần follow-up.
4. **Tab: Chi tiet don hang** — Xem toàn bộ danh sách đơn B2B hôm nay với trạng thái thanh toán, chiết khấu. Click mã đơn để mở chi tiết trên detailview.

## Data Lineage

- **Core Model:** `fact_orders` — net_revenue, discount_amount, status, payment_status, ordered_at
- **Dimensions:** `dim_customers` — full_name, customer_type (WHOLESALE / PARTNER); `dim_channels` — channel_name
- **Scope:** `scope_b2b` — chỉ bao gồm WHOLESALE và PARTNER orders; retail excluded
- **Filter:** `is_active_order` loại trừ đơn hủy khi tính doanh thu

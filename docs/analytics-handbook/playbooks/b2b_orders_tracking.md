# Playbook: B2B Orders Tracking

## Overview

- **Audience:** B2B Account Manager
- **Goal:** Monitor payment status and fulfillment progress for WHOLESALE and PARTNER orders — công nợ, tuổi nợ, giao hàng pending.
- **Tool:** metabase
- **Collection:** `Operations > B2B Operations`
- **Cadence:** Rolling 30 days (default), adjustable via date filter
- **Blueprint:** [blueprints/b2b_orders_tracking.md](../blueprints/metabase/b2b_orders_tracking.md)

## Key Questions

- Tổng công nợ B2B hiện tại là bao nhiêu? Bao nhiêu đơn chưa thanh toán?
- Những đơn nào đã quá 30 ngày chưa thu được tiền?
- Phân bổ công nợ giữa WHOLESALE và PARTNER như thế nào?
- Khách hàng nào đang chiếm tỷ trọng công nợ lớn nhất?
- Có bao nhiêu đơn đang chờ giao hàng hoặc đang vận chuyển?

## Reading Flow

1. **Tab: Cong no** — Bắt đầu với 3 scalar đầu (Cong no, Don chua TT, Thanh toan mot phan) để nắm tổng quan nhanh. Kiểm tra Ngay trung binh: nếu > 14 ngày thì cần follow-up.
2. **Aging Analysis** — Xem biểu đồ cột tuổi nợ: tập trung vào bucket "> 30 ngay" — đây là rủi ro mất tiền cao nhất. So sánh Wholesale vs Partner trên pie chart để xác định nhóm cần ưu tiên.
3. **Top Customers** — Xem bảng top 10 khách công nợ lớn nhất, cột "Don cu nhat" cho biết đơn nào lâu nhất chưa thanh toán.
4. **Tab: Giao hang** — Kiểm tra Cho giao hang và Dang giao. Xem bảng danh sách đơn pending để lên lịch giao và liên hệ khách.

## Data Lineage

- **Core Model:** `fact_orders` — payment_status, fulfillment_status, net_revenue, ordered_at
- **Dimensions:** `dim_customers` — full_name, customer_type (WHOLESALE / PARTNER)
- **Scope:** `scope_b2b` — chỉ bao gồm WHOLESALE và PARTNER orders; retail excluded
- **Filter:** `payment_status IN ('UNPAID', 'PARTIAL')` cho công nợ; `is_active_order` loại trừ đơn hủy

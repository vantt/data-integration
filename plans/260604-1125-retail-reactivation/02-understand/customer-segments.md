---
title: "Phân khúc khách lẻ — tệp 1.082 & tài sản ẩn US gift"
stage: 2
status: resolved
source: ../archive/2026-06-04-original-sales-slowdown-playbook.md
---

# Phân khúc khách lẻ — tệp 1.082 & tài sản ẩn US gift

## 1.3 Trọng tâm đã chọn & tài sản ẩn

Chủ quyết định tập trung **khách lẻ (B2C)** ở giai đoạn này.

Tài sản ẩn quan trọng: **~824 người nhận quà từ Mỹ** (814 có SĐT Việt, contactable) là nhóm
đã cầm & dùng sản phẩm Fine Japan nhưng chưa từng tự trả tiền — tiềm năng chuyển đổi sang mua
nội địa nếu tiếp cận đúng thông điệp (xem mục 4 và §6 trong nguồn).

---

## 4. Tệp khách lẻ liên hệ được — phân khúc & rào cản

### 4.1 Phân khúc tệp 1.082 khách có SĐT

| Phân khúc | Số khách | LTV (tr) | Đặc điểm | Cách tiếp cận |
|---|---|---|---|---|
| **Active** (≤30 ngày) | 32 | 2.973 | AOV cao 2.661K, đang khỏe | Giữ ấm, upsell |
| **At Risk** (31–90 ngày) | 64 | 897 | Đang nguội, cứu kịp | High-touch |
| **Churned** (>90 ngày) | 986 | 2.299 | 91% tệp, TB nguội ~3.4 năm | Tách nóng/lạnh |
| — OVERDUE (lặp lại quá hạn) | 166 | 2.199 | Từng mua đều (~82 ngày/lần) rồi biến mất | Win-back ưu tiên |
| — one-timer | 844 | 630 | Mua đúng 1 lần, đa số rất cũ | Bulk + second-order |

**Phân bổ công sức:** ~120 khách giá-trị/đúng-hạn (action queue, **~1.3 tỷ value at stake**)
→ high-touch (gọi/Zalo cá nhân); ~700+ khách nguội → bulk low-touch (Zalo blast).
Đừng gọi tay khách nguội 3 năm.

> Brand chủ lực **Fine Japan (739 khách)** — collagen/supplement là hàng tiêu dùng tái mua tự nhiên.
> Đòn bẩy mạnh nhất: nhắc **đúng lúc hết hàng** theo chu kỳ cá nhân (`avg_days_between_orders`).

### 4.2 Tín hiệu mua tiếp (`next_purchase_signal`)

Bảng `mart_customer_action_queue` đã có cột này; kết hợp `predicted_next_purchase_date` để hẹn giờ
tiếp cận cá nhân, không blast đại trà.

### 4.3 Retention theo kênh acquisition

| Acquired via | Khách | % mua lại | Đơn/đời | Liên hệ được |
|---|---|---|---|---|
| Retail (offline) | 26 | **38.5%** | 3.96 | 81% |
| Web | 24 | **33.3%** | 3.79 | 96% |
| **Shopee** | 246 | 22.4% | 1.47 | **chỉ 10%** |
| Social | 59 | 11.9% | 1.20 | 98% |

Kênh nhà giữ chân tốt hơn Shopee **2–3×**.

### 4.4 Rào cản cấu trúc — Shopee "thuê" không "sở hữu"

246 khách Shopee, chỉ 54 mua lần 2 — **52/54 lại trên Shopee, chỉ 2 chuyển kênh nhà**. Và
**chỉ 10% có SĐT** ⇒ toàn bộ cỗ máy CSKH/`action_queue` **vô dụng với 90% tệp lẻ lớn nhất**.

> **LƯU Ý QUAN TRỌNG:** 823/1.082 ≈ 76% tệp "khách lẻ liên hệ được" là **người nhận quà US** —
> nhóm này chưa từng tự trả tiền mua, cần thông điệp khác hoàn toàn so với win-back thông thường.

> **Data cần build** → [04-opportunities/data-backlog](../04-opportunities/data-backlog.md).

---
title: "US Gift Recipients — Luồng người nhận quà từ Mỹ tại Việt Nam"
stage: 5
status: pending
source: "../reference/sales-slowdown-diagnosis-and-action-playbook.md — §6"
---

# US Gift Recipients — Luồng người nhận quà từ Mỹ tại Việt Nam

> Trích nguyên văn §6 từ [`../reference/sales-slowdown-diagnosis-and-action-playbook.md`](../reference/sales-slowdown-diagnosis-and-action-playbook.md).
> Lộ trình triển khai (P4 test): xem [`b2c-reactivation-phases.md`](./b2c-reactivation-phases.md).
> Perspectives trust/JTBD: xem [`../perspectives/`](../perspectives/).

---

## 6. Đơn US — mỏ người nhận tại Việt Nam

### 6.1 Bản chất luồng kiều bào

Luồng **người MUA ở Mỹ, người NHẬN ở VN**. Trong data, `customer_key` của đơn US = người nhận VN.
Địa chỉ ship & bill đều là địa chỉ VN thật (Đà Nẵng, TP HCM, Đồng Nai...).

- **824 người nhận VN**; 823 `customer_type=RETAIL`; **814 có SĐT Việt (0/+84), 0 SĐT Mỹ → contactable**.
- Họ đã cầm & dùng sản phẩm (chủ yếu Fine Japan) nhưng **chưa bao giờ tự trả tiền** (người nhà ở Mỹ trả).
- Hầu như **không mua nội địa**: 816 khách/1.188 đơn CrossBorder; chỉ ~10–15 người từng mua qua kênh VN
  (Web 3, Retail 3, Social 3, Direct 1).
- **823 người này ≈ 76% của tệp "1.082 khách lẻ liên hệ được"** → tệp đó thực chất phần lớn là
  người nhận quà US, không phải khách đã từng chủ động mua.

### 6.2 Phân tầng độ ấm (theo recency)

| Nhóm | Recency | Số khách | Ghi chú |
|---|---|---|---|
| Nóng nhất | 0–90 ngày | **51** | Đang hoặc vừa nhận hàng gần đây |
| Ấm | 91–365 ngày | 129 | Trong vòng 1 năm |
| Nguội | 1–2 năm | 55 | |
| Rất nguội | >2 năm | **589** | Yield thấp, bulk cuối cùng |

→ **~180 khách trong vòng 1 năm** là tệp ấm đáng làm. 51 nóng là điểm test đầu tiên.

### 6.3 Thông điệp tiếp cận

**Bước 0 (trước khi outbound call): Audit hộp hàng CrossBorder**
Kiểm tra: hộp có card, QR, hướng dẫn dùng không? Nếu không → người nhận dùng sản phẩm mà không có
hành trình → conversion thấp là hợp lý, không phải do thiếu outbound calling.
**Nếu không có gì trong hộp → đây là fix ưu tiên trước khi test 51 khách nóng.**

**Script outbound (product-experience first):**
> *"Chào anh/chị [tên], anh/chị vừa nhận [Fine Japan] do người nhà gửi từ Mỹ đúng không ạ?
> Bên em là nhà phân phối chính hãng tại VN. Em hỏi thăm: anh/chị dùng có thấy gì chưa ạ?"*
→ Nếu **thấy hiệu quả / thích**: *"Vậy thì đặt trực tiếp bên em tiện hơn nhiều — giao tận nơi,
   giá nội địa, khỏi chờ gửi từ Mỹ. Tuần này em có ưu đãi [X] cho lần đầu đặt nội địa."*
→ Nếu **chưa thấy gì / chưa dùng đủ**: tư vấn cách dùng đúng → tạo lý do thật để reorder khi thấy kết quả.
→ Nếu **không biết đây là Fine Japan / nhận mà không hay**: ghi lại, không ép, đây là nhóm yield thấp.

Góc bonus: (1) re-gift/giới thiệu cho người quen; (2) kéo người mua ở Mỹ đặt trực tiếp từ VN — phụ, thứ yếu.

### 6.4 Rủi ro và cảnh báo (TEST chưa kiểm chứng)

| Rủi ro | Mô tả |
|---|---|
| Chưa từng trả tiền | Không biết giá, không có thói quen mua nội địa |
| Bối cảnh quà biếu | Người nhận có thể lớn tuổi, không rành online |
| Tế nhị/quyền riêng tư | Gọi lạnh cho người chưa từng là khách trực tiếp |
| 589 khách >2 năm | Yield rất thấp — bulk cuối cùng, không ưu tiên |

### 6.5 Khuyến nghị triển khai

1. **TEST nhỏ: 51 khách nóng (0–90 ngày)** — đo phản hồi & tỷ lệ chuyển đổi sang mua nội địa.
2. Nếu ≥10% mua nội địa → mở rộng 180 ấm → rồi bulk 589 nguội.
3. **Thêm cờ `is_us_gift_recipient`** vào `dim_customers` để `mart_customer_action_queue` tách
   luồng này riêng (thông điệp khác, không dùng win-back thông thường).

---
title: "Câu hỏi chưa giải đáp — tổng hợp"
stage: 2
status: open
source: ../reference/sales-slowdown-diagnosis-and-action-playbook.md
---

# Câu hỏi chưa giải đáp — tổng hợp

> Nguồn gốc: §9 (7 câu hỏi gốc) + §0.5.2 (3 câu quyết định chiến lược).
> Đánh dấu OPEN/RESOLVED. Cập nhật khi có câu trả lời — ghi nguồn & ngày.

---

## Từ §9 — Câu hỏi chưa giải đáp (nguyên văn)

**Q1** — `OPEN`
> "6.025 khách lẻ 'New/Unknown' (LTV=0) trong `dim_customers` là gì?
> Lead/đăng ký chưa mua, hay đơn COD hủy? Cần xác minh trước khi coi là tệp reactivation."

---

**Q2** — `OPEN`
> "Ế" = doanh thu, **dòng tiền (cashflow)**, hay **margin**? (điều tra B2B cho thấy KHÔNG phải mất đơn — xem [b2b-collapse-root-cause](./b2b-collapse-root-cause.md)) — cần xác nhận góc nhìn để chọn đúng KPI."

---

**Q3** — `OPEN`
> "Nhóm wholesale ẩn (`negotiated_deep`) chiếm bao nhiêu % doanh thu 2023–2025?
> (cần chạy thêm)."

---

**Q4** — `OPEN`
> "Có ngân sách/nhân sự CSKH để **chạy call-list hằng ngày** không?
> Nếu không, ưu tiên tự động hóa nhắc qua Zalo/SMS theo `predicted_next_purchase_date`."

---

**Q5** — `OPEN`
> "**Người nhận quà US** (mục 6): họ có biết sản phẩm mình nhận là Fine Japan /
> nhà phân phối tại VN không? Người gửi (ở Mỹ) có thể là 'người giới thiệu tự nhiên' không?"

---

**Q6** — `OPEN`
> "Tỷ lệ chuyển đổi US gift → mua nội địa thực sự ra sao?
> (chưa có data — cần test 51 khách nóng trước)."

---

**Q7** — `OPEN`
> "Bối cảnh đơn US: người nhận thường được báo trước hay nhận bất ngờ?
> (ảnh hưởng cách cold-contact)."

---

**Q8** — `OPEN` *(thêm 2026-06-09)*
> "Biên lợi nhuận B2B thật: nhiều đơn `net_revenue=0` dù gross cao (deep-discount) — margin thực bao nhiêu?"

---

**Q9** — `OPEN` *(thêm 2026-06-09)*
> "54tr COD ≤Feb chưa thu (đuôi AR) — tỷ lệ thu hồi thực tế ra sao? Đây có phải nguyên nhân chính của 'ế' cảm nhận không?" → xem [cashflow-collection-ar.md](./cashflow-collection-ar.md).

---

**Q10** — `OPEN` *(thêm 2026-06-09)*
> **Data:** vì sao `fact_payments` rỗng? `payment_status` có được cập nhật khi khách trả không? (CUZN00015 'nợ' 79 đơn từ 2022 vẫn Active VIP — nợ thật hay không ghi nhận thanh toán?)

---

> **Câu hỏi quyết định chiến lược** → [03-evaluate/open-decisions](../03-evaluate/open-decisions.md).

---

## Hướng dẫn cập nhật

Khi một câu được trả lời: đổi `OPEN` → `RESOLVED`, thêm dòng:
```
**Trả lời:** [nội dung ngắn gọn]
**Nguồn/ngày:** [ai trả lời / khi nào]
```

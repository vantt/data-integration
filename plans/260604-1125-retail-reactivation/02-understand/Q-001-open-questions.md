---
title: "Q-001 - Open Questions"
stage: 2
status: open
source: ../archive/2026-06-04-original-sales-slowdown-playbook.md
---

# Q-001 - Open Questions

**Registry:** [Q-001](../REGISTRY.md#q-001)

> Nguồn gốc: §9 (7 câu hỏi gốc) + §0.5.2 (3 câu quyết định chiến lược).
> Đánh dấu OPEN/RESOLVED. Cập nhật khi có câu trả lời — ghi nguồn & ngày.

---

## Từ §9 — Câu hỏi chưa giải đáp (nguyên văn)

**Q1** — `OPEN`
> "6.025 khách lẻ 'New/Unknown' (LTV=0) trong `dim_customers` là gì?
> Lead/đăng ký chưa mua, hay đơn COD hủy? Cần xác minh trước khi coi là tệp reactivation."

---

**Q2** — `OPEN`
> "Ế" = doanh thu, **dòng tiền (cashflow)**, hay **margin**? (điều tra B2B cho thấy KHÔNG phải mất đơn — xem [b2b-collapse-root-cause](./FIND-004-b2b-collapse-root-cause.md) — cần xác nhận góc nhìn để chọn đúng KPI."

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
> "54tr COD ≤Feb chưa thu (đuôi AR) — tỷ lệ thu hồi thực tế ra sao? Đây có phải nguyên nhân chính của 'ế' cảm nhận không?" → xem [cashflow-collection-ar.md](./INV-001-cashflow-collection-ar.md).

---

**Q10** — `OPEN` *(thêm 2026-06-09)*
> **Data:** vì sao `fact_payments` rỗng? `payment_status` có được cập nhật khi khách trả không? (CUZN00015 'nợ' 79 đơn từ 2022 vẫn Active VIP — nợ thật hay không ghi nhận thanh toán?)

---

---

## Từ fresh-scan 2026-06-13 (mới)

> Nguồn: [fresh-scan-260613-data-market.md](./FIND-007-fresh-scan-data-market.md).

**Q11** — `OPEN` ⭐
> Vì sao **base đơn lẻ co −55%** từ đỉnh 2024 (479-539 đơn/quý → ~200/quý)? Event/promo/kênh nào tạo đỉnh 2024 rồi tắt? (thiếu acquisition-source log) — có thể là gốc rễ thật của "ế".

**Q12** — `OPEN`
> 96 đơn UNPAID 2026 (605tr) = credit-term B2B bình thường hay bad-debt? (thiếu due_date để phân biệt).

**Q13** — `RESOLVED` (2026-06-13)
> **UV Care Plus** là loss-leader hay rò rỉ thuần?
> **Trả lời:** rò rỉ thuần — 409 khách vào, 42 quay lại, 72% repeat lại mua UV Care, ~0 bắc cầu sang cordyceps/collagen/tim mạch. Ngõ cụt da liễu tự-đóng, KHÔNG nuôi phễu hero → cắt acquisition an toàn.
> **Nguồn:** product cross-sell scan, [fresh-scan §B+](./FIND-007-fresh-scan-data-market.md).

**Q17** — `OPEN` ⭐ *(2026-06-13)*
> Vì sao **Khớp/Xương sụn entry chỉ 15% repeat** dù khớp là nhu cầu hero người già? efficacy thấp / quà 1-lần / sai SKU? → đưa vào VOC.

**Q18** — `OPEN` *(2026-06-13)*
> Brand ngoài Fine Japan (Jpanwell repeat 0%, Kirkland 8.7%) — dừng nhập hay chỉ noise volume nhỏ?

**Q19** — `OPEN` ⭐ *(2026-06-13, từ audit kênh nhà §I)*
> Vì sao 2 site D2C của mình (finejapanvietnam 15 SKU + jpcshop 8 SKU) chỉ trưng lõi mono-brand Fine Japan, lệch giá nhau 38%, đẩy giảm giá sâu? Ai quản giá/catalog từng site? Phân vai 2 site là gì? → cần dẹp xung đột kênh + nạp đủ catalog (O8/O9).

**Q14** — `OPEN`
> Fine Japan có mặt trên **nhà thuốc chuỗi (Long Châu/An Khang)** không? — kênh niềm tin #1 cho TPCN người già; nếu vắng = gap kênh lớn. Cần verify thực địa.

**Q15** — `OPEN` ⭐
> **% đơn "con-mua-cho-bố-mẹ"** (buyer≠user) là bao nhiêu? Nếu >40% → thiết kế lại toàn bộ message + retention theo người-mua (con 25-45), không theo người-dùng-cuối.

**Q16** — `OPEN`
> CAC theo kênh không có trong data → chưa tính được LTV/CAC thật. Zalo LTV gấp 5.3× Shopee nhưng CAC Zalo bao nhiêu? (cần để quyết dồn ngân sách acquisition).

---

> **Câu hỏi quyết định chiến lược** → [DEC-001 decision register](../03-evaluate/DEC-001-decision-register.md#open-blocking-decisions).

---

## Hướng dẫn cập nhật

Khi một câu được trả lời: đổi `OPEN` → `RESOLVED`, thêm dòng:
```
**Trả lời:** [nội dung ngắn gọn]
**Nguồn/ngày:** [ai trả lời / khi nào]
```

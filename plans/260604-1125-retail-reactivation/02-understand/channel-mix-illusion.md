---
title: "Ảo giác kênh — doanh thu lõi/B2B đang sụp, bị marketplace che"
stage: 2
status: resolved
source: ../archive/2026-06-04-original-sales-slowdown-playbook.md
---

# Ảo giác kênh — cơn đau cấp tính

## 1.1 Doanh thu lõi/B2B sụp nhưng bị marketplace che

"Số đơn 2026 tốt" là **ảo giác** do trộn ba thứ khác nhau:

| Nguồn (2026) | Đơn | Bản chất |
|---|---|---|
| **Shopee** (Marketplace) | 319 | Kênh MỚI (0 đơn nửa đầu 2025). AOV chỉ 1.48M, rơi xuống 939K (T5). Đơn nhỏ lẻ tự động |
| **CrossBorder/US** | 78 | Doanh thu thật chỉ T1 (129M); T2–T5 = **0đ** → bản ghi giao vận, không phải bán hàng |
| **B2B + Social + Web** | ~130 | Việc kinh doanh **lõi** — đang teo nhanh |

**Nhu cầu lõi thật** (bỏ Shopee + CrossBorder-0đ): T1 **326M → T5 chỉ 14M** (sụp ~95%).
Riêng **B2B**: T1 **42 đơn/278M → T5 2 đơn/2M**. Nhóm sỉ ~5–10 khách/tháng gánh cả công ty
(rủi ro cô đặc) — họ ngừng mua là sụp ngay. **Đây chính là "ế" mà chủ cảm nhận.**

> Phải tách **kênh lõi vs marketplace** và **completed vs OPEN** thì mới thấy đúng.

---

## 2.1 Xu hướng theo năm — tăng trưởng giả nhờ wholesale, rồi sụp

| Năm | Đơn hợp lệ | Doanh thu (tr.đ) | Số khách | Nhận định |
|---|---|---|---|---|
| 2021 | 556 | 255 | 411 | Nền bán lẻ nhỏ, AOV thấp |
| 2022 | 623 | 1.879 | 397 | Doanh thu nhảy 7×, AOV tăng mạnh |
| 2023 | 456 | 2.865 | **128** | **Khách sụt 397→128 nhưng DT đỉnh** → lệ thuộc sỉ/B2B |
| 2024 | 398 | 1.916 | 120 | Tiếp tục cô đặc vào ít khách lớn |
| 2025 | 387 | **1.095** | 196 | **DT thấp nhất kể từ 2021** — "ế" cảm nhận từ đây |
| 2026* | 656 | 2.394 | 367 | *5 tháng. Bùng nổ đơn & khách mới |

**Rủi ro cô đặc:** giai đoạn 2023–2024 doanh thu được kéo bởi ~120–128 khách (AOV 5–6M ⇒ sỉ ẩn).
Khi nhóm này giảm mua → 2025 sụp. Doanh thu phụ thuộc số ít khách lớn, không được nâng đỡ bởi tệp
lẻ rộng.

> Taxonomy `discount_type = negotiated_deep` (giảm ≥40%) đang đánh dấu **sỉ trá hình** lẫn trong
> tệp RETAIL. Cần tách & chính thức hóa kênh sỉ.

---

## 2.2 Xu hướng theo tháng — bóc tách kênh (tại sao "số đơn tốt" là ảo giác)

**Bảng tổng tháng (all channels):**

| Tháng | Đơn | DT (tr) | Người mua | Mới | Quay lại | AOV (ng.đ) |
|---|---|---|---|---|---|---|
| 2025-04 | 11 | 27 | 8 | 1 | 7 | 2.474 |
| 2025-05 | 8 | 20 | 7 | 3 | 4 | 2.443 | ← đáy gần-chết |
| 2025-07 | 65 | 76 | 53 | 34 | 19 | 1.163 | ← phục hồi |
| 2025-12 | 56 | 107 | 41 | 19 | 22 | 1.910 |
| 2026-01 | 144 | 428 | 103 | **77** | 26 | 2.973 |
| 2026-03 | 151 | 382 | 108 | **70** | 38 | 2.527 |
| 2026-05 | 135 | 306 | 98 | **71** | 27 | 2.264 |

Mỗi tháng 2026 có ~70 khách mới nhưng chỉ ~26–42 quay lại. Acquisition đang gánh toàn bộ;
retention gần bằng 0 hiệu lực.

**Bóc tách kênh 2026 (completed):**

| channel_format | platform | Đơn | DT (tr) | AOV (ng.đ) | Ghi chú |
|---|---|---|---|---|---|
| Marketplace | **Shopee** | 319 | 471 | 1.478 → **939 (T5)** | Kênh mới, đơn nhỏ, đang co |
| CrossBorder | US | 78 | 129 (chỉ T1) | T2–T5 = **0** | Bản ghi giao vận, không phải sales |
| **B2B** | — | 85↓ | — | 6.000–10.000 | **Cỗ máy thật — đang chết** |
| Social/Web | — | ~40 | — | 3.000–4.000 | Nhỏ |

**B2B theo tháng (completed):** T1 42đơn/278tr → T2 15/137 → T3 16/101 → T4 10/103 → **T5 2/2**.

> ⚠️ **HIỆU CHỈNH 2026-06-09:** con số completed-only này gây hiểu lầm — B2B thực tế KHÔNG sụp (cầu theo tháng-đặt-đơn 2026 = 2–3× 2025). Xem [b2b-collapse-root-cause](./b2b-collapse-root-cause.md) (resolved). Giữ số gốc để đối chiếu.

**Nhu cầu lõi** (loại Marketplace + CrossBorder-0đ + System): T1 **326tr** → T3 261 → T4 209 →
**T5 14tr**. Lõi sụp ~95%; số tổng được đỡ bởi Shopee nhỏ lẻ + giao vận 0đ.

> **Caveat cần kiểm chứng:** (1) **Mùa Tết** — T1 cao có thể do đại lý gom hàng trước Tết (~17/2/2026),
> chững sau Tết bình thường; nhưng tụt còn 2 đơn B2B thì dốc hơn mức thường. (2) **Đơn OPEN** —
> T5–T6 còn đơn chưa completed ⇒ tháng gần nhất có thể bị đếm thiếu; nhưng đà giảm B2B đã rõ từ T1→T4.

---
title: "Điều tra: Cashflow & công nợ COD — nghi phạm thật của 'ế'"
stage: 2
status: open
blocker: "fact_payments rỗng (không đo được tiền thực thu) + cần chủ/kế toán xác nhận nợ thật"
source: spawned from b2b-collapse-root-cause.md
lens: A3
investigated_at: 2026-06-09
---

# Điều tra: Cashflow & công nợ COD — nghi phạm thật của "ế"

**Trạng thái:** 🟠 OPEN — có **findings mạnh** nhưng **BLOCKED** trên 1 ngã rẽ chỉ chủ/kế toán + data thanh toán mới giải được.

---

## Kết luận tạm thời (2026-06-09) — TL;DR

> **"Ế" nhiều khả năng là chuyện TIỀN/CÔNG NỢ, không phải doanh số** — nhưng **dữ liệu để chốt đang thiếu**.
> Suy từ cờ trạng thái: **~2.708 tỷ AR B2B** (đã giao, chưa đánh dấu PAID), **84% quá 90 ngày**, **cô đặc ~77% vào 2 khách VIP**.
> **NHƯNG `fact_payments` rỗng** → không phân biệt được đây là **nợ thật** hay **pipeline thanh toán không cập nhật**.

**Ngã rẽ phải hỏi chủ/kế toán (30 phút) trước khi hành động:**
- CUZN00015 có thật sự nợ **1.681 tỷ** (79 đơn từ 2022 chưa thu) không? Hay đã thu mà hệ thống không ghi?

→ Đây mirror đúng pattern của [b2b-collapse](./b2b-collapse-root-cause.md): **data B2B có lỗ hổng hệ thống** (completed-only ở đó, payment-tracking ở đây). KHÔNG xây chương trình thu nợ trên data mềm.

---

## Findings định lượng (suy từ payment_status — xem caveat)

### 1. ⚠️ Caveat dữ liệu (quyết định độ tin cậy mọi số dưới)
- **`fact_payments` RỖNG** (0 bản ghi, `paid_on` NULL toàn bộ) → **không có bằng chứng tiền thực thu**.
- `total_collected` = **giá trị danh nghĩa VAT-inclusive** (≈ net × 1.0–1.08), KHÔNG phải tiền đã về.
- "AR" = đơn `payment_status ∈ (UNPAID, PARTIALLY_PAID)` & đã giao & không huỷ. **Nếu cờ payment_status không được cập nhật → AR bị thổi phồng.**

### 2. Quy mô AR (theo cờ trạng thái)
| Nhóm | Đơn | Outstanding (tỷ) |
|---|---|---|
| **Tổng AR** | 226 | **3.127** |
| **B2B** | 188 | **2.708** (86.6%) |
| Non-B2B | 38 | 0.419 |

### 3. Aging B2B — **84% quá 90 ngày** (báo động nếu là nợ thật)
| Tuổi | Đơn | Outstanding (tỷ) | % AR B2B |
|---|---|---|---|
| 0–30 ngày | 26 | 0.146 | 5.4% |
| 31–60 | 17 | 0.188 | 6.9% |
| 61–90 | 17 | 0.092 | 3.4% |
| **>90 ngày** | **128** | **2.283** | **84.3%** |

### 4. Cô đặc cực độ — 2 khách = 77% AR B2B
| customer_code | value_group | status | recency | đơn chưa thu | outstanding (tỷ) | đơn cũ nhất |
|---|---|---|---|---|---|---|
| **CUZN00015** | VIP | Active | 9 ngày | 79 | **1.681** | 2022-04-07 |
| **CUZN03970** | VIP | Active | 7 ngày | 40 | **0.401** | 2024-01-09 |
| (churned cũ ~5 khách) | — | Churned | >400 ngày | — | ~0.224 | 2022–2023 |

→ CUZN00015 vẫn **Active VIP đang mua tiếp** nhưng "nợ" 79 đơn từ 2022 → **rất khả nghi là data gap** (không ai bán 4 năm cho người nợ 1.68 tỷ); hoặc là **bán gối đầu/ký gửi** quy mô lớn.

### 5. Cơ chế trễ (đáng tin hơn — không phụ thuộc payment data)
- **Giao hàng KHÔNG phải vấn đề:** delivery lag B2B median **0.9 ngày**.
- **Nút thắt = sau giao (đóng đơn/xác nhận thu):** post-ship lag median **31 ngày** (P75 73d) = **97.3% tổng chu kỳ**. Retail chỉ 3 ngày.
- Chu kỳ hoàn tất B2B **dài ra +17% YoY** (2025 ~42d → 2026 ~49d median).

### 6. COD đang phình + lịch sử thu hồi
- **Tỷ trọng COD trong B2B tăng vọt:** Jan 4.5% → **May 100%** đơn B2B là COD. Phụ thuộc COD/gối đầu tăng nhanh.
- **Lịch sử thu hồi COD (2021–2024): 83–94% cuối cùng COMPLETED** → phần lớn COD *có* về (ủng hộ giả thuyết "timing" cho đơn mới).
- **Nhưng pre-2025 còn kẹt: 79 đơn / 1.894 tỷ** SHIPPED_COD 1–4 năm chưa đóng → **nợ khó đòi thật, không phải timing** (hoặc data gap).
- Cancel-after-ship 2025–2026 ≈ **0** (rủi ro mất hàng đã giao: thấp).

---

## Hai kịch bản (phải disambiguate bằng phỏng vấn + fix data)

| | Kịch bản A — NỢ THẬT | Kịch bản B — DATA GAP |
|---|---|---|
| Bản chất | Bán gối đầu/ký gửi; 2.7 tỷ thật sự đang treo, cô đặc 2 VIP | `payment_status`/`fact_payments` không được cập nhật → AR ảo |
| Bằng chứng ủng hộ | COD mix tăng tới 100%; đuôi 1–4 năm | fact_payments rỗng; VIP nợ 4 năm vẫn được bán tiếp (vô lý) |
| "Ế" giải thích | Tiền kẹt ở 2 khách → đúng là thiếu tiền mặt dù bán chạy | Không phải vấn đề tiền — chỉ là không nhìn thấy dòng tiền |
| Hành động | Đàm phán thu nợ CUZN00015/03970; siết hạn mức gối đầu | Fix pipeline thanh toán; rồi đo lại AR |

→ **Cả hai đều dẫn tới cùng 2 việc đầu tiên** (bên dưới).

---

## Hành động đề xuất (bất kể kịch bản nào)
1. **Hỏi chủ/kế toán (30 phút):** CUZN00015 & CUZN03970 thực tế còn nợ bao nhiêu? Chính sách gối đầu/ký gửi với 2 VIP này là gì? → phân định A vs B ngay.
2. **Fix data thanh toán:** vì sao `fact_payments` rỗng & `payment_status` có đáng tin không → [04-opportunities/data-backlog](../04-opportunities/data-backlog.md). Đây là **lỗ hổng đo lường nghiêm trọng** — chặn mọi phân tích cashflow/biên.
3. Sau khi phân định: nếu A → chương trình thu nợ + siết hạn mức (đòn bẩy: 2 khách vẫn Active); nếu B → đo lại rồi mới kết luận "ế".

---

## Hệ quả cho path
- **"Ế" gần như chắc KHÔNG phải mất cầu** (B2B + cashflow đều không phải mất bán) → củng cố [b2b-collapse](./b2b-collapse-root-cause.md): trọng tâm là **B2C retention (mạn tính)** + **dòng tiền/đo lường**.
- Mở lỗ hổng data mới (payment tracking) → [open-questions](./open-questions.md) + [data-backlog](../04-opportunities/data-backlog.md).
- Quyết định #1 ([open-decisions](../03-evaluate/open-decisions.md)): "ế cấp tính" có thể là **cash concentration** (2 VIP) — cần chủ xác nhận, KHÔNG phải lý do để đổ lực vào acquisition.

---

## Phụ lục — phương pháp & độ tin cậy
DuckDB trên parquet (snapshot 2026-06-09), B2B=`scope_b2b`, ICT. 3 luồng (AR aging · lag decomposition · COD recovery cohort).
**Độ tin cậy:** mục 5 (lag) ĐÁNG TIN (dùng timestamp giao/đóng đơn). Mục 2–4 (số AR) PHỤ THUỘC `payment_status` — mềm vì `fact_payments` rỗng. Mục 6 (recovery lịch sử) đáng tin tương đối (status transition).

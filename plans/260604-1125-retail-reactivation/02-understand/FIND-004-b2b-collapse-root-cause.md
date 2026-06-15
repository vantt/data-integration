---
title: "FIND-004 - B2B Collapse Root Cause"
stage: 2
status: resolved
source: ../archive/2026-06-04-original-sales-slowdown-playbook.md
lens: A3
related_lens: ../01-perspectives/PERS-001-first-principles-lenses.md
resolved_at: 2026-06-09
---

# FIND-004 - B2B Collapse Root Cause

**Registry:** [FIND-004](../REGISTRY.md#find-004)

**Trạng thái:** ✅ RESOLVED (định lượng) — giả thuyết gốc **BỊ BÁC BỎ**. Còn 1 thread định tính (phỏng vấn chủ) tách sang [open-questions](./Q-001-open-questions.md).

---

## Kết luận (2026-06-09) — TL;DR

> **B2B KHÔNG sụp đổ.** "Sụp 95% (T1 278tr → T5 2tr)" trong playbook là **artifact đo lường**, không phải khách bỏ.
> Theo *tháng đặt đơn*, B2B 2026 chạy **190–290tr/tháng — gấp 2–3× mức 2025**. Top khách sỉ VIP vẫn đang mua đều.

**3 nguyên nhân tạo ảo giác "sụp":**
1. **Đếm completed-only** trong khi B2B có **lag hoàn tất ~46–78 ngày** (median 1.100–1.875 giờ) → tháng gần đây hiện 0 completed dù đơn vẫn về.
2. **491tr đang ở trạng thái OPEN = SHIPPED_COD/UNPAID** (68 đơn, đã giao chờ thu COD) — doanh thu thật trong pipeline, không phải mất.
3. Playbook chốt số ngày 2026-06-04 khi T5–T6 chưa đóng kỳ.

**Giả thuyết gốc (5–10 khách sỉ ngừng mua) → SAI.** Top VIP sỉ vẫn Active, recency 0–19 ngày, đặt nhiều đơn tới tận May–Jun.

---

## Bằng chứng định lượng

### 1. Cầu B2B theo THÁNG ĐẶT ĐƠN (status ≠ CANCELLED/DRAFT) — tín hiệu cầu thật

| Tháng | Đơn | Khách | Doanh thu (tr, total_collected) | Còn OPEN |
|---|---|---|---|---|
| 2025 (dải) | 4–23 | 3–9 | **12–173** | — |
| 2026-01 | 42 | 9 | **290** | 2 |
| 2026-02 | 26 | 8 | 238 | 12 |
| 2026-03 | 33 | 10 | 168 | 18 |
| 2026-04 | 21 | 9 | 197 | 13 |
| 2026-05 | 28 | 6 | **191** | 28 |
| 2026-06* | 6 | 3 | 57 | 6 |

*9 ngày đầu. → 2026 cao gấp 2–3× 2025; May khỏe mạnh, KHÔNG sụp.

### 2. Ảo giác completed-only (cùng dữ liệu, lọc status='COMPLETED')

| Tháng | Completed đơn/tr | OPEN đơn/tr |
|---|---|---|
| 2026-04 | 8 / 74 | 13 / 122 |
| 2026-05 | **0 / —** | **28 / 191** |
| 2026-06 | 0 / — | 6 / 57 |

→ "0 completed" tháng gần = chưa đóng kỳ, KHÔNG phải hết khách. Lag hoàn tất B2B median ~46–78 ngày.

### 3. OPEN B2B = đơn đã giao chờ thu (không phải mất bán)

| fulfillment × payment | Đơn | tr |
|---|---|---|
| SHIPPED_COD / UNPAID | 68 | 491 |
| SHIPPED_PAID / PAID | 10 | 56 |
| SHIPPED_COD / PARTIALLY_PAID | 1 | 12 |

### 4. Top khách sỉ vẫn ACTIVE (không churn)

| customer_code | value_group | status | recency (ngày) | đơn OPEN May–Jun | tr |
|---|---|---|---|---|---|
| CUZN00055 | VIP | Active | **0** | 21 | 129 |
| CUZN03970 | VIP | Active | 7 | 15 | 168 |
| CUZN00133 | VIP | Active | 19 | 2 | 13 |
| CUZN00015 | VIP | Active | 9 | 4 | 12 |

### 5. Cancel rate thấp (COD không bị từ chối nhiều)
2026: Jan 4.5% · Feb 3.6% · Mar 2.9% · Apr 0% · May 0% (Jun 40% = nhiễu, 4/10 mẫu nhỏ). → OPEN/UNPAID sẽ chủ yếu thành PAID.

---

## Rủi ro thật phát hiện được (nhỏ hơn nhiều giả thuyết)

1. **Đuôi công nợ COD:** 4 đơn / **54tr** SHIPPED_COD/UNPAID từ ≤Feb vẫn chưa thu tới Jun → rủi ro thu hồi/ghi giảm. (31 đơn/189tr nhóm Mar–Apr: theo dõi; 33 đơn/248tr May–Jun: bình thường.)
2. **Lag hoàn tất ~46–78 ngày** làm mọi báo cáo completed-only hiểu sai tháng gần — lỗi đo lường hệ thống.
3. **Biên mỏng:** nhiều đơn B2B có `net_revenue=0` dù `gross` cao (deep-discount) → cần soi margin (thread mới).

---

## Hệ quả chiến lược (QUAN TRỌNG)

- **Tiền đề lens A1 "đám cháy thật là B2B" → phần lớn SAI.** B2B không phải đám cháy.
- Quyết định #1 ([DEC-001](../03-evaluate/DEC-001-decision-register.md#decision-1-focus)): "ế" cấp tính **không** đến từ mất cầu B2B → trọng tâm quay về **bệnh mạn tính B2C retention** (71.8% one-time — có thật) + **dòng tiền/AR**.
- **"Ế" mà chủ cảm nhận** nhiều khả năng là **CASHFLOW** (491tr đã giao chờ thu COD + lag 46–78 ngày = "hàng đi mà tiền chưa về") hoặc **margin** — KHÔNG phải mất đơn. → spawn [cashflow-collection-ar](./INV-001-cashflow-collection-ar.md).

---

## Thread còn mở (chuyển tiếp)

- **Định tính:** vẫn nên hỏi chủ "Q1–Q2 2025 cảm nhận ế từ đâu?" — nhưng đặt lại câu hỏi: *cảm giác ế là doanh thu, dòng tiền, hay margin?* → [open-questions](./Q-001-open-questions.md).
- **Cashflow/AR:** → [cashflow-collection-ar](./INV-001-cashflow-collection-ar.md) (OPEN).
- **Margin erosion** (net=0 deep-discount): → [open-questions](./Q-001-open-questions.md) (thêm câu hỏi).

---

## Phụ lục — query đã chạy
DuckDB (python, read parquet trực tiếp, `SET TimeZone='Asia/Ho_Chi_Minh'`), nguồn `fact_orders_*.parquet` (snapshot 2026-06-09), B2B = `scope_b2b=true`. Đếm theo `date_key` (ICT). Doanh thu = `total_collected` (khớp playbook: T1 completed 277tr ≈ "278tr"). 4 query: monthly completed-vs-open · top khách 2026 · OPEN fulfillment×payment + aging · cầu theo tháng đặt đơn + cancel rate.

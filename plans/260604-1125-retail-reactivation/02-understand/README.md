---
title: "02 · Understand — Khám phá & điều tra"
stage: 2
status: living
---

# 02 · Understand — Khám phá & điều tra

> **Luồng:** ← [01-perspectives](../01-perspectives/) · → [03-evaluate](../03-evaluate/) (đánh giá findings)

Mục đích: hiểu vấn đề bằng số thật — bóc tách kênh, đo retention, phân khúc khách. Song song điều tra những gì chưa rõ nguyên nhân.

---

## Đã chốt (resolved)

| File | Nội dung |
|---|---|
| [channel-mix-illusion.md](channel-mix-illusion.md) | Marketplace che lõi: B2B completed-only trông sụp ~95% (T1→T5), Shopee tạo ảo giác tăng trưởng; xu hướng năm + tháng có số cụ thể ⚠️ xem hiệu chỉnh bên trong |
| [retention-leak.md](retention-leak.md) | M1 repeat chỉ 3–17% (benchmark 30–50%+); waterfall point-in-time & SQL; model cũ sai 9× |
| [customer-segments.md](customer-segments.md) | Tệp 1.082 khách lẻ: phân khúc Active/At-Risk/Churned, tín hiệu mua tiếp, rào cản Shopee "thuê không sở hữu", tài sản ẩn US gift |
| [b2b-collapse-root-cause.md](b2b-collapse-root-cause.md) | ✅ **RESOLVED 2026-06-09:** B2B KHÔNG sụp — artifact completed-only + COD lag (~46–78 ngày) + 491tr OPEN. Cầu 2026 = 2–3× 2025; top VIP vẫn active. |
| [product-performance-assessment.md](product-performance-assessment.md) | ✅ data product đủ, KHÔNG cần pipeline lớn; reframe: portfolio sức khỏe người lớn tuổi; retention theo sản phẩm (Cordyceps dính, Fucoidan bẫy volume) |

---

## Đang điều tra (open)

| File | Giả thuyết đang kiểm |
|---|---|
| [cashflow-collection-ar.md](cashflow-collection-ar.md) | Nghi phạm thật của "ế" — AR/COD 54tr ≤Feb chưa thu; dòng tiền thực vs doanh thu kế toán. 🟠 findings mạnh nhưng BLOCKED (fact_payments rỗng + cần hỏi chủ); ~2.7 tỷ AR B2B cô đặc 2 VIP |
| [demand-migration-recon.md](demand-migration-recon.md) | Cầu dịch sang TikTok Shop/livestream thay vì mất hoàn toàn |
| [open-questions.md](open-questions.md) | 9 câu hỏi dữ liệu/vận hành còn OPEN (Q1–Q9; Q8–Q9 thêm 2026-06-09) |
| [voc-customer-interviews.md](voc-customer-interviews.md) | ⭐ **Đòn bẩy #1** — VOC: tại sao 72% one-timer không quay lại? Phỏng vấn 15 one-time + 10 repeater (NGOÀI hệ thống, owner/CSKH làm tuần này) |
| [unboxing-experience-audit.md](unboxing-experience-audit.md) | Audit unboxing & follow-up sau mua: hộp lẻ có card/QR/hướng dẫn không? So sánh với TikTok Shop/spa (mystery shopping, NGOÀI hệ thống) |

---

## Mở điều tra mới

Tạo file mới theo template dưới, `status: open`; khi có kết luận → đổi `status: resolved`.

```markdown
---
title: "Điều tra: <tên giả thuyết>"
stage: 2
status: open
source: ../reference/sales-slowdown-diagnosis-and-action-playbook.md
---

## Giả thuyết

## Câu hỏi cần trả lời

## Cách điều tra

## Bằng chứng đã có

## Kết luận
```

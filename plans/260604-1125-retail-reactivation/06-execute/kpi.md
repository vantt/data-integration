---
title: "KPI Đo lường — Stage 6 Execute"
stage: 6
status: tracking
source: archive/2026-06-04-original-sales-slowdown-playbook.md §8 + §5.5
---

# KPI Đo lường

## Bảng KPI "Hết ế" (lagging — từ §8)

| KPI | Hiện tại | Mục tiêu | Thời hạn |
|---|---|---|---|
| One-time rate | **72%** | < 60% | 2 quý |
| M1 repeat rate | **3–17%** | ≥ 25% | 2 quý |
| Returning buyers/tháng | ~30 | ≥ 60 | 2 quý |
| ACTIVE point-in-time (cuối tháng) | ~98 | tăng đều | theo dõi liên tục |
| Reactivation rate win-back | — | ≥ 15%/30 ngày | per campaign |
| US gift → nội địa conversion | 0 (test chưa có) | ≥ 10% → mở rộng | sau P4 test |

## Bảng KPI Leading (product-journey health — từ §8)

| KPI | Ý nghĩa | Đo thế nào |
|---|---|---|
| Day-7 engagement rate | % khách mới phản hồi Touch 1 hoặc Touch 2 | Ghi vào Sheet tracking |
| "Thấy hiệu quả" rate | % WIN_BACK/SECOND_ORDER call trả lời "có thấy hiệu quả" | Cột trong Sheet outcome |
| Dùng đúng cách Y/N | % khách được tư vấn lại sau khi nói "không thấy gì" | Cột trong Sheet |

> Nếu Day-7 engagement thấp → product journey chưa hoạt động → call-list về sau sẽ không đủ.

## Đo đúng (từ §8)

Luôn tách **kênh lõi vs marketplace**; dùng **completed-only**; **waterfall point-in-time**
(không dùng `mart_customer_status_snapshot_monthly` cho xu hướng).

## Nguyên tắc Holdout 10–20% (tham chiếu §5.5)

Nguồn chi tiết: [../05-action-plans/action-flows.md](../05-action-plans/action-flows.md) — §5.5 *Đo lường (bắt buộc có nhóm chứng)*.

- Mỗi luồng hành động (1–5) giữ lại **10–20% không tác động** làm nhóm chứng.
- So sánh tỷ lệ mua lại giữa nhóm được tiếp cận và nhóm chứng → đo **incremental lift**.
- Tránh nhận công cho đơn tự đến (organic reorder) — không có holdout thì overcount conversion.
- Khi pool nhỏ (Luồng 1: 6 khách) → holdout 1 người là đủ; ghi rõ trong execution-log.

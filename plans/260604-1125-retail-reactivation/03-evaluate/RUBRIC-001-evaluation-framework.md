---
title: "RUBRIC-001 - Evaluation Framework"
stage: 3
status: living
source: new
---

# RUBRIC-001 - Evaluation Framework

**Registry:** [RUBRIC-001](../REGISTRY.md#rubric-001)

> **Mục đích:** Dùng rubric này để chấm cơ hội từ stage 04 trước khi promote lên plan ở stage 05.
> Active priority board hiện nằm trong [`README.md`](./README.md#priority-board). File này chỉ giữ framework chấm điểm, không giữ bảng ưu tiên hiện hành.

---

## Tiêu Chí Chấm (Thang 1-5)

| Tiêu chí | 1 | 3 | 5 |
|---|---|---|---|
| **Impact** | Tác động doanh thu/retention thấp, nhỏ lẻ | Tác động vừa, một phân khúc | Tác động lớn, nhiều khách hoặc doanh thu cao |
| **Effort** | Rất khó / tốn nhiều nguồn lực | Trung bình | Dễ triển khai ngay, ít nguồn lực *(điểm cao = dễ)* |
| **Confidence** | Chưa có bằng chứng, giả thuyết | Có tín hiệu, chưa kiểm chứng | Đã có data, benchmark rõ ràng, hoặc owner xác nhận |
| **Time-to-cash** | Tiền về sau >2 quý | Tiền về sau 4-8 tuần | Tiền về trong tuần / tháng này |

**Điểm ưu tiên = Impact × Confidence × Time-to-cash × Effort**

Tối đa = 625. Ngưỡng tham khảo để cân nhắc promote: `>= 100`, nhưng vẫn phải kiểm blocker và capacity.

---

## Gate Trước Khi Promote

| Gate | Câu hỏi |
|---|---|
| Evidence | Cơ hội dựa trên finding nào ở stage 02 hoặc lens nào ở stage 01? |
| Capacity | Owner/CSKH/Marketing/Data có đủ sức chạy không? |
| Blocker | Có blocker chưa gỡ như `fact_payments`, VOC, Zalo OA, catalog, margin artifact không? |
| KPI | Stage 06 sẽ đo bằng KPI nào? |
| Scope | Đây là một mũi nhọn rõ hay đang dàn mỏng quá nhiều lane? |

Không promote cơ hội sang stage 05 nếu blocker chính vẫn chưa có owner hoặc chưa có đường gỡ.

---

## Cách Dùng

1. Khi stage 04 có opportunity mới, chấm 4 tiêu chí ở trên.
2. Ghi source finding/lens và blocker rõ ràng.
3. Nếu điểm cao nhưng blocker chưa gỡ, đưa vào `Blocked / Needs Answer` trong [`README.md`](./README.md#blocked--needs-answer).
4. Nếu đủ điều kiện chạy, đưa vào `Ready To Move` trong [`README.md`](./README.md#ready-to-move).
5. Khi quyết định promote, ghi vào [`decision-log.md`](./DEC-001-decision-register.md) và tạo/cập nhật plan ở [`../05-action-plans/`](../05-action-plans/).

---
title: "06 · Execute — Thực thi & đo lường"
stage: 6
status: active
source: plans/260604-1125-retail-reactivation/
---

# 06 · Execute — Thực thi & đo lường

> **Luồng:** ← [05-action-plans](../05-action-plans/) · → (LOOP) [02-understand](../02-understand/) (kết quả sinh finding mới)

Stage này chạy các action plan đã thiết kế, đo kết quả theo KPI bắc cầu, và **đóng vòng lặp học**: mỗi tuần thực thi cho ra finding mới (lý do bỏ, nhóm yield thấp, message không work) — những finding đó quay ngược về [02-understand](../02-understand/README.md) để cập nhật chẩn đoán và điều chỉnh kế hoạch.

---

## Index

| File | Mô tả |
|---|---|
| [kpi.md](./kpi.md) | Bảng KPI lagging (hết ế) + leading (product-journey health) + nguyên tắc holdout |
| [execution-log.md](./execution-log.md) | Nhật ký thực thi tuần — kết quả, lý do bỏ, KPI cập nhật |

---

## Vòng lặp đóng

```
05-action-plans
      ↓ chạy
06-execute  →  đo KPI  →  ghi execution-log
                                  ↓
                          finding mới (lý do bỏ / nhóm yield 0% / message fail)
                                  ↓
                          02-understand  (cập nhật chẩn đoán)
                                  ↓
                          03-evaluate → 04-opportunities → 05-action-plans
                                  ↓
                               (lặp lại)
```

**Thực thi không phải điểm cuối — là điểm khởi đầu vòng học tiếp theo.**

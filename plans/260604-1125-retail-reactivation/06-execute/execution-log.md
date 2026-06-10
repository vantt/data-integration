---
title: "Nhật ký thực thi — Stage 6 Execute"
stage: 6
status: tracking
source: new
---

# Nhật ký Thực thi

> **Vòng lặp học:** kết quả thực thi = finding mới → cập nhật ngược về [02-understand](../02-understand/README.md). Đây là điểm đóng vòng của path.

---

| Tuần | Hành động chạy | Luồng/Plan | Kết quả (đặt lại Y/N · lý do bỏ · thấy hiệu quả?) | KPI cập nhật |
|---|---|---|---|---|
| *VD: 2026-W24* | *Zalo 31 REORDER_NUDGE + 16 SECOND_ORDER nóng* | *Luồng 3 + 4* | *Y: 8 · N: 23 (lý do bỏ: 12 không phản hồi, 7 "đang dùng kênh khác", 4 "chưa hết") · thấy hiệu quả: 11/24 có phản hồi* | *M1 repeat: 18% · Day-7 engagement: 46%* |

---

## Hướng dẫn ghi log

- Mỗi tuần ghi **1 dòng tổng hợp** sau review T7 (theo lịch 5.3).
- Cột **Kết quả** ghi đủ 3 chiều: đặt lại Y/N, lý do bỏ (gom nhóm), "thấy hiệu quả" Y/N.
- Cột **KPI cập nhật** chỉ ghi KPI nào **thay đổi** so với tuần trước.
- Phát hiện pattern mới (lý do bỏ lặp lại, nhóm yield 0%) → ghi note riêng dưới bảng và **tạo finding trong [02-understand](../02-understand/README.md)**.

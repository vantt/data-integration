# Phase 4: quan sát 7 đêm và đóng

**Effort:** 0.25d + 7 đêm · **Phụ thuộc:** phase 3 · **Đụng prod:** chỉ đọc

## Các bước

1. Mỗi sáng (gộp vào lần kiểm buổi sáng đang có): `resource-meter status` và `report --date <hôm qua> --top 10`; ghi một dòng vào bảng nhật ký dưới đây.
2. Sau 7 đêm: kiểm 7 tiêu chí chấp nhận trong `plan.md`; so thời gian nightly với trung vị trước khi cài.
3. Chạy `compare` giữa đêm đầu và đêm cuối để chứng minh lệnh dùng được.
4. Báo cáo đóng `reports/phase-04-close.md`; cập nhật `status: completed` trong `plan.md`.

## Nhật ký

| Ngày | Nightly (phút) | RSS công cụ (MB) | CPU công cụ (%) | Ghi đĩa (MB) | Bước thiếu | Model thiếu | Ghi chú |
|---|---|---|---|---|---|---|---|

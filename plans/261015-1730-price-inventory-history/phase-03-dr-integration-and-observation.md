# Phase 3: phối hợp DR, theo dõi, đóng plan

**Effort:** 0.25d + 7 đêm theo dõi · **Phụ thuộc:** phase 2 đã deploy. Việc kiểm off-site (bước 3) chờ plan DR phase 2 (sidecar off-site) chạy trên prod · **Đụng prod:** chỉ đọc

## Bối cảnh

Plan DR (`plans/261015-1140-backup-restore-dr/`) xếp `data_lake/sapo_v2_raw` là nguồn sự thật, lên off-site hằng ngày (`design.md:83`). Plan đó ghi rằng plan giá/tồn sẽ "thêm bảng vào danh sách xuất" (`design.md:26,96`; `plan.md:125,139`). Thiết kế ở đây đặt dữ liệu không dựng lại được vào raw, nên **không cần** thêm bảng vào `duckdb_snapshot.py --tables`. Chỉ cần sửa bảng phân loại và xác minh.

## Việc

1. **Báo chủ plan DR** (qua coordinator hoặc user, không tự sửa plan đó) ba điểm:
   - Dòng 96 của DR `design.md` cần đổi thành: "`sapo_v2_raw/product_daily_snapshot/`: nguồn sự thật, KHÔNG dựng lại được (ảnh chụp giá/tồn hằng đêm), lên off-site cùng `sapo_v2_raw`; hai bảng `fact_*_snapshot` vẫn phái sinh."
   - Không thêm gì vào `duckdb_snapshot.py --tables`.
   - T3 tự gồm ba bảng mới, vì `public_models.yaml` được sinh tự động.
2. **Tài liệu dùng chung:** nếu `docs/operations/backup-and-recovery.md` đã có (DR phase 0 tạo), thêm dòng phân loại cho thư mục raw mới **cùng commit** với phase này. Nếu chưa có thì chuyển nội dung cho DR phase 8.
3. **Xác minh off-site** (khi DR phase 2 đã chạy): `restic ls latest` có `sapo_v2_raw/product_daily_snapshot/`, và số file khớp với số file trên ổ. T2 của DR đọc được mọi file.
4. **Theo dõi 7 đêm** sau D2. Mỗi sáng ghi vào `reports/observation.md` trong thư mục plan:
   - Số file raw mới.
   - `coverage_ratio`.
   - Số dòng `as_of_date` mới ở hai bảng daily.
   - Số khoảng mới ở `fact_variant_price_changes`.
   - Thời lượng nightly.
5. **Đóng plan:**
   - Cập nhật mục "Lịch sử giá và tồn kho theo ngày" trong `plans/261013-1751-modularize-data-platform-suite/roadmap.md`: đã xong, kèm liên kết.
   - Chuyển danh sách người dùng (design §8) cho plan report (`plans/261014-2225-report-productization/`).
   - Đổi trạng thái plan bằng CLI `ak plan` (chạy `ak plan --help` trước), không sửa tay.

## Kiểm chứng (tiêu chí 1, 3, 7 của plan.md)

- 7/7 đêm có file raw, `coverage_ratio ≥ 0.98`, freshness check xanh.
- Mỗi đêm hai bảng daily có thêm đúng một `as_of_date`, số dòng trong ±5% của mức 15/10.
- Off-site có thư mục raw mới. Bảng phân loại DR có dòng mới.

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| DR off-site trễ, lịch sử chỉ nằm cùng ổ | Cao × Cao | Ghi thành điều kiện đóng plan. Trong lúc chờ, 7 bản backup cục bộ có `sapo_v2_raw` |
| Một đêm lỡ trong 7 đêm theo dõi | Trung bình × Trung bình | Ghi ngày thiếu vào `observation.md`, tìm nguyên nhân. Bộ đếm 7 đêm bắt đầu lại |

## Rollback

Không có thay đổi code. Nếu phải sửa tài liệu dùng chung thì `git revert` commit đó.

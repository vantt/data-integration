# Full refresh sản phẩm trên prod và so với dữ liệu hiện có (15/10/2026)

## Kết luận

**Cursor tăng dần của `products_batch` không kẹt, và không có cập nhật sản phẩm nào bị giấu sau
trạng thái `skipped`.** Danh mục sản phẩm trên Sapo đúng là không đổi từ 15/09/2026 13:51 (ICT):
560 sản phẩm, 684 biến thể. Tên, vendor, brand, trạng thái, loại, `modified_on`, số biến thể và tập
SKU biến thể của từng sản phẩm đều khớp với dữ liệu raw và `dim_products` đang có. Full refresh
không nạp dòng nào và không làm đổi dữ liệu kho.

## Các bước đã làm

Sau khi deploy D3 + bản sửa freshness xanh (nightly chạy tay `bf000c1b` SUCCESS), không có run nào
đang chạy.

1. **Ảnh "trước"** (11:32, chỉ đọc, ghi ra scratchpad ngoài lake): bản ghi raw mới nhất của mỗi sản
   phẩm (`sapo_v2_raw/product`) và `dim_products` (bản chép `olap.duckdb`). Raw: 560 sản phẩm,
   `modified_on` lớn nhất 2026-09-15 13:51:08+07, 684 biến thể; `dim_products`: 699 dòng.
2. **Full refresh riêng asset** (11:38): `dagster.materialize([ingest_sapo_v2_products_batch_asset],
   tags={"full_refresh": "true"})` trong `data_platform`, ghi vào instance Dagster (run
   `4e6f84e0-40a6-4a00-b002-cfe48cb20898`). Không asset nào khác chạy. Asset ingest chỉ ghi parquet
   raw, không giữ `duckdb_lock`.
   - Log: `--reset-cursor` xoá state cục bộ; lấy 12 trang, 560 sản phẩm, tất cả được coi là "mới"
     theo code; **0 load package** được nạp. Health DB ghi `skipped`, `full_refresh = 1`.
   - Lý do 0 package: ngoài bộ lọc trong code, dlt còn một bộ lọc `incremental` theo
     `sync_metadata.event_timestamp` với giá trị cuối 15/09 13:51. Sapo sắp sản phẩm theo
     `modified_on` giảm dần, nên nếu có bất kỳ sản phẩm nào sửa sau mốc đó thì nó đã lọt qua và được
     nạp. 0 package nghĩa là không có sản phẩm nào như vậy.
3. **Lấy trực tiếp toàn bộ sản phẩm từ API Sapo** (chỉ GET, cùng phiên và cùng 12 trang như asset)
   để bắt cả trường hợp đổi tên hay thêm biến thể mà không đổi `modified_on`. So với ảnh "trước":
   - 560 dòng, `modified_on` lớn nhất `2026-09-15T06:51:08Z` (= 13:51 ICT), trùng raw.
   - name, vendor, brand, status, product_type, variant_count, `modified_on`: **0 khác biệt**.
   - Tập SKU biến thể của từng sản phẩm so với `dim_products`: **0 khác biệt**; mọi sản phẩm trên
     Sapo đều có trong `dim_products`.
   - 2 sản phẩm có trong raw nhưng không có trong lần lấy trực tiếp, và 2 sản phẩm bị lấy trùng: cả
     4 có cùng `modified_on` 2023-01-05 (đợt import hàng loạt). API trả thứ tự không ổn định giữa
     các trang khi giá trị sắp xếp bằng nhau; đây là lỗi phân trang của lần lấy, không phải sản phẩm
     bị xoá.
4. **Ảnh "sau"** (11:4x): `dim_products` giống hệt từng byte. Raw: mọi trường giống hệt; chỉ cột
   kiểm `payload_md5` khác ở 335 dòng, vì 553 sản phẩm có từ 2 bản ghi raw trở lên tại cùng
   `event_timestamp` (nạp trùng từ trước) và lần chụp chọn một bản bất kỳ. Không có dữ liệu mới.
5. Các run theo lịch sau đó (`pipeline_sapo_v2_realtime_job`, `pipeline_hug_realtime_job`) SUCCESS.

## Phát hiện phụ (không gấp, không làm gì)

- **Phân trang theo `modified_on` có thể bỏ sót sản phẩm khi nhiều sản phẩm cùng thời điểm sửa**
  (vd. sửa hàng loạt). Với tải tăng dần hằng ngày, ảnh hưởng nhỏ vì nhóm trùng thường nằm trọn
  trong một trang và lần chạy sau quét lại phần chồng (`min_overlap_items = 100`). Nếu cần chắc
  chắn: thêm khoá phụ ổn định (`id`) vào thứ tự sắp xếp, nếu API Sapo hỗ trợ.
- **Raw sản phẩm có bản ghi trùng** cùng `entity_id` và `event_timestamp` (553/560 sản phẩm). Staging
  lọc trùng bằng `ROW_NUMBER` nên không ảnh hưởng số liệu.
- `pipeline_batch_fullrefresh_job` chưa từng chạy trên prod (0 run `full_refresh` trong lịch sử
  `products_batch`).

## Câu hỏi cho user

Không có.

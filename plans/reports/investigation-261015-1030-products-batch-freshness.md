# Check freshness `products_batch` đỏ mỗi đêm: nguyên nhân và đề xuất (15/10/2026)

## Kết luận

Check đỏ vì **cách đo**, không phải vì dữ liệu sản phẩm cũ. Lần nạp sản phẩm chạy đều và thành công,
nhưng Sapo hầu như không có sản phẩm nào bị sửa nên dlt không nạp gì; khi đó asset ghi trạng thái
`skipped`. Check freshness chỉ tính `status = 'success'`, nên tuổi dữ liệu tăng mãi từ lần duy nhất
có sản phẩm đổi (15/09). Đây cùng cơ chế với `customers_batch` (đỏ/xanh tuỳ ngày có khách mới hay
không), chỉ nặng hơn vì danh mục sản phẩm rất ít đổi. Dữ liệu sản phẩm phía sau không bị thiếu.

## Check đo gì

- Asset: `sapo/ingest_sapo_v2_products_batch_asset` (connector `sapo_v2`, chạy trong
  `pipeline_batch_nightly_job` và vài lần chạy khác trong ngày).
- Check: `freshness` (`orchestration/asset_checks/freshness_checks.py`), mức ERROR, SLA
  `freshness_hours: 28` (`orchestration/config/ingestion_sla.yaml`).
- Cách tính: tuổi = bây giờ − `last_success()` trong `ingestion_health.db`
  (`orchestration/asset_checks/health_db.py:28`), chỉ lấy dòng `status = 'success'`.
- Trạng thái ghi trong `orchestration/connectors/sapo_v2/assets.py`:
  `status = "success" if loaded_packages else "skipped"`. Tức là `skipped` = pipeline chạy xong,
  không lỗi, nhưng không có package nào để nạp (không có dữ liệu mới).

## Bằng chứng (chỉ đọc)

- `ingestion_health.db` (volume `monitoring_db`, đọc `mode=ro` trong `data_platform`):
  - `products_batch`: **1** lần `success` (15/09 20:00 UTC, 1 dòng) và **83** lần `skipped` (0 dòng)
    từ 16/07 tới 14/10. Không có lần `failure` nào.
  - `customers_batch`, để so sánh: 52 `success`, 32 `skipped`; lần success gần nhất 14/10.
- Raw `sapo_v2_raw/product` (đọc parquet): 560 sản phẩm; `batch_sync` chỉ có 13 bản ghi đổi trong
  tháng 7, 0 trong tháng 8, 1 trong tháng 9 (15/09), 0 trong tháng 10.
- Dữ liệu phía sau còn đủ (bản chép `olap.duckdb` trong container, đã xoá): `dim_products` 699
  dòng / 571 sản phẩm. Từ 16/09 có 248 dòng bán của 24 sản phẩm; **0** dòng không khớp
  `dim_products`, **0** sản phẩm thiếu `sku`. Không có sản phẩm mới nào bán ra mà kho chưa biết.
- Giá và tồn kho không đi qua asset này: giá lấy từ `price_list` (`fact_variant_prices_snapshot`),
  tồn kho từ `inventory_transaction_v2`. Hai nguồn này không bị ảnh hưởng bởi check đỏ.

## Giới hạn của kết luận

Kết luận "Sapo không đổi sản phẩm" dựa trên việc dlt lọc theo `modified_on` (sắp giảm dần, dừng sớm
khi gặp đủ bản ghi cũ) và việc không có sản phẩm bán ra nào bị thiếu. Em không gọi API Sapo để đếm
sản phẩm sửa sau 15/09 (tránh dùng phiên đăng nhập prod cho một việc chỉ đọc). Nếu Sapo không đổi
`modified_on` của sản phẩm khi chỉ sửa biến thể, thay đổi kiểu đó sẽ bị bỏ sót; nên kiểm một lần
bằng full refresh trên shadow khi sửa.

## Đề xuất sửa

1. **Freshness đo "lần chạy gần nhất thành công", không phải "lần cuối có dữ liệu mới".** Trong
   `health_db.last_success()` (hoặc một hàm mới cho freshness) tính cả `status IN ('success',
   'skipped')`: `skipped` nghĩa là đã hỏi nguồn và nguồn không có gì mới, tức là dữ liệu vẫn tươi.
   Các check xu hướng (`row_count_within_trend`, đếm lần 0 dòng) vẫn chỉ dùng `success`. Áp cho mọi
   asset ghi `skipped` (sapo_v2, hug, misa_amis). Hệ quả: `products_batch` freshness và
   `customers_batch` freshness hết đỏ giả.
2. **Nếu muốn biết "lâu rồi không có sản phẩm đổi"**, đó là một tín hiệu nghiệp vụ khác: thêm check
   mức WARN riêng (vd. "không có thay đổi sản phẩm trong 30 ngày") thay vì dùng check freshness ERROR.
   Với danh mục ít đổi như Fine Japan, em đề xuất không thêm.
3. **Kiểm một lần** bằng full refresh `products_batch` trên shadow (không phải prod) để chắc không
   có sản phẩm sửa mà bị bỏ sót, rồi so với raw hiện có.

Sửa (1) chỉ đổi Python của asset check, không đổi số liệu: đi qua gate M và runbook deploy như các
thay đổi code khác. Sau deploy, nightly sẽ còn 4 check đỏ có từ trước thay vì 5.

## Câu hỏi cho user

1. Đồng ý sửa theo hướng (1), áp cho mọi asset có trạng thái `skipped`, và không thêm check (2)?

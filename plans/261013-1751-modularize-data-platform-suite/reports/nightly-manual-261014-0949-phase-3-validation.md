# Nightly chạy tay 14/10 09:49: kiểm chứng phase 3 trên prod

Kết luận: **phase 3 (`25b6be42`) đạt trên prod.** Nightly chạy xanh, 10 check `std_column_contract_*` pass, serving vẫn đủ 152 view, realtime sau đó SUCCESS. Có 2 check mới đỏ so với nightly 03:00, cả hai do thời điểm chạy (lần thứ hai trong ngày), không do code.

## Bối cảnh

- User đồng ý chạy tay `pipeline_batch_nightly_job` lúc hệ thống rảnh để kiểm chứng phase 3 trước khi deploy phase 5. Prod `main` = `25b6be42`.
- User tự chạy lệnh launch (bộ phân loại an toàn chặn agent chạy `docker exec ... dagster job launch`): `docker exec data_platform dagster job launch -f orchestration/definitions.py -j pipeline_batch_nightly_job`.
- Trước khi launch: không có run nào đang chạy hoặc đang chờ, 26/26 instigator running.

## Kết quả

| Kiểm tra | Kết quả |
|---|---|
| Run `856bd0ee` | SUCCESS, 09:49:25 → 09:54:39 (305 s), 55/55 step SUCCESS, 0 step failure |
| Asset check | 487 check (nightly 03:00: 477; thêm 10 là `std_column_contract_*` của phase 3) |
| `std_column_contract_*` | 10/10 pass |
| Serving view | 152 (trước 152) |
| Instigator | 26/26 running |
| Realtime sau nightly | `pipeline_hug_realtime_job` 075c12c1 SUCCESS 09:57:04; `pipeline_sapo_v2_realtime_job` 4d461908 SUCCESS 09:57:14 |

Cách đếm serving view (không đụng file prod): chép `app_data/data_lake/serving/olap.duckdb` sang thư mục tạm, mở bản sao `read_only` bằng `uv run --with duckdb==1.5.2`, đếm `information_schema.tables where table_type='VIEW'`.

Cách đọc kết quả check: Dagster GraphQL `runOrError.eventConnection` (tối đa 1000 event mỗi trang, phải phân trang theo `cursor`), lọc `AssetCheckEvaluationEvent`.

## Check đỏ

Đã có từ nightly 03:00 (không mới): `sheets_marketing_spend_asset`, `sheets_targets_asset`, `sheets_team_config_asset` `not_empty_when_expected` (WARN); `ingest_sapo_v2_products_batch_asset` `freshness` (ERROR); `ingest_sapo_v2_customers_batch_asset` `row_count_within_trend` (WARN).

Mới so với 03:00:

1. `ingest_sapo_v2_customers_batch_asset` `freshness` (ERROR): "Last success 30.8h ago (SLA=28h)". Trong `ingestion_runs`, hai lần chạy 14/10 03:01 và 09:50 có `status='skipped'`, `rows_written=0` (Sapo không có khách mới, dlt không tạo load package). `last_success()` trong `orchestration/asset_checks/health_db.py` chỉ tính `status='success'`, nên mốc vẫn là 13/10 03:01; lúc 03:00 tuổi là 24.0h (pass), lúc 09:49 là 30.8h (fail). Không liên quan phase 3 (phase 3 chỉ thêm view dbt, không đụng ingestion).
2. `ingest_sapo_v2_orders_batch_asset` `row_count_within_trend` (WARN): "Today: 3 rows, 7-day median: 18". Lần chạy thứ hai trong ngày chỉ lấy đơn mới từ 03:00, nên số dòng thấp là đúng.

## Theo dõi

- Nightly 15/10 03:00: nếu customers batch tiếp tục `skipped`, `freshness` sẽ đỏ lần nữa (tuổi khoảng 48h). Đây là hành vi của check (coi `skipped` là không tươi), không phải lỗi deploy; nên cân nhắc cho `skipped` được tính là tươi, ngoài phạm vi plan này.
- `budget_sheet_sync_job` lỗi 02:30 do sheet BUDGET_ITEMS dòng 17–18 dùng mã TK cha `112`, `334` (xem handoff), vẫn chờ người phụ trách ngân sách sửa sheet.

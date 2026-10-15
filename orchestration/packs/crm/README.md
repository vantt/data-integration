# Pack `crm` (orchestration)

Phần Dagster của pack CRM: đưa dữ liệu qua lại giữa warehouse và app CRM (`crm/`, container `crm`), và sao lưu CRM. Phần dbt: [transformation/models/packs/crm/README.md](../../../transformation/models/packs/crm/README.md). Hợp đồng chung của pack: [../README.md](../README.md).

**Cho ai:** vận hành nền tảng; gián tiếp là nhân viên dùng app CRM (cache CRM luôn theo dữ liệu warehouse mới nhất).

## Asset và job

| Asset / job | File | Làm gì |
|---|---|---|
| 11 `crm_*_export` (group `crm_writeback`) | `crm_writeback_assets.py` | Đọc SQLite của CRM (read-only, `ATTACH ... READ_ONLY`) và ghi parquet vào `data_lake/crm_export/` (snapshot hoặc incremental theo cursor) cho source dbt `crm_export` |
| `crm_cache_refresh` (group `reporting_layer`) | `crm_sync.py` | Sau khi serving (`olap.duckdb`) build xong, POST `/admin/refresh` để CRM nạp lại cache. Fire-and-forget: lỗi HTTP chỉ log cảnh báo |
| `crm_backup`, `crm_restore_verify` (group `ops_maintenance`) | `crm_sync.py` | POST `/admin/backup` rồi gọi sidecar `crm_drill_runner` để khôi phục thử; lỗi làm đỏ run |
| `crm_backup_job`, `crm_backup_schedule` (02:00 ICT, bật sẵn) | `jobs.py` | Chạy hai asset backup, không giữ khoá `dbt_rw` |

`NIGHTLY_ASSETS` = 11 export + `crm_cache_refresh`: job nightly/full refresh chọn chúng qua kernel. `AFTER_SERVING_ASSETS` = `crm_cache_refresh`: 6 job đồng bộ của connector `sapo_v2`, `shopee`, `misa_amis`, `sheets` chạy nó sau `build_serving_db` qua `orchestration.job_support.after_serving_selection()`; connector không import pack này. Tắt pack `crm` (bỏ khỏi `packs:` trong `orchestration/config/modules.yaml`, cùng `sales_playbook` đang phụ thuộc nó) thì các job đó kết thúc ở serving.

## Cấu hình

| Biến | Nguồn | Ghi chú |
|---|---|---|
| `CRM_REFRESH_URL`, `CRM_BACKUP_URL`, `CRM_DRILL_URL` | Tenant setting: env cùng tên, nếu không có thì `orchestration/tenants/<tenant>/config.py` | Không có mặc định trong pack; thiếu thì asset lỗi `TenantConfigError` |
| `CRM_REFRESH_TOKEN`, `DRILL_TOKEN` | Env (`.env.docker`) | Header xác thực; không đặt thì không gửi |
| `CRM_REFRESH_TIMEOUT_SEC` (10), `CRM_BACKUP_TIMEOUT_SEC` (120), `CRM_DRILL_TIMEOUT_SEC` (330) | Env, có mặc định | |
| `CRM_DB_PATH` (`/app/var/crm_data/crm.db`), `DBT_DATA_LAKE_PATH` | Env, có mặc định | Đường dẫn trong container, không phải giá trị doanh nghiệp |

## App CRM đọc gì từ warehouse

App CRM đọc `serving/olap.duckdb` read-only theo tên relation (`crm/sync/duckdb_reader.py`, `crm/src/adapters/outbound/duckdb/`). Các bảng nó đọc (lõi, `finance`, `sales_playbook`, `hug`, tenant) đều giữ nguyên tên khi dời module; danh sách hợp đồng ở `scripts/checks/public_models.yaml`.

## Phần còn là của Fine Japan

- Địa chỉ CRM trong mạng docker của deployment (`crm:8090`, `crm_drill_runner:9000`) nằm ở `orchestration/tenants/fine_japan/config.py`.
- Dữ liệu trong SQLite của CRM.

# Tenant `fine_japan` (orchestration)

Cấu hình của doanh nghiệp mà deployment này chạy cho. Nguyên tắc: logic là sản phẩm (kernel, connector, pack), dữ liệu và cấu hình là của doanh nghiệp (tenant). Code chung đọc giá trị tenant qua `orchestration.tenants.setting(name)` và **không có giá trị mặc định**: thiếu thì báo `TenantConfigError` (fail closed) thay vì dùng giá trị của doanh nghiệp khác. Bật tenant: `tenants: [fine_japan]` trong [`../../config/modules.yaml`](../../config/modules.yaml). Phần dbt: [transformation/models/tenants/fine_japan/README.md](../../../transformation/models/tenants/fine_japan/README.md). Kiến trúc: [docs/architecture/modules.md](../../../docs/architecture/modules.md) mục 10.

## `config.py`

Mỗi giá trị bị ghi đè bởi biến môi trường cùng tên khi biến đó được đặt (kể cả chuỗi rỗng), giống hành vi `os.environ.get(name, default)` trước đây. Giá trị giữ nguyên như mặc định cũ trong code chung.

| Tên | Dùng ở | Trước đây nằm ở |
|---|---|---|
| `SHEETS_SENSOR_TARGETS_URL`, `SHEETS_SENSOR_MARKETING_URL`, `SHEETS_SENSOR_US_SHIPMENT_PRICES_URL` | `sensors/sheets_modified_sensor.py` (`ingest_sheets_modified_sensor`, đọc mỗi tick; thiếu thì tick lỗi, code location vẫn chạy) | Mặc định trong sensor |
| `CRM_REFRESH_URL`, `CRM_BACKUP_URL`, `CRM_DRILL_URL` | Pack `crm` (`crm_sync.py`, đọc khi asset chạy) | Mặc định trong `assets/crm_sync.py` |
| `APPROACH_SCRIPT_LOAD_URL` | Pack `sales_playbook` (đọc khi asset chạy) | Mặc định trong `assets/approach_script_generation.py` |

Thêm một giá trị: khai báo ở đây, đọc bằng `setting("<TÊN>")` ở code chung, ghi vào bảng trên. Test: `orchestration/tenants/__tests__/test_tenant_setting.py`.

## Cấu hình Fine Japan còn nằm ngoài thư mục này

User quyết định (14/10/2026) giữ nguyên chỗ, chỉ ghi nhận ở đây:

| Giá trị | Vị trí | Dùng bởi |
|---|---|---|
| Domain Sapo `fwg.mysapogo.com` | `ingestion/.dlt/config.toml` `[sources.sapo] domain` | Connector `sapo_v2` |
| `login_url` (`accounts.sapo.vn`, `domain=fwg`) | `ingestion/.dlt/config.toml` `[sources.sapo]` | Đăng nhập Sapo (cookie) |
| URL Cloudflare webhook worker | `ingestion/.dlt/config.toml` `[sources.sapo_webhook_source] worker_url` (env `WORKER_URL` ghi đè) | Connector `sapo_v2` (webhook consumer); connector `hug` đọc `sources.hug_webhook_source.worker_url` hoặc `WORKER_URL` |

Còn lại, chưa dời (ghi để làm sau): URL Google Sheet mặc định trong các reader `ingestion/src/gsheet_*.py` (env `SOURCES__SPREADSHEET_URL__<NAME>` ghi đè); literal Fine Japan trong SQL lõi (danh sách ở `transformation/docs/TAXONOMY.md` mục 6).

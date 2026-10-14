# Tenant `fine_japan` (orchestration)

Cấu hình của doanh nghiệp mà deployment này chạy cho. Nguyên tắc: logic là sản phẩm (kernel, connector, pack), dữ liệu và cấu hình là của doanh nghiệp (tenant). Code chung đọc giá trị tenant qua `orchestration.tenants.setting(name)` và **không có giá trị mặc định**: thiếu thì báo `TenantConfigError` (fail closed) thay vì dùng giá trị của doanh nghiệp khác. Bật tenant: `tenants: [fine_japan]` trong [`../../config/modules.yaml`](../../config/modules.yaml). Phần dbt: [transformation/models/tenants/fine_japan/README.md](../../../transformation/models/tenants/fine_japan/README.md). Kiến trúc: [docs/architecture/modules.md](../../../docs/architecture/modules.md) mục 10.

## `config.py`

Mỗi giá trị bị ghi đè bởi biến môi trường cùng tên khi biến đó được đặt (kể cả chuỗi rỗng), giống hành vi `os.environ.get(name, default)` trước đây. Giá trị giữ nguyên như mặc định cũ trong code chung.

| Tên | Dùng ở | Trước đây nằm ở |
|---|---|---|
| `CRM_REFRESH_URL`, `CRM_BACKUP_URL`, `CRM_DRILL_URL` | Pack `crm` (`crm_sync.py`, đọc khi asset chạy) | Mặc định trong `assets/crm_sync.py` |
| `APPROACH_SCRIPT_LOAD_URL` | Pack `sales_playbook` (đọc khi asset chạy) | Mặc định trong `assets/approach_script_generation.py` |

Thêm một giá trị: khai báo ở đây, đọc bằng `setting("<TÊN>")` ở code chung, ghi vào bảng trên. Test: `orchestration/tenants/__tests__/test_tenant_setting.py`.

## Cấu hình Fine Japan còn nằm ngoài thư mục này

### URL Google Sheet: biến môi trường `SOURCES__SPREADSHEET_URL__<NAME>`

Sáu URL Google Sheet là **cấu hình Fine Japan**, khai báo **một nơi duy nhất**: biến môi trường trong `.env.docker` (container) hoặc `.env.local` (máy host). Tên biến liệt kê trong [`.env.docker.example`](../../../.env.docker.example) (không có giá trị thật). Code không có URL mặc định: thiếu biến thì đúng chỗ dùng báo lỗi `SpreadsheetUrlNotConfigured` nêu tên biến (`ingestion/src/gsheet_auth.py`, `spreadsheet_url(name)`), còn Dagster definitions vẫn load. Ingestion không import `orchestration.tenants`.

| Biến | Reader (đọc khi asset chạy) | Sensor `ingest_sheets_modified_sensor` (đọc mỗi tick, CSV export của cùng sheet) |
|---|---|---|
| `SOURCES__SPREADSHEET_URL__TARGETS` | `ingestion/src/gsheet_targets.py` | ✅ tab đầu |
| `SOURCES__SPREADSHEET_URL__MARKETING_SPEND` | `ingestion/src/gsheet_marketing_spend.py` | ✅ tab đầu |
| `SOURCES__SPREADSHEET_URL__US_SHIPMENT_PRICES` | `ingestion/src/gsheet_us_shipment_prices.py` | ✅ tab `gid=304875363` |
| `SOURCES__SPREADSHEET_URL__TEAM_CONFIG` | `ingestion/src/gsheet_team_config.py` | — |
| `SOURCES__SPREADSHEET_URL__OVERHEAD_CLASSIFICATION` | `ingestion/src/gsheet_overhead_classification.py` | — |
| `SOURCES__SPREADSHEET_URL__BUDGET` | `ingestion/src/gsheet_budget_sync/` (đọc và ghi gợi ý) | — |

Trước đây sensor giữ bản sao riêng của ba URL (`SHEETS_SENSOR_*_URL` trong `config.py` này) và mỗi reader có URL mặc định viết cứng; cả hai đã bỏ.

### Giá trị giữ nguyên chỗ

User quyết định (14/10/2026) giữ nguyên chỗ, chỉ ghi nhận ở đây:

| Giá trị | Vị trí | Dùng bởi |
|---|---|---|
| Domain Sapo `fwg.mysapogo.com` | `ingestion/.dlt/config.toml` `[sources.sapo] domain` | Connector `sapo_v2` |
| `login_url` (`accounts.sapo.vn`, `domain=fwg`) | `ingestion/.dlt/config.toml` `[sources.sapo]` | Đăng nhập Sapo (cookie) |
| URL Cloudflare webhook worker | `ingestion/.dlt/config.toml` `[sources.sapo_webhook_source] worker_url` (env `WORKER_URL` ghi đè) | Connector `sapo_v2` (webhook consumer); connector `hug` đọc `sources.hug_webhook_source.worker_url` hoặc `WORKER_URL` |

Còn lại, chưa dời (ghi để làm sau): ba seed tenant mà lõi đọc (luật `dbt-seed`, allowlist trong `scripts/checks/boundary_allowlist.yaml`); literal Fine Japan trong SQL lõi (danh sách ở `transformation/docs/TAXONOMY.md` mục 6).

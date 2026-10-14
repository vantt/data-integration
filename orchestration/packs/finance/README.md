# Pack `finance` (orchestration)

Chi phí, lợi nhuận, kế toán MISA, dòng tiền và ngân sách. Phần dbt và mô tả đầy đủ: [transformation/models/packs/finance/README.md](../../../transformation/models/packs/finance/README.md).

Pack này **không có code Dagster riêng** (`ASSETS`, `NIGHTLY_ASSETS`, `JOBS`, `SCHEDULES`, `SENSORS` đều rỗng):

- Các model dbt của pack chạy trong asset dbt của kernel.
- Dữ liệu đầu vào đến từ connector `misa_amis` (sổ cái, chứng từ bán hàng) và `sheets`: `budget_sheet_sync_asset` (02:30) ghi hai seed ngân sách của tenant (`seed_cashflow_budget`, `seed_cash_allocation_policy` ở `transformation/seeds/tenants/fine_japan/`, tìm theo tên bằng `seed_path`), `budget_suggestion_writeback_asset` ghi gợi ý ngược lên Google Sheet.

Package có mặt để `packs:` trong `config/modules.yaml` khớp với phía dbt.

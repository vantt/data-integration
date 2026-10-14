# Pack `sales_playbook` (orchestration): thử nghiệm, chưa chuẩn hoá

> **Trạng thái: thử nghiệm, chưa chuẩn hoá.** Nội dung kịch bản là dữ liệu Fine Japan; cách sinh và nạp kịch bản sẽ đổi khi chuẩn hoá thành sản phẩm (sau Đợt 1).

Sinh kịch bản tiếp cận (approach script) cho các khách trong hàng đợi hành động mỗi đêm và nạp thẳng vào CRM, không qua người duyệt (chỉ linter máy). Phần dbt: [transformation/models/packs/sales_playbook/README.md](../../../transformation/models/packs/sales_playbook/README.md). Hợp đồng chung: [../README.md](../README.md).

**Cho ai:** nhân viên bán hàng/CSKH dùng kịch bản trong app CRM.

## Asset

| Asset | File | Làm gì |
|---|---|---|
| `approach_script_autogen` (group `approach_script_autogen`, deps `crm_cache_refresh`) | `approach_script_generation.py` | Chạy `scripts/generate_approach_scripts.py --cohort-from-queue` (đọc `mart_customer_sku_action_queue`, gọi model sinh văn bản) rồi POST kịch bản vào CRM. Fire-and-forget: lỗi không chặn job nightly |

Chạy trong `pipeline_batch_nightly_job` / `pipeline_batch_fullrefresh_job` (`NIGHTLY_ASSETS`). Không có job riêng. Pack này import `crm_sync` của pack `crm` để khai báo deps (allowlist `orch-import`, pack → pack).

## Cấu hình

| Biến | Nguồn | Ghi chú |
|---|---|---|
| `APPROACH_SCRIPT_LOAD_URL` | Tenant setting (env cùng tên, nếu không có thì `orchestration/tenants/<tenant>/config.py`) | Không có mặc định; thiếu thì asset lỗi `TenantConfigError` |
| `APPROACH_SCRIPT_AUTOGEN_PROVIDER` (`codex`), `APPROACH_SCRIPT_AUTOGEN_REASONING_EFFORT` (`low`), `APPROACH_SCRIPT_AUTOGEN_LIMIT` (10), `APPROACH_SCRIPT_AUTOGEN_TIMEOUT_SEC` (1800), `CRM_DB_PATH` | Env, có mặc định | |

## Phần còn là của Fine Japan

Danh mục kịch bản (`seed_action_scenario_registry`), prompt và luật trong `scripts/generate_approach_scripts.py` / `scripts/approach_script*`, địa chỉ nạp kịch bản (`crm:8090`) trong tenant config.

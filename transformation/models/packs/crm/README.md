# Pack `crm` (dbt)

Phần warehouse của app CRM (`crm/`): đọc dữ liệu CRM ghi ngược về data lake để đo nỗ lực tiếp cận khách, hiệu quả nhân viên và nhật ký hoạt động; cung cấp trạng thái liên hệ cho hàng đợi hành động (pack `sales_playbook`). Pack là sản phẩm dùng lại được; Fine Japan là doanh nghiệp đầu tiên bật dùng. Kiến trúc: [docs/architecture/modules.md](../../../../docs/architecture/modules.md) mục 8.

**Cho ai:** quản lý bán hàng/CSKH (dashboard nỗ lực CRM theo tuần), app CRM, pack `sales_playbook`.

## Đầu vào

| Nguồn | Ghi bởi | Ghi chú |
|---|---|---|
| dbt source `crm_export` ([staging/_sources.yml](staging/_sources.yml)), `data_lake/crm_export/` | `orchestration/packs/crm/crm_writeback_assets.py` (xuất bảng SQLite của CRM ra parquet trong job nightly) | 11 bảng: `crm_last_contact`, `crm_activity_log`, `crm_task`, `crm_note`, `crm_tag`, `crm_party_tag`, `crm_party_insight`, `crm_customer_profile_custom`, `crm_campaign_target`, `crm_app_user`, `crm_hug_voucher` (bảng cuối do pack `hug` đọc) |
| `core`: `dim_customers`, `dim_staff`, `fact_orders` | dbt | Lõi |

## Đầu ra

| Model | Layer | Dùng ở |
|---|---|---|
| `stg_crm__*` (9: `activity_log`, `app_user`, `campaign_target`, `customer_profile_custom`, `last_contact`, `note`, `party_insight`, `party_tag`, `task`) | staging (view) | Trong pack; `stg_crm__app_user` cho `dim_staff`, `stg_crm__last_contact` cho `sales_playbook` |
| `int_crm_party_tag_flags` | marts | `mart_customer_action_queue` (`sales_playbook`) |
| `int_crm_outreach_effort_events` | marts | Bảng sự kiện nỗ lực tiếp cận theo `(task_id, action_type)` |
| `mart_crm_activity_log`, `mart_crm_outreach_effort_by_action_weekly`, `mart_staff_performance_weekly` | marts (rolling, serving) | Metabase (`docs/analytics-handbook/blueprints/metabase/crm_outreach_effort_weekly.md`) |

Tên relation, schema và tag không đổi khi dời vào pack (Đợt 1 chỉ dời file).

## Cấu hình

Không có biến dbt riêng. Cấu hình phía orchestration (đường dẫn CRM SQLite, endpoint CRM) ở [orchestration/packs/crm/README.md](../../../../orchestration/packs/crm/README.md).

## Phần còn là dữ liệu Fine Japan

- Toàn bộ dữ liệu trong `crm_export` (khách, nhân viên, tag, ghi chú) là của Fine Japan.
- Nhãn kết quả liên hệ (`contact_result`, `outcome_label`, tập `is_reached`) đang viết trong SQL, kiểm kê ở [TAXONOMY.md](../../../docs/TAXONOMY.md).

## Lõi đọc gì từ pack này

Chỉ `dim_staff` đọc `stg_crm__app_user` (`crm_user_id`, `email`, `is_active`) qua `pack_ref('crm', 'stg_crm__app_user')`; hợp đồng cột trong `pack_contracts()` ([transformation/macros/packs/pack_contracts.sql](../../../macros/packs/pack_contracts.sql)), test `pack_contract` gắn trên `stg_crm__app_user`. Tắt pack `crm` thì `dim_staff.crm_user_id` NULL, các cột khác giữ nguyên ([docs/architecture/modules.md](../../../../docs/architecture/modules.md) mục 7 và 8.1). Pack `sales_playbook` đọc thẳng model crm nên phải tắt cùng.

## Phụ thuộc chéo (ghi trong `scripts/checks/boundary_allowlist.yaml`)

- `mart_customer_action_queue`, `mart_customer_sku_action_queue` (`sales_playbook`) → `stg_crm__last_contact`, `int_crm_party_tag_flags`: pack → pack.
- `stg_crm__*` đọc source `crm_export` (luật `dbt-source` chỉ cho connector/tenant đọc source).

Hướng thoát: khai báo phụ thuộc pack → pack và source của pack (cạnh lõi → crm đã qua `pack_ref`). Chuẩn hoá CRM (cấu trúc dữ liệu, entity, quyền, API/CLI/MCP) là hạng mục roadmap, không làm trong Đợt 1.

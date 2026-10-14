# Pack `sales_playbook` (dbt): thử nghiệm, chưa chuẩn hoá

> **Trạng thái: thử nghiệm, chưa chuẩn hoá.** Pack gom các model hàng đợi hành động đang chạy cho Fine Japan để tách khỏi lõi. Cấu trúc bảng, kịch bản và luật chọn khách sẽ còn đổi khi chuẩn hoá thành sản phẩm (sau Đợt 1).

Kịch bản bán hàng: chọn khách (và cặp khách × SKU) cần tiếp cận, gán loại cơ hội (`action_type`) theo danh mục kịch bản, để nhân viên xử lý trong CRM. Kiến trúc: [docs/architecture/modules.md](../../../../docs/architecture/modules.md) mục 8.

**Cho ai:** nhân viên bán hàng/CSKH qua app CRM (worklist, hàng đợi hành động) và detailView.

## Đầu vào

| Nguồn | Ghi chú |
|---|---|
| Seed `seed_action_scenario_registry` (`seeds/tenants/fine_japan/`) | Danh mục kịch bản của Fine Japan (dữ liệu tenant) |
| `core`: `dim_customers`, `mart_customer_tier`, `int_customer_sku_supply_tracking` | Lõi |
| `crm`: `stg_crm__last_contact`, `int_crm_party_tag_flags` | Pack → pack, khai báo trong allowlist |

## Đầu ra

| Model | Layer | Dùng ở |
|---|---|---|
| `dim_action_scenario_registry` | marts (rolling, serving) | App CRM (`crm/sync/`): danh mục loại cơ hội |
| `mart_customer_action_queue` | marts (rolling, serving) | App CRM, detailView |
| `mart_customer_sku_action_queue` | marts (rolling, serving) | App CRM; asset `approach_script_autogen` (orchestration pack này) |

## Cấu hình

Không có biến dbt riêng. Asset sinh kịch bản tiếp cận: [orchestration/packs/sales_playbook/README.md](../../../../orchestration/packs/sales_playbook/README.md).

## Phần còn là dữ liệu Fine Japan

- Nội dung kịch bản (`seed_action_scenario_registry`), nhóm SKU và chu kỳ dùng (`seed_sku_regimen_config`, lõi đọc qua `int_customer_sku_supply_tracking`).
- Ngưỡng và nhãn viết trong SQL (danh sách ở [TAXONOMY.md](../../../docs/TAXONOMY.md)).

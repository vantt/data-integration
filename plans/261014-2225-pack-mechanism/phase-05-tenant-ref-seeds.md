---
phase: 5
title: "tenant_ref: lõi đọc seed tenant qua seed mặc định rỗng đúng cột"
status: pending
priority: P1
effort: "0.5d"
dependencies: [2, 4]
---

# Phase 5: `tenant_ref` cho seed tenant mà lõi đọc

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/modules.md` §10 (tenant overlay: seed nào tenant ghi đè, seed mặc định của lõi, biến `tenant`); `transformation/models/tenants/fine_japan/README.md` (3 seed này là bản ghi đè của Fine Japan); README mới `transformation/seeds/defaults/README.md` (mỗi seed mặc định: ai đọc, hợp đồng cột, tenant ghi đè thế nào); `transformation/AGENTS.md` (quy tắc: lõi đọc seed tenant chỉ qua `tenant_ref`; tenant mới phải có đủ seed được ghi đè, chép từ bản mặc định); `scripts/checks/README.md`.

## Phạm vi (đã kiểm với code 14/10/2026)

| Seed tenant (`transformation/seeds/tenants/fine_japan/`) | Lõi đọc ở | Cách đọc |
|---|---|---|
| `seed_channel_targets` (cột: `channel_name, period_month, metric_type, target_value, target_source, notes`) | `core/marts/dim_channel_targets.sql:12` | `SELECT *` |
| `seed_sku_regimen_config` (cột: `sku, product_group, display_name, supply_days_per_unit, dose_reduction_buffer, remind_lead_days, journey_enabled`) | `core/marts/intermediate/int_customer_sku_supply_tracking.sql:42` | `SELECT *` |
| `seed_sku_alias_manual` (cột: `sapo_pack_sku, sapo_pack_unit, sapo_base_sku, sapo_base_unit, units_per_pack, misa_join_key, misa_qty_multiplier, notes`) | `core/marts/dim_sku_alias.sql:136` | chọn cột |

Ba seed tenant khác (`seed_action_scenario_registry`, `seed_cashflow_budget`, `seed_cash_allocation_policy`) chỉ pack đọc, không thuộc phạm vi.

## Thiết kế

- **Biến dbt `tenant`** trong `dbt_project.yml` `vars:` = `fine_japan`; rule `module-config` (phase 2) mở rộng: `tenants` trong `modules.yaml` có đúng 0 hoặc 1 phần tử và bằng `vars.tenant` (rỗng ↔ `""`).
- **Seed mặc định của lõi:** `transformation/seeds/defaults/<seed>__default.csv`, chỉ có dòng tiêu đề đúng tên và thứ tự cột của seed tenant. `dbt_project.yml` khối `seeds: sapo_warehouse: defaults:` khai `+column_types` cho từng seed theo **kiểu thật** của seed Fine Japan trong warehouse (lấy bằng `DESCRIBE` trên lake-A; seed Fine Japan hiện để dbt tự suy kiểu). Tên khác seed tenant nên không phạm rule `seed-duplicate` và `ingestion/src/utils/seed_paths.py` không bị ảnh hưởng.
- **Macro `tenant_ref(seed)`** (`transformation/macros/tenants/tenant_ref.sql`): `var('tenant')` khác rỗng → `ref(seed)`; rỗng → `ref(seed ~ '__default')`. Fine Japan compile ra đúng chuỗi relation cũ.
- **Kiểm tra (`check_boundaries.py`):**
  - Rule `dbt-seed` (Đợt 1 phase 7) đổi: lõi đọc seed trong `seeds/tenants/**` hợp lệ khi và chỉ khi `raw_code` có `tenant_ref('<seed>')`; `ref()` thẳng vẫn vi phạm. Xoá 3 dòng allowlist `dbt-seed`.
  - Rule mới `tenant-seed-contract`: với mỗi seed được gọi qua `tenant_ref`, có `seeds/defaults/<seed>__default.csv`; tenant đang bật (`modules.yaml`) có `seeds/tenants/<tenant>/<seed>.csv`; tiêu đề hai file giống nhau từng cột. Test pytest cho từng ca.
- Từ phase này bước 6b của gate thật sự chạy nhánh mặc định (`tenant: ""`).

## Files

- Create: `transformation/macros/tenants/tenant_ref.sql`, `transformation/seeds/defaults/{seed_channel_targets__default,seed_sku_regimen_config__default,seed_sku_alias_manual__default}.csv`, `transformation/seeds/defaults/_defaults__seeds.yml` (mô tả + `data_type` từng cột), `transformation/seeds/defaults/README.md`.
- Modify: 3 model lõi ở trên (thay `ref` bằng `tenant_ref`), `transformation/dbt_project.yml` (var `tenant`, khối `seeds: defaults:`), `scripts/checks/check_boundaries.py` (+ test), `scripts/checks/boundary_allowlist.yaml`, `scripts/shadow/README.md` (danh sách khác biệt dự kiến của bước 6b thêm: `dim_channel_targets` rỗng, `int_customer_sku_supply_tracking` theo cấu hình rỗng, `dim_sku_alias` không còn alias tay), tài liệu ở khối đầu.

## Verification

- **Gate M `--allow-new --allow-code-change`** (3 seed mới là node mới; checksum 3 model đổi): golden 83/83.
- **Compiled SQL giống hệt:** `dbt_inventory.py compiled-diff` không cờ exit 0.
- Bước 6b (lõi trần, `tenant: ""`) build xanh; 3 seed mặc định có 0 dòng và đúng kiểu; khác biệt nằm trong danh sách dự kiến.
- `check_boundaries.py` pass; thêm tạm `ref('seed_channel_targets')` thẳng vào lõi → fail; xoá tạm một cột trong seed mặc định → `tenant-seed-contract` fail.

**Đổi số:** không (profile Fine Japan).

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Kiểu seed mặc định lệch kiểu suy ra của seed Fine Japan → model `SELECT *` đổi kiểu ở profile lõi trần | Khai `+column_types` từ `DESCRIBE`; không ảnh hưởng Fine Japan |
| Job prod ghi lại seed tenant (budget sync, `sync_seeds.py`) | Không đụng 3 seed này; tên và vị trí seed tenant giữ nguyên |

## Rollback

`git revert` theo runbook. Ba bảng seed `*__default` còn lại trong warehouse: vô hại, xoá bằng `DROP TABLE` khi tiện.

---
phase: 3
title: "Hoàn thiện CDM: đóng các chỗ core đọc thẳng nguồn, test schema mức cảnh báo"
status: completed
priority: P1
effort: "1.5d"
dependencies: [2]
---

# Phase 3: CDM — close leaks

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md` (bản sống trên nhánh; sơ đồ authority/boundary, giao diện, quyền ghi). Trong lúc làm: tài liệu đi cùng commit với code, không dồn về phase 7. Phase chỉ được coi là xong khi tài liệu dưới đây khớp với code thật.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/std-layer-conventions.md` (std mới, ma trận phụ thuộc, test warn); `docs/architecture/modules.md` §3, §6 (danh sách std và allowlist còn lại).

## Goal

Áp ma trận phụ thuộc giữa các module: `core/` chỉ đọc `cdm/` và `core/`. Đóng các chỗ rò bằng model `std_*` pass-through theo quy ước đã có trong `docs/architecture/std-layer-conventions.md` (R1: downstream không đọc `stg_*`; R2: pass-through trung thành + `source_system`). Thêm test schema mức **warn** (quyết định: chưa enforce contract).

## Ma trận phụ thuộc (cưỡng chế bởi `check_boundaries.py`)

| Model ở | Được `ref` tới |
|---|---|
| `connectors/<x>/` | `connectors/<x>/`, seeds |
| `cdm/` | `connectors/*`, `cdm/`, seeds |
| `core/` | `cdm/`, `core/`, seeds |
| `packs/<p>/` | `cdm/`, `core/`, `packs/<p>/`, connector pack khai báo (`marketplace` → `shopee`, `finance` → `misa`, `facebook_*` → `facebook_*`) |
| `tenants/<t>/` | mọi thứ |
| `monitoring/` | mọi thứ |

`core/` và `packs/` đọc `tenants/` là vi phạm; các trường hợp hiện có thành **tenant hook** ghi trong allowlist (phase 6).

## Danh sách rò

**Sinh từ `depends_on` trong manifest + `model_buckets.yaml`**, không lấy từ văn bản scout. Danh sách đã biết (để đối chiếu, không phải danh sách đầy đủ):

| Model | Đang đọc | Hướng xử lý |
|---|---|---|
| `dim_customer_{addresses,contacts,notes,tags}` | `stg_sapo_v2_customer_*` | `cdm/std_customer_{addresses,contacts,notes,tags}` |
| `fact_order_transitions` | `stg_sapo_v2_orders` | `cdm/std_order_events` |
| `int_order_tags` | `src_sapo_v2_orders` | `cdm/std_order_tags` |
| `fact_sales`, `fact_orders`, `dim_teams` | `stg_teams`, `stg_team_members` | `cdm/std_teams`, `cdm/std_team_members` |
| `fact_targets` | `stg_targets` | `cdm/std_targets` |
| `fact_marketing_spend` | `stg_marketing_spend` | `cdm/std_marketing_spend` |
| `dim_gl_account` | `src_misa_account_ledger` | Chuyển `dim_gl_account` sang `packs/finance` (tên/schema giữ nguyên) |
| `fact_order_costs` | `stg_shopee_*`, `int_order_overhead_allocation` | Allowlist + ghi nợ kỹ thuật: core fact trộn phí sàn và overhead FJ |
| `dim_staff` | `stg_crm__app_user` | Tenant hook (CRM là của FJ), xử lý ở phase 6 |
| `mart_data_quality` | `fact_us_shipment_economics` | Tenant hook, phase 6 |

Pass-through giữ nguyên tên, kiểu và thứ tự cột; `source_system` thêm ở cuối. Nếu model core đang `select *` từ stg thì giữ danh sách cột tường minh để cột mới không lọt ra bảng public.

## Test schema (mức warn)

- Với mỗi `std_*`: test kiểm tra danh sách cột và kiểu (lấy kiểu thực tế từ `information_schema` trên lake-A), `config: {severity: warn}`. Không chặn nightly; cảnh báo hiện qua kết quả test của Dagster.
- Không bật `contract: enforced` ở plan này.

## Files to Create / Modify

- Create: các `cdm/std_*.sql` ở bảng trên + khai báo trong `cdm/_schema.yml`.
- Modify: các model core tương ứng (chỉ đổi `ref`); `model_buckets.yaml` (`dim_gl_account` → `packs/finance`).
- Modify: `docs/architecture/std-layer-conventions.md` (thêm các std mới, ma trận phụ thuộc).
- Modify: `scripts/checks/check_boundaries.py`, `boundary_allowlist.yaml`.

## Verification

- **Gate S** (phase 0), gồm pass `--full-refresh` cho incremental.
- `dagster_inventory diff`: chỉ thêm asset cho model view mới; selection của các job hiện có giữ nguyên tập model cũ (cộng các view mới nằm upstream là chấp nhận được, phải liệt kê).
- `check_boundaries.py` pass; allowlist chỉ còn các mục ghi ở bảng trên.

## Rollback

Revert commit; các view `std_*` mới còn lại trong `main_staging` vô hại, xoá bằng `DROP VIEW` nếu cần (liệt kê trong commit message).

## Kết quả thực hiện (2026-10-14)

**Trạng thái: hoàn thành trên nhánh, chưa deploy.** Commit `a35878af`. Thực hiện bởi worker Herdr `p03a01` (Sonnet), coordinator kiểm chứng lại bằng gate S.

- 10 view `std_*` pass-through mới trong `models/cdm/staging/`; 11 model core đổi `ref` sang tầng canonical, giữ danh sách cột tường minh.
- Test generic `std_column_contract` (tên/thứ tự/kiểu cột) mức warn cho 10 std mới; không enforce contract.
- Allowlist 61 → 46 (đã đóng 15 chỗ core đọc staging connector); còn 4 tenant hook, 2 MISA, 3 Shopee, 37 dbt-path tenant.
- Harness: `dbt_inventory.py diff --allow-code-change` chấp nhận dep bị đổi khi dep cũ vẫn nằm upstream (3 unit test). Duyệt qua mailbox `q-p03-a01-01`.
- Gate S (`--allow-new --allow-code-change`): PASS — 83 bảng giống hệt, cả sau full refresh.
- Tài liệu: `docs/architecture/modules.md` §3/§6, `docs/architecture/std-layer-conventions.md` (R9, R10), `docs/operations/refactor-safety-harness.md` §6.2, `scripts/checks/README.md`.
- Rollback: revert commit; 10 view `std_*` còn lại trong `main_staging`, xoá bằng `DROP VIEW` nếu cần.
- Tài liệu chi tiết: `docs/architecture/canonical-layer.md` (commit `d7f8a953`, kèm sửa comment `std_order_tags.sql`).
- 14/10: gate S chạy lại với baseline build cùng ngày tại `main` = `97d05451`: PASS. Gate nay tự build lại baseline khi khác ngày (commit `25b6be42`).

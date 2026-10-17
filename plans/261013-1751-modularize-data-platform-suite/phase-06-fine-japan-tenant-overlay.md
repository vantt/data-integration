---
phase: 6
title: "Pack sản phẩm (CRM, HUG, tài chính, kịch bản bán hàng) + tenant Fine Japan tối thiểu"
status: pending
priority: P2
effort: "3d"
dependencies: [3, 4, 5]
---

# Phase 6: Pack sản phẩm + tenant Fine Japan

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md` (bản sống trên nhánh). Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** README cho từng pack mới (`transformation/models/packs/<pack>/README.md`, `orchestration/packs/<pack>/README.md`: pack làm gì, cho ai, đầu vào, đầu ra, cấu hình, phần nào còn là dữ liệu Fine Japan); `transformation/models/tenants/fine_japan/README.md`, `orchestration/tenants/fine_japan/README.md`; `docs/architecture/modules.md` §8 (packs), §10 (tenant và hook sinh từ manifest).

## Quyết định của user (14/10/2026)

Bản cũ của phase này dời mọi thứ "chỉ Fine Japan dùng" vào `tenants/fine_japan/`. User quyết định khác:

- **CRM, HUG, phân bổ chi phí chung, dòng tiền/ngân sách (gộp vào pack finance) là sản phẩm dùng lại được**, không phụ thuộc ngành. Chúng thành **pack**; Fine Japan chỉ là doanh nghiệp đầu tiên bật dùng.
- **Kịch bản bán hàng** (hàng đợi hành động khách/SKU, bộ kịch bản tiếp cận) là thứ đáng tiền, sẽ thành sản phẩm, nhưng **chuẩn hoá để sau**. Trong phase này chỉ đặt vào một pack đánh dấu "thử nghiệm"; nội dung kịch bản là dữ liệu Fine Japan.
- **Chỉ US shipment là riêng Fine Japan.**
- HUG là module **nối lại khách từ sàn thương mại điện tử về mua trực tiếp với shop** (tại quầy, website).
- CRM đi theo hướng chuẩn hoá: cấu trúc dữ liệu, entity, quyền, thân thiện với agent (API, CLI, MCP chuẩn); UI là lớp trên, sinh theo từng doanh nghiệp và khẩu vị. Phần chuẩn hoá này **không làm trong phase 6** (đây vẫn là Đợt 1: chỉ dời file, không đổi số); ghi thành hạng mục roadmap.

Nguyên tắc chia:

- **Logic là sản phẩm (pack), dữ liệu và cấu hình là của doanh nghiệp (tenant).**
- **Connector lấy dữ liệu, pack dùng dữ liệu; hai bên gặp nhau ở lớp chuẩn `std_*`.** Connector không phụ thuộc pack; pack không phụ thuộc riêng một connector.
- **Lõi giữ doanh thu, pack finance giữ toàn bộ chi phí và lợi nhuận** (user chốt 14/10). Lý do: không phải connector nào cũng có giá vốn (sàn, Pancake, Haravan không quản lý kho), và chọn/đối chiếu nguồn giá vốn là logic kế toán chi phí. Chỉ có lõi thì xem doanh thu; bật pack finance thì xem thêm lợi nhuận. Ví dụ pack `sales_playbook` chứa model hàng đợi hành động, còn `seed_action_scenario_registry` (kịch bản của Fine Japan) nằm ở seed của tenant.

## Phạm vi dbt

Tên relation **giữ nguyên** (chỉ dời thư mục), nên không đổi số và không đổi tên bảng public.

| Đích | Nội dung | Ghi chú |
|---|---|---|
| `packs/crm/` | `stg_crm__*` (10), `marts/crm/*` (2), `mart_crm_activity_log`, `int_crm_party_tag_flags`, `int_crm_outreach_effort_events` | Phần warehouse của CRM. App `crm/` giữ nguyên vị trí |
| `packs/hug/` | `stg_hug_*`, `mart_hug_optin`, `mart_hug_attribution`, `stg_crm__hug_voucher` nếu chỉ HUG dùng | Module nối lại khách từ sàn về kênh trực tiếp. `src_hug_*` là dữ liệu nguồn, đặt ở `connectors/hug/` như các connector khác |
| `packs/finance/` (đã có) | Thêm chi phí và lợi nhuận: `int_order_cogs_reconciled`, `int_order_promo_goods_cost`, `fact_order_costs`, `fact_order_economics`, `mart_order_cogs_summary`, `int_customer_economics` (grep lại các model chi phí khác trong `core/`). Thêm overhead: `stg_overhead_account_classification`, `int_overhead_pool_monthly`, `int_order_overhead_allocation`; thêm dòng tiền/ngân sách: `fact_cashflow_budget`, `dim_cash_allocation_policy`, `mart_cashflow_{budget_vs_actual,forecast,reserve_status,unmapped_actuals}`, `mart_cash_surplus_allocation` | Đi cùng `fact_account_balance_monthly`, `fact_cash_movement`, `dim_gl_account` đã có |
| `packs/sales_playbook/` (thử nghiệm) | `mart_customer_action_queue`, `mart_customer_sku_action_queue`, `dim_action_scenario_registry` | README ghi rõ "thử nghiệm, chưa chuẩn hoá" |
| `tenants/fine_japan/` | US shipment: `stg_us_shipment_prices`, `int_us_shipment_line_prices`, `fact_us_shipment_economics` | Phần duy nhất riêng Fine Japan |
| `seeds/tenants/fine_japan/` | `seed_action_scenario_registry`, `seed_cashflow_budget`, `seed_cash_allocation_policy`, `seed_channel_targets`, `seed_sku_regimen_config`, `seed_sku_alias_manual` | Dữ liệu doanh nghiệp cho các pack. Seed do Python ghi (`seed_cashflow_budget`, `seed_cash_allocation_policy`) đi qua `seed_paths.py`; kiểm tra lại mọi writer sau khi dời |

Grep lại trước khi dời: mọi model còn nằm ở `transformation/models/{staging,intermediate,marts}/` cũ phải có đích rõ ràng; model nào không thuộc bảng trên thì hỏi lại, không tự xếp.

Trước khi dời các model mà CRM đọc (`int_customer_metrics`, `dim_customers_base`, `mart_hug_optin`…), đọc `crm/` (adapter outbound và `crm/sync/`) để biết CRM đọc chúng từ đâu; không đoán.

## Phụ thuộc giữa các tầng (sinh từ manifest)

Liệt kê bằng script từ manifest, mỗi cạnh một dòng trong `boundary_allowlist.yaml` kèm lý do và hướng xử lý:

- **Tenant hook** (`core/` hoặc `packs/` → `tenants/`): `dim_customers` (CROSSBORDER dùng đơn US), `mart_data_quality` → `fact_us_shipment_economics`.
- **Pack hook** (`core/` → `packs/`): sau khi gom chi phí vào pack finance còn `dim_customers` → `int_customer_economics` (hai cột `lifetime_gross_profit`, `lifetime_contribution_margin`) và `dim_staff` → `stg_crm__app_user` (cột `crm_user_id`). `check_boundaries.py` thêm quy tắc core → packs chỉ được qua allowlist.
- **Pack → pack** được phép nếu khai báo: `mart_hug_attribution` (hug) → `fact_order_economics` (finance). Giám sát: `mart_data_quality` → `fact_order_economics`.

**Không** sửa các hook trong phase này (Đợt 1 chỉ dời file). Hướng xử lý sau Đợt 1: macro điểm cắm `pack_ref(pack, model, columns)` trả về `ref()` khi pack bật, bảng rỗng đúng cột khi pack tắt; danh sách pack bật lấy từ `modules.yaml` qua biến dbt `enabled_packs` (xem `roadmap.md`).

**Ghi lại, không sửa trong Đợt 1:** `fact_order_costs` đang coi giảm giá là "dòng chi phí"; về nghĩa, giảm giá thuộc phía doanh thu. Tách sau, có đổi cấu trúc bảng.

## Phạm vi orchestration và cấu hình

- `orchestration/packs/crm/` ← `assets/crm_sync.py`, `assets/crm_writeback_assets.py`, job/schedule CRM backup.
- `orchestration/packs/sales_playbook/` ← `assets/approach_script_generation.py`.
- `orchestration/connectors/hug/` giữ nguyên (đã là connector từ phase 5); asset dbt của pack hug đi theo nhóm dbt.
- Khai báo pack cùng cách với connector (phase 5): `modules.yaml` thêm `packs: [crm, hug, finance, sales_playbook]` và `tenants: [fine_japan]`.
- Giá trị riêng Fine Japan đang nằm cứng trong code chung: URL Google Sheet mặc định (`orchestration/sensors/sheets_modified_sensor.py:45-66`), domain Sapo và webhook worker URL (`ingestion/.dlt/config.toml:11,14,24`), và mọi giá trị riêng Fine Japan trong code CRM/HUG tìm được khi dời. Dời vào `orchestration/tenants/fine_japan/config.py` (hoặc env của tenant) với **cùng giá trị**; code chung báo lỗi khi thiếu thay vì dùng mặc định. `check_boundaries.py` thêm quy tắc: không có URL/domain cứng trong `orchestration/connectors/**` và `orchestration/packs/**`.

## Verification

- Gate M (chỉ dời file và dời hằng số): golden 83/83, compiled SQL không đổi, inventory dbt chỉ đổi đường dẫn file, inventory Dagster không đổi (tên asset, job, selection giữ nguyên).
- `check_boundaries.py`: allowlist tenant hook và pack hook trùng khớp danh sách sinh từ manifest; check `check_taxonomy_inventory.py` không cảnh báo (vị trí file đổi thì cập nhật bảng vị trí trong `TAXONOMY.md`, hash giữ nguyên).
- Danh sách bảng CRM đọc ([scout dbt §2](reports/scout-dbt-graph-consumers.md)) đều còn trong serving; smoke test CRM trên shadow nếu có.
- Trên shadow, bỏ một biến cấu hình Fine Japan → code chung báo lỗi rõ ràng (fail closed).
- Sau deploy: nightly bằng tay như phase 4, cộng kiểm job CRM sync/writeback và HUG chạy thành công.

## Rollback

Revert commit + restart. Không có relation mới.

## Quyết định bổ sung khi thực thi (user, 14/10/2026 ~16:30, qua session thực thi)

1. `int_promo_642_monthly_total` (đối soát TK 642, không model nào đọc) → `packs/finance`.
2. `mart_sku_economics_monthly` → `packs/finance`, kèm 4 pack hook core → finance trong allowlist: `int_product_velocity_trend`, `mart_inventory_health` (chỉ dùng tốc độ bán), `mart_product_health`, `mart_product_action_queue` (dùng `realized_margin_pct`, `cogs_variance_pct`, `margin_outlier`). Gỡ sau Đợt 1 (xem `roadmap.md`, "Cơ chế pack").
3. `crm_cache_refresh`: các job của connector `sapo_v2`, `shopee`, `misa_amis`, `sheets` import từ `orchestration/packs/crm`. Mỗi connector một dòng allowlist (connector → pack), sửa sau Đợt 1.
4. **Domain Sapo và webhook worker URL giữ nguyên trong `ingestion/.dlt/config.toml`**; README của tenant ghi đó là cấu hình Fine Japan. Chỉ dời URL Google Sheet của `sheets_modified_sensor.py` sang `orchestration/tenants/fine_japan/config.py`, chạy fail-closed. (Thay cho dòng tương ứng ở mục "Phạm vi orchestration và cấu hình".)

**Ba điểm lệch giữa brief và manifest (session thực thi xử lý):**

- (a) CROSSBORDER trong `dim_customers` không phải cạnh `ref` mà là logic viết trong SQL (mã nhóm `TYPE_CROSSBORDER`/`CTN00014` và tín hiệu kênh US), nên không sinh được từ manifest. Ghi là **"logic hook"** trong `docs/architecture/modules.md` §10 và `TAXONOMY.md`, không đưa vào allowlist.
- (b) Sau khi dời, có thêm cạnh pack → connector (`fact_order_costs` → `stg_shopee_*`) và pack → pack (`fact_order_economics` → `int_shopee_order_fees` của pack marketplace). Khai báo trong allowlist, dùng lại lý do của các dòng cũ.
- (c) `stg_crm__hug_voucher` chỉ `mart_hug_attribution` đọc → vào `packs/hug`.

Baseline gate đã dời lên `111f1386` (lake-A build 16:05, golden 83/83).

## Đã chốt (14/10/2026)

1. Tên pack HUG: **`hug`** (một tên cho thư mục, bảng `mart_hug_*` và tên thương mại; README mở đầu bằng định nghĩa "nối lại khách từ sàn thương mại điện tử về mua trực tiếp với shop"). Hướng sản phẩm của HUG ghi ở `roadmap.md` (agent friendly, data model chuẩn, phân quyền, API/CLI/MCP; giao diện admin và landing page build on top).
2. Dòng tiền/ngân sách **gộp vào `packs/finance`**.

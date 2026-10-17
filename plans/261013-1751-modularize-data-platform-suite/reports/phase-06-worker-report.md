# Báo cáo thực thi phase 6 (pack sản phẩm + tenant Fine Japan tối thiểu): worker

- Ngày: 14/10/2026 (Asia/Saigon)
- Worktree: `/home/vantt/app/fg-dw-modular` (nhánh `refactor/modularize-suite`, HEAD `111f1386`). **Chưa commit, chưa stash, chưa push.** Index đang trống (mọi thay đổi ở working tree, kể cả các file đã `git mv`): khi commit hãy `git add -A` để git nhận đổi tên.
- Kết quả kiểm tại chỗ: dbt inventory 0 khác biệt, Dagster inventory 0 khác biệt, boundaries 0 vi phạm mới / 0 mục thừa, taxonomy 0 cảnh báo, pytest 237 passed. **Chưa chạy `gate.sh M`** (golden, compiled SQL, lake rỗng): coordinator chạy.
- Không đụng checkout prod (ngoài file này), `fg-dw-baseline`, container `data_platform`; không chạy dbt vào `app_data/`; không sửa file `.sql` nào (45 model và 6 seed dời byte-identical, đã so sha256).

## 1. File dời

| Đích | Số | Nội dung |
|---|---|---|
| `models/packs/crm/` | 14 model | 9 `stg_crm__*` (`staging/`), `int_crm_party_tag_flags`, `mart_crm_activity_log`, `mart_crm_outreach_effort_by_action_weekly`, `mart_staff_performance_weekly` (`marts/`), `int_crm_outreach_effort_events` (`marts/intermediate/`); source `crm_export` → `staging/_sources.yml` |
| `models/packs/hug/` | 5 model | `stg_hug_scan`, `stg_hug_optin_event`, `stg_crm__hug_voucher` (`staging/`), `mart_hug_optin`, `mart_hug_attribution` (`marts/`) |
| `models/connectors/hug/staging/` | 2 model | `src_hug_scan`, `src_hug_optin_event`; source `hug_raw` → `_sources.yml` |
| `models/packs/finance/` (thêm) | 18 model | Từ core: `intermediate/cogs/` (3: `int_order_cogs_reconciled`, `int_order_promo_goods_cost`, `int_promo_642_monthly_total`), `marts/sales/` (4: `fact_order_costs`, `fact_order_economics`, `mart_order_cogs_summary`, `mart_sku_economics_monthly`), `marts/intermediate/int_customer_economics`. Từ thư mục cũ: `staging/stg_overhead_account_classification`, `intermediate/overhead/` (2), `marts/` (7 dòng tiền/ngân sách) |
| `models/packs/sales_playbook/marts/` | 3 model | `mart_customer_action_queue`, `mart_customer_sku_action_queue`, `dim_action_scenario_registry` |
| `models/tenants/fine_japan/` | 3 model | `staging/stg_us_shipment_prices`, `intermediate/us_shipment/int_us_shipment_line_prices` (giữ thư mục để giữ tag `us_shipment`), `marts/fact_us_shipment_economics` |
| `seeds/tenants/fine_japan/` | 6 seed | `seed_action_scenario_registry`, `seed_cashflow_budget`, `seed_cash_allocation_policy`, `seed_channel_targets`, `seed_sku_regimen_config`, `seed_sku_alias_manual`; khối properties của `seed_action_scenario_registry` (trước nằm đầu `models/marts/schema.yml`) → `_fine_japan__seeds.yml` |
| `orchestration/packs/crm/` | 2 file | `crm_sync.py`, `crm_writeback_assets.py` (từ `orchestration/assets/`); `crm_backup_job` + `crm_backup_schedule` từ `definitions.py` → `jobs.py` |
| `orchestration/packs/sales_playbook/` | 1 file | `approach_script_generation.py` |

Tổng 45 model. Thư mục cũ `models/{staging,intermediate,marts}/` và `models/sources.yml` không còn. Mọi model nằm đúng thư mục bucket (0 mục `dbt-path`).

`dbt_project.yml`: anchor layer định nghĩa ở chỗ dùng đầu tiên (`connectors.sapo_v2.staging/intermediate`, `core.marts`) vì khối layer gốc không còn model; thêm `connectors.hug`, `packs.{finance.staging, crm, hug, sales_playbook}`, `tenants.fine_japan`; `+column_types` của `seed_action_scenario_registry` dời xuống `tenants: fine_japan:`. Cấu hình phân giải của mọi model/seed không đổi (dbt inventory 0 khác biệt).

`scripts/shadow/move_models.py` mở rộng: dời model đã ở module này sang module khác (core → pack), dời source không phải connector (`SOURCE_OWNER`: `hug_raw` → connector hug, `crm_export` → pack crm), xoá `models/sources.yml` khi rỗng. **Sửa lỗi của tool**: trước đây file properties bị `git rm` khi hết khối model dù phần đầu còn khối `seeds:` (làm mất properties + 4 test của `seed_action_scenario_registry`; Dagster inventory bắt được 4 check bị mất). Đã khôi phục khối seed và sửa điều kiện xoá.

## 2. Allowlist (sinh từ manifest + import orchestration)

Trước: 46 mục (37 `dbt-path` + 9 `dbt-ref`). Sau: 33 mục, `check_boundaries.py` trên manifest parse từ nhánh: `33 known, 0 new, 0 stale`.

Gỡ (13 + 37): 37 `dbt-path`; `dim_staff → stg_crm__app_user [core -> tenant]`, `fact_order_costs/fact_order_economics → int_order_overhead_allocation`, `fact_order_costs → stg_shopee_* [core -> connector]`, `fact_order_economics → int_shopee_order_fees [core -> pack]`, `mart_sku_economics_monthly → int_misa_sales_lines` (đổi bucket hoặc thành cạnh nội bộ finance). Còn giữ: `dim_sku_alias → int_misa_sales_lines`, `mart_data_quality → fact_us_shipment_economics`.

| Luật | Subject | Target |
|---|---|---|
| dbt-ref | dim_customers | int_customer_economics [core -> pack:finance] |
| dbt-ref | dim_sku_alias | int_misa_sales_lines [core -> pack:finance] |
| dbt-ref | dim_staff | stg_crm__app_user [core -> pack:crm] |
| dbt-ref | fact_order_costs | stg_shopee_order_revenue [pack:finance -> connector:shopee] |
| dbt-ref | fact_order_costs | stg_shopee_order_service_fees [pack:finance -> connector:shopee] |
| dbt-ref | fact_order_economics | int_shopee_order_fees [pack:finance -> pack:marketplace] |
| dbt-ref | int_product_velocity_trend | mart_sku_economics_monthly [core -> pack:finance] |
| dbt-ref | mart_customer_action_queue | int_crm_party_tag_flags [pack:sales_playbook -> pack:crm] |
| dbt-ref | mart_customer_action_queue | stg_crm__last_contact [pack:sales_playbook -> pack:crm] |
| dbt-ref | mart_customer_sku_action_queue | stg_crm__last_contact [pack:sales_playbook -> pack:crm] |
| dbt-ref | mart_data_quality | fact_order_economics [core -> pack:finance] |
| dbt-ref | mart_data_quality | fact_us_shipment_economics [core -> tenant:fine_japan] |
| dbt-ref | mart_hug_attribution | fact_order_economics [pack:hug -> pack:finance] |
| dbt-ref | mart_inventory_health | mart_sku_economics_monthly [core -> pack:finance] |
| dbt-ref | mart_product_action_queue | mart_sku_economics_monthly [core -> pack:finance] |
| dbt-ref | mart_product_health | mart_sku_economics_monthly [core -> pack:finance] |
| dbt-source | stg_crm__{activity_log, app_user, campaign_target, customer_profile_custom, last_contact, note, party_insight, task} | crm_export.<cùng tên bảng> (8 mục) |
| dbt-source | stg_crm__party_tag | crm_export.crm_party_tag, crm_export.crm_tag (2 mục) |
| dbt-source | stg_crm__hug_voucher | crm_export.crm_hug_voucher |
| dbt-source | stg_overhead_account_classification | gsheet_raw.overhead_account_classification_raw |
| orch-import | orchestration/connectors/{sapo_v2, shopee, misa_amis, sheets}/jobs.py | orchestration.packs.crm (4 mục) |
| orch-import | orchestration/packs/sales_playbook/approach_script_generation.py | orchestration.packs.crm |

Mỗi mục có lý do và hướng thoát; 4 hook của `mart_sku_economics_monthly` dùng đúng câu thoát được giao. Ngoài danh sách được giao, manifest cho thêm: 3 cạnh `sales_playbook → crm`, 12 mục `dbt-source` (pack crm/hug đọc `crm_export`, finance đọc sheet overhead), `orch-import` của `sales_playbook → crm`. Tất cả vào allowlist với lý do thật.

Lựa chọn:

- `fact_order_costs → stg_shopee_*`: **allowlist**, không thêm `shopee` vào `pack_connectors` của finance (giữ luật chặt).
- `stg_hug_* → src_hug_*`: **thêm `hug: [hug]` vào `pack_connectors`** (pack đọc connector của chính nó, như `marketplace → shopee`), nên không có mục allowlist. Nếu muốn chặt hơn thì đổi thành 2 mục allowlist.
- Luật "core → packs chỉ qua allowlist" **đã có sẵn** trong ma trận (`core` chỉ được `cdm`, `core`); thêm test chứng minh và ghi rõ trong docstring/README.

## 3. Thay đổi `check_boundaries.py`

- Luật mới `orch-import`: file trong `orchestration/connectors/<c>/` import `orchestration.packs.*`, hoặc file trong `orchestration/packs/<p>/` import pack khác (ast; bỏ qua `__tests__` và loader).
- `connector-url` mở rộng thêm domain trong string literal (`fwg.mysapogo.com`, ...; module path và tên file không khớp); luật mới `pack-url` cho `orchestration/packs/**`.
- `--write-allowlist` ghi description mới (allowlist sinh từ manifest + import).
- Test (`scripts/tests/test_check_boundaries.py`, mỗi luật fail trên vi phạm cài sẵn): core → pack; connector → pack (hai dạng import); pack → pack khác (pack tự import chính nó thì không); URL và domain trong pack/connector, không bắt nhầm module path/tên file.

## 4. Orchestration

- `orchestration/module_registry.py` (mới): đọc `connectors`/`packs`/`tenants` từ `config/modules.yaml`, import theo id. `connectors/__init__.py` dùng lại (giữ `_MODULES_FILE` cho test).
- `orchestration/packs/__init__.py`: `enabled_ids()`, `load_enabled()`, `load_enabled_jobs()`. Hợp đồng pack: `ASSETS`, `NIGHTLY_ASSETS` (`__init__.py`), `JOBS`, `SCHEDULES`, `SENSORS` (`jobs.py`). `crm`: 14 asset, `NIGHTLY_ASSETS` = 11 export + `crm_cache_refresh`, `crm_backup_job`/`crm_backup_schedule`. `sales_playbook`: `approach_script_autogen`. `hug`, `finance`: package tối thiểu với list rỗng + README (không có code Dagster; ingestion hug là connector) để `packs:` khớp phía dbt.
- `definitions.py`: không import CRM theo tên; nạp pack qua loader; job nightly/full refresh chọn `NIGHTLY_ASSETS` của pack thay cho `groups("crm_writeback") | crm_cache_refresh | approach_script_autogen` (tập asset phân giải giống hệt; Dagster inventory 0 khác biệt, kể cả tags và dbt unique_ids của mọi job).
- `modules.yaml`: `packs: [crm, hug, finance, sales_playbook]`, `tenants: [fine_japan]`.
- 4 connector `jobs.py`: `from orchestration.packs.crm import crm_sync` (giữ import theo quyết định user, allowlist).
- `orchestration/tenants/__init__.py`: `setting(name)`: env cùng tên thắng khi được đặt (kể cả rỗng, đúng hành vi `os.environ.get(name, default)`), nếu không thì `config.py` của tenant bật; không có thì `TenantConfigError` (nêu tên biến và tenant bật). Test `orchestration/tenants/__tests__/test_tenant_setting.py`: giá trị từ config, env ghi đè, bỏ một biến → lỗi, không tenant → lỗi, tenant lạ → lỗi. Test `orchestration/packs/__tests__/test_pack_registry.py`: loader, hợp đồng, tên asset/job của crm.

### Giá trị cứng đã dời sang `orchestration/tenants/fine_japan/config.py` (cùng giá trị)

| Tên | Trước | Đọc lúc |
|---|---|---|
| `SHEETS_SENSOR_TARGETS_URL`, `SHEETS_SENSOR_MARKETING_URL`, `SHEETS_SENSOR_US_SHIPMENT_PRICES_URL` | `sensors/sheets_modified_sensor.py:45-66` | Mỗi tick sensor (`sheet_urls()`): thiếu thì tick lỗi, code location vẫn load |
| `CRM_REFRESH_URL` (`http://crm:8090/admin/refresh`), `CRM_BACKUP_URL` (`.../admin/backup`), `CRM_DRILL_URL` (`http://crm_drill_runner:9000/run-drill`) | `assets/crm_sync.py` | Khi asset chạy |
| `APPROACH_SCRIPT_LOAD_URL` (`http://crm:8090/admin/approach-scripts/load`) | `assets/approach_script_generation.py` | Khi asset chạy |

Các URL CRM là địa chỉ container trong mạng docker của deployment, không hẳn là "dữ liệu Fine Japan", nhưng luật `pack-url` cấm URL trong pack nên phải ra cấu hình tenant. Hệ quả hành vi: chỉ khi thiếu cả env lẫn config (`crm_cache_refresh` vốn fire-and-forget nay sẽ đỏ run nếu cấu hình thiếu, đúng tinh thần fail closed). Prod không đặt các env này (`.env.docker.example` để comment) nên dùng giá trị config, giống hệt mặc định cũ. Giữ nguyên trong code: token, timeout, `CRM_DB_PATH`, `DBT_DATA_LAKE_PATH` (không phải URL/giá trị doanh nghiệp). `approach_script_generation.py` lấy `PROJECT_ROOT` từ `orchestration.assets.utils` (cùng giá trị `/app`) thay vì tính theo `__file__`.

Domain Sapo, `login_url`, worker URL ở `ingestion/.dlt/config.toml` giữ nguyên (quyết định user), ghi trong `orchestration/tenants/fine_japan/README.md`. Code hug orchestration (connector) không có giá trị cứng (luật URL/domain sạch).

## 5. CRM đọc gì (đã đọc `crm/sync/` và `crm/src/adapters/outbound/`)

CRM mở `serving/olap.duckdb` read-only (`crm/sync/config.py` `CRM_OLAP_PATH`, `crm/src/adapters/outbound/duckdb/connection.py`) và đọc theo tên relation (`main_marts.<tên>` trong `duckdb_reader.py`, tên trần trong `order_sql.py`...). Bảng đọc: lõi `dim_customers`, `dim_products`, `dim_staff`, `dim_channels`, `dim_payment_methods`, `dim_branch_location`, `dim_date`, `dim_time`, `dim_geography`, `dim_promotions`, `dim_teams`, `fact_orders`, `fact_sales`, `fact_payments`, `fact_fulfillments`, `fact_order_returns`, `mart_customer_tier`, `mart_product_health`, `mart_deadstock_target_queue`, `mart_customer_status_snapshot_monthly`, `mart_data_quality`; **dời trong phase này**: `fact_order_costs`, `fact_order_economics`, `int_order_cogs_reconciled`, `int_order_promo_goods_cost` (finance), `mart_customer_action_queue`, `mart_customer_sku_action_queue`, `dim_action_scenario_registry` (sales_playbook), `mart_hug_optin` (hug), `fact_us_shipment_economics` (tenant). Tên relation, schema, materialization không đổi (dbt inventory 0 khác biệt), serving builder lấy tên từ manifest nên CRM đọc được như cũ. Đề nghị smoke test CRM trên shadow/sau deploy như phase file yêu cầu.

## 6. Tài liệu

- Mới: `transformation/models/packs/{crm,hug,finance,sales_playbook}/README.md`, `transformation/models/tenants/fine_japan/README.md`, `orchestration/packs/README.md` (hợp đồng, tiếng Anh như `connectors/README.md`), `orchestration/packs/{crm,hug,finance,sales_playbook}/README.md`, `orchestration/tenants/fine_japan/README.md`. README pack/tenant viết tiếng Việt; hug mở đầu bằng định nghĩa được giao; sales_playbook ghi "thử nghiệm, chưa chuẩn hoá".
- `docs/architecture/modules.md`: bảng trạng thái, §1, §2 (quyền ghi `crm_export`, seed tenant), §2b (bố cục mới), §3 (ma trận có pack hook/pack → pack, số model, 33 vi phạm, quyết định 14/10 về COGS thay quyết định 13/10), §4, §5 (hug, cấu hình Sapo), §7, §8 (viết lại), §9, §10 (viết lại, hook sinh từ manifest, logic hook CROSSBORDER), §11 (CRM đọc serving theo tên), §12. Sửa số đếm cũ sai: 182 model (172 bật + 10 tắt), không phải "172 kể cả 10 tắt".
- `scripts/checks/README.md` (luật mới, số mục allowlist, test), `orchestration/connectors/README.md`, `orchestration/README.md`, `transformation/AGENTS.md`, `transformation/docs/TAXONOMY.md` (bảng vị trí 11 chỗ, seed tenant đã dời, ghi logic hook ở dòng `CTN00014` mục 6; hash không đổi), `scripts/checks/taxonomy_inventory.yaml` (10 đường dẫn).
- Đường dẫn file đã dời trong tài liệu sống: `docs/analytics-handbook/**` (12 file), `docs/architecture/order-pl/overhead-allocation-worked-example.md`, `docs/operations/backup-restore-completeness-runbook.md`, `orchestration/docs/{ASSETS,JOBS,SCHEDULES}.md`, `docs/README.md`, `docs/analytics-handbook/AGENTS.md`, `crm/docs/ui-spec/panels/P07-*.md`, comment trong `crm/src/tests/helpers_action_queue_fixtures.py`, `scripts/ensure_crm_export_placeholder.py`, docstring `ingestion/src/gsheet_budget_sync/__init__.py`. Không sửa bản ghi lịch sử: `docs/journals/`, `docs/project-changelog.md`, `.skills/**/lessons-learned.md`, `crm/docs/ui-spec/notes/`.

## 7. Kiểm tra đã chạy

```text
dbt parse (shadow, run-shadow.sh ... dbt parse)         OK
dbt_inventory diff dbt-main.json vs nhánh               186 vs 186 nodes, 0 difference(s)
dagster_inventory export / diff dagster-main.json       254 assets, 502 checks, 21 jobs, 17 schedules, 9 sensors; 0 difference(s)
check_boundaries.py --manifest <manifest nhánh>         33 known (dbt-ref 16, dbt-source 12, orch-import 5), 0 new, 0 stale
check_taxonomy_inventory.py --repo fg-dw-modular       79 blocks, 46 domains, 0 warning(s)
pytest-shadow ingestion/tests orchestration scripts/tests   237 passed (26 test mới/liên quan đều PASS)
sha256 45 .sql + 6 .csv trước/sau                      giống hệt
```

Lake tạm `lake-p6test` (pytest) và hai file inventory tạm đã xoá. `git status`: 44 sửa, 62 xoá (nửa cũ của các file dời), 23 mục mới (thư mục/file).

## 8. Lệch so với brief

- Allowlist có thêm 3 cạnh `sales_playbook → crm`, 12 `dbt-source`, 1 `orch-import` pack → pack (không có trong brief, sinh từ manifest/import).
- `pack_connectors` thêm `hug: [hug]` thay vì allowlist cho `stg_hug_* → src_hug_*`.
- Endpoint CRM và nơi nạp approach script cũng ra tenant config (bắt buộc bởi luật `pack-url`).
- Ba comment trong SQL (`int_crm_outreach_effort_events.sql:209`, `mart_staff_performance_weekly.sql:139` nhắc `orchestration/assets/crm_writeback_assets.py`; `dim_action_scenario_registry` có tag `crm_sync`) **để nguyên**: sửa comment SQL đổi checksum và vi phạm "không sửa SQL". Tag giữ nguyên là đúng.
- Phase file ghi `stg_crm__*` (10); brief tách thành 9 (crm) + `stg_crm__hug_voucher` (hug). Làm theo brief.

## 9. Chưa giải quyết / cần user

1. "Grep lại các model chi phí khác trong core/": không còn model nào trong core mang tên chi phí/lợi nhuận. Các chỗ còn đụng giá vốn trong core, **không dời** (không có trong danh sách, cần user quyết nếu muốn): `mart_customer_tier` đọc `lifetime_contribution_margin` từ `dim_customers` (gián tiếp qua hook finance); `fact_inventory_movements.cogs_amount` (giá trị xuất kho theo MAC, thuộc tồn kho); `dim_price_lists`, `fact_variant_prices_snapshot` (bảng giá nhập `is_cost`); `dim_sku_alias` (hook MISA có sẵn).
2. Ba seed tenant được lõi đọc (`seed_channel_targets` → `dim_channel_targets`, `seed_sku_alias_manual` → `dim_sku_alias`, `seed_sku_regimen_config` → `int_customer_sku_supply_tracking`). Seed không có bucket nên checker không thấy; ghi ở modules.md §3/§7 và TAXONOMY.md. Có thể cần luật "core không đọc seed tenant" sau Đợt 1.
3. URL Google Sheet mặc định trong các reader `ingestion/src/gsheet_*.py` vẫn là giá trị Fine Japan viết cứng (ngoài phạm vi quyết định 14/10, đã ghi trong README tenant).
4. Quyết định 5 trong phase file ("bỏ cách xử lý mặc định: không còn") chưa rõ nghĩa; bản làm này hiểu là code chung không còn giá trị mặc định cho giá trị tenant (fail closed).
5. Chưa chạy `gate.sh M` (golden 83/83, compiled SQL, lake rỗng) và chưa smoke test CRM; coordinator chạy.

Status: DONE_WITH_CONCERNS
Summary: Đã dời 45 model, 6 seed và code CRM/approach sang pack/tenant, nạp pack qua modules.yaml, chuyển URL sang tenant config fail-closed, thêm luật orch-import/pack-url có test và sinh lại allowlist 33 mục; inventory dbt/Dagster 0 khác biệt, boundaries/taxonomy/pytest sạch.
Concerns/Blockers: Gate M đầy đủ chưa chạy; xem mục 9 cho các điểm cần user quyết.

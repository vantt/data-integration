# Audit toolchain report skills (Metabase / Analytics Design / Evidence / Debug)

> Ngày: 2026-10-14 · Phạm vi: `.skills/analytics-design`, `.skills/metabase-automation`, `.skills/evidence-automation`, `.skills/debug-metabase`, `.claude/commands/` (wrapper báo cáo), phần report-related của `.skills/data-pipeline`.
> Phương pháp: đọc đầy đủ SKILL.md, STRATEGY.md, evidence/debug SKILL, toàn bộ wrapper; đọc headings + grep có số dòng cho các tài liệu tham chiếu lớn và thân script (xem Concerns). Không gọi Metabase, không đọc `.env*`, không sửa file nào khác.

## 1. Tóm tắt

- Toolchain hiện là **pipeline 2 skill**: Analytics Design (Phase 0-6, tool-agnostic, ra Design Spec) → Metabase Automation (Phase 7-10, ra blueprint `.md` và deploy qua API). Evidence là đường thứ hai, viết page tay, không có script.
- **Phần tái sử dụng cao**: phương pháp thiết kế (archetype, card role, viz vocabulary 25 term, visual language, comparative framing), `MetabaseClient` và `lib/resources/*`, cơ chế parse/deploy blueprint, và kiến trúc hai DuckDB context của Evidence.
- **Tenant-hardcoded**: tên DB mặc định `"Sapo"`, enum scope `scope_sales/scope_retail/scope_b2b/filter_us` cùng nhãn `[Retail]/[B2B]/[Cross]/[US]`, `field_id` số cố định (324, 141/848, 287, 773, 758), tên bảng `int_misa_sales_lines`, `int_shopee_order_fees`, `fact_us_shipment_economics`, mã kênh `SHOPEE_VN`, quy tắc VAT `/1.08`, hostname `*.lan.fwg.vn`, và danh sách dashboard/page cụ thể.
- **Thiếu cho report factory**: không có tenant profile, không có metric/dimension registry canonical độc lập tool, không có schema validate Design Spec, không có capability matrix theo engine, không có renderer Rill, không có test cho script deploy.
- **Mâu thuẫn tài liệu** cần xử lý trước khi chuẩn hóa (mục 5): trạng thái "Workflow C / không có design-spec layer" vs artifact ownership bắt buộc; `field_id` cho `ordered_at` là 141 hay 848; đường dẫn blueprint có hay không subfolder `{tool}`.

## 2. Inventory theo skill

### 2.1 `.skills/analytics-design/` (Analyst brain)

- **Mục đích**: thiết kế analytics artifact: domain (metric definitions), playbook (audience/purpose/Action Triggers), guide (tùy chọn), Design Spec.
- **Phase**: 0 Domain Modeling → 1 Playbook → 2 Guide (tùy chọn) → 3 Design Brief → 4 Composition (card role, narrative, spatial, view, filter) → 5 Visualization (25 term + decision tree) → 6 Enrichment (comparative framing, visual language, Dashboard Finish Checklist). Định nghĩa trong `SKILL.md` (mục Phase 0-6 Process).
- **Input**: request của user + domain có sẵn. **Output**: `docs/analytics-handbook/domains/*.md` (7 file), `playbooks/*.md` (22), `designs/*.md` (22), `guides/*.md` (9).
- **Deploy**: không có. Handoff sang Metabase Automation qua Design Spec. Field `**Tool:** metabase|evidence` bắt buộc trong playbook (`SKILL.md`, Phase 1 bước 4).
- **File tài liệu**: `DOMAIN_MODELING.md` (306 dòng), `COMPOSITION_PATTERNS.md` (311), `VISUALIZATION_VOCABULARY.md` (379), `VISUAL_LANGUAGE.md` (442), `COMPARATIVE_FRAMING.md` (79). Templates: `templates/{domain,playbook,guide,design_spec}_template.md`.

Tenant-specific assumptions:

| Vị trí | Nội dung | Ghi chú |
|---|---|---|
| `SKILL.md:12` | Ghi "Workflow C (no design-spec intermediate layer)", trái với Artifact Ownership (`SKILL.md:80`) bắt buộc Design Spec | Mâu thuẫn, xem mục 5 |
| `SKILL.md:205` | "3 tools deployed: metabase (bi.lan.fwg.vn), rill (rill.lan.fwg.vn), evidence (planned)" | Hostname nội bộ |
| `SKILL.md:205-226` | Tool selection: "mart parquet < 250MB", "Executive Pulse → evidence" | Ngưỡng theo hạ tầng hiện tại |
| `DOMAIN_MODELING.md:49` | Ví dụ context "Revenue Quality" dùng `fact_orders.net_revenue` | Tên bảng tenant |
| `DOMAIN_MODELING.md:111,131` | `dbt Source: marts.sales.fact_orders` (schema dbt khác với `main_marts.*` trong Evidence) | Hai quy ước tên không khớp |
| `domain_template.md:13`, `playbook_template.md:32` | Ví dụ `fact_orders`, `dim_channels` | Template dùng ví dụ tenant |
| `VISUAL_LANGUAGE.md:277,320,373,394` | Đơn vị "VND", "M VND", ký hiệu ₫ | Locale hardcode |
| `COMPOSITION_PATTERNS.md:241,276` | "~80M VND/tuần", footer "Source: fact_orders" | Ví dụ tenant |
| `VISUALIZATION_VOCABULARY.md:15-17` | Bảng vocabulary chỉ có cột "Metabase Support"; không có cột Evidence/Rill | Thiếu capability matrix đa engine |

Reusability: **High** cho phương pháp và vocabulary (logic không nhắc BI tool cụ thể). **Medium** cho bộ tài liệu vì ví dụ và đơn vị đều là Fine Japan/VND.

### 2.2 `.skills/metabase-automation/` (Engineer brain)

- **Mục đích**: biến Design Spec thành Metabase resources (Collection, Model, Metric, Segment, Card, Dashboard + tabs, Filter, Text card, Pulse).
- **Phase 7-10**: định nghĩa đầy đủ chỉ có trong wrapper `.claude/commands/create-metabase-blueprint.md` (Step 2: Translation → Configuration → Blueprint Assembly → Deploy). `SKILL.md` và `STRATEGY.md` không định nghĩa lại phase; `STRATEGY.md §3` dùng bước 1-7 và "Pre-deploy Check (Phase 10)".
- **Input**: Design Spec (`docs/analytics-handbook/designs/`), `semantic/*.md` (segments, metrics, dimensions, rules, freshness, entities), `METABASE_VIZ_CATALOG.md`.
- **Output**: blueprint markdown (`docs/analytics-handbook/blueprints/metabase/*.md`, 45 file hiện có), hoặc JS config.
- **Deploy**: `scripts/deploy_from_markdown.js` (blueprint, chính), `scripts/deploy_from_config.js` (JS config). Đảo chiều: `capture_dashboard.js` (live → blueprint), `generate-design-spec-from-dashboard.js` (live → design spec draft, `status: draft-from-capture`).

Script inventory (`scripts/`, 11 file + `lib/`):

| File | Dòng | Vai trò | Tenant-coupled? |
|---|---|---|---|
| `metabase_client.js` | 58 | Facade: `connect`, `findDatabaseId`, `collection/card/dashboard/model/metric/segment/snippet/pulse/table` | Không |
| `lib/metabase_core.js` | — | HTTP client thấp tầng | Không |
| `lib/resources/*.js` (9 class) | — | CRUD có unarchive, `syncCards` (PUT tabs + dashcards một lần) | Không (chỉ cycle-indicator tiếng Việt, xem dưới) |
| `lib/markdown_parser.js`, `lib/text-card-helpers.js` | — | Parse block `metabase-viz/-pos/-filter`, text-id marker | Không |
| `deploy_from_markdown.js` | 590 | Deploy blueprint; match dashboard theo tên; field_id/field_id_map; lint SQL | **Có** (xem bảng) |
| `deploy_from_config.js` | 181 | Deploy JS config | Có (`Sapo` ở dòng 11) |
| `create_blueprint.js` | 231 | Scaffold blueprint; scope `TODO`; output `blueprints/<domain>_<purpose>.md` (dòng 8) | **Có** (enum scope dòng 50-52, 94, 98; `scope_TODO` dòng 136-186) |
| `capture_dashboard.js` | 663 | Live → blueprint (fresh/merge/positions-only) | Có (field_id giữ nguyên dòng 167, 425) |
| `validate-analytics-artifacts.js` | 247 | Lint blueprint: frontmatter, scope enum, raw `customer_type='RETAIL'` | **Có** (dòng 105, 143-147) |
| `validate-collections.js` | 244 | So live Metabase với `collection_registry.yml` | **Có** (SCOPE_RE dòng 25: `[All\|Retail\|B2B\|Cross\|US\|Internal]`; SKIP_NAMES có "Thùng rác") |
| `patch-dashcard-viz.js` | 61 | Patch viz settings qua env `PATCH_VIZ` | Không (default port 3001, dòng 7) |
| `migrate-segmentation-scope-to-semantic-contract.js` | 299 | Migration một lần: map scope, `shopee_service_fee`, `crossborder` (dòng 19, 24-26, 48) | **Có**, one-off, nên archive sau migrate |
| `usage_example.js` | 51 | Ví dụ, `fact_orders`, `ordered_at` (dòng 20, 28) | Có (ví dụ) |

Lưu ý: default `METABASE_URL` không thống nhất: 3000 (`capture_dashboard.js:35`, `generate-design-spec-from-dashboard.js:21`), 3001 (`patch-dashcard-viz.js:7`).

Tenant-specific assumptions chính:

| Vị trí | Nội dung |
|---|---|
| `deploy_from_markdown.js:256-259` | DB mặc định `config.database \|\| METABASE_DB_NAME \|\| "Sapo"` |
| `deploy_from_config.js:11`, `SKILL.md:188`, `manage-metabase-resources.md:35` | `database: "Sapo"` / `findDatabaseId("Sapo")` |
| `deploy_from_markdown.js:171-174`, `validate-analytics-artifacts.js:143-147` | Cảnh báo cứng khi SQL dùng `customer_type = 'RETAIL'` hoặc `WHOLESALE` |
| `STRATEGY.md:36,41,56` | Quy tắc: luôn dùng `scope_retail` / `scope_b2b` / `scope_sales` pre-computed (tên cột tenant) |
| `create_blueprint.js:94,98`, `blueprint_template.md` | Enum scope `scope_sales\|scope_retail\|scope_b2b\|filter_us\|none`; `scope_indicator` `[All]\|[Retail]\|[B2B]\|[Cross]\|[US]\|[Internal]` |
| `STRATEGY.md:133-138` | Bảng field_id: 324 = `int_misa_sales_lines.posting_date` (Finance, Channel P&L); 141 = `fact_orders.ordered_at` (US CrossBorder) |
| `blueprint_template.md:178-181` | `field_id_map` gồm `int_misa_sales_lines`, `int_shopee_order_fees` (287), `fact_orders` |
| `Dashboard.js:81,97-100`, `deploy_from_markdown.js:566-577` | Cảnh báo cycle-indicator tên tiếng Việt "Chu kỳ báo cáo" tại row=0 |
| `SKILL.md:188-195` (+ ví dụ dòng 70, 146) | `fact_orders`, `gmv` |
| `migrate-...js:48` | `shopee_service_fee`, `crossborder` |

Reusability: **lib + MetabaseClient = High**. **Deploy/lint scripts = Medium** (logic tốt, enum và DB name hardcode, cần đổi thành đọc từ profile). **Docs (SKILL, STRATEGY, blueprint_template, filter refs) = Low** (field_id, bảng, scope Fine Japan là nội dung chính).

Gaps quan sát được:
- `SKILL.md` không liệt kê `validate-*`, `patch-dashcard-viz.js`, `generate-design-spec-from-dashboard.js`, `migrate-*` (có trong `scripts/`).
- `STRATEGY.md:6` nói có `deploy_from_design_spec.js` sắp tới; file không tồn tại. Hiện chưa có translator Design Spec → blueprint nào ngoài làm tay.
- Dashboard identity là **tên** (`STRATEGY.md §5.3`): đổi tên = tạo dashboard mới. Với multi-tenant, tên dễ trùng giữa tenant.
- `field_id` là ID cố định theo instance Metabase; không tái lập được cho tenant mới.
- Không có test cho `deploy_from_markdown.js`, `markdown_parser.js`, `capture_dashboard.js` (không có file `*test*` trong `metabase-automation/`).

### 2.3 `.skills/evidence-automation/` (đường report tĩnh)

- **Mục đích**: sinh page Evidence.dev (`.md`) từ Design Spec hoặc Playbook. Đây là skill thuần hướng dẫn: không có script trong thư mục (`SKILL.md` là file duy nhất).
- **Input**: playbook/design spec; mart table trong `olap.duckdb`. **Output**: `evidence/pages/<slug>/index.md` + tab pages, `evidence/sources/datalake/*.sql`.
- **Deploy**: `docker compose restart evidence` (cp → sources → build → preview, `SKILL.md` phần Architecture). Không có API, không có bước deploy blueprint.
- **Phase**: không có phase; luồng "Adding a New Dashboard" 4 bước (`SKILL.md` gần cuối).
- **Kiến trúc**: hai DuckDB context (`olap.duckdb` ở `/app/var/data_lake/serving/` → parquet → WASM DuckDB), `SKILL.md:17-42`. Đây là phần **đáng giữ** cho mọi tenant.

Tenant-specific assumptions:

| Vị trí | Nội dung |
|---|---|
| `SKILL.md:42,50-56` | Schema `main_marts`; danh sách `.sql` cứng: `fact_orders`, `dim_customers`, `dim_channels`, `fact_targets`, `fact_order_economics`, `fact_order_returns` |
| `SKILL.md:169-175` | Múi giờ `Asia/Ho_Chi_Minh`, "timestamps are ICT", format `%d/%m %H:%M` |
| `SKILL.md:170` | Scope filter cứng `scope_sales AND is_active_order` |
| `SKILL.md:218-219` | Dashboard có sẵn `ceo-weekly-pulse`, `finance-cashflow` |
| `SKILL.md` (phần Blueprints, cuối file) | Blueprint tại `docs/analytics-handbook/blueprints/evidence/`, hiện 1 file (`finance_cashflow.md`) |
| `.claude/commands/deploy-evidence-page.md:18-19,25,33-34` | `scope_sales`, `evidence.lan.fwg.vn`, `localhost:3006` |
| `SKILL.md` (Format strings) | `fmt="#,##0"` cho VND, đơn vị cứng |

Reusability: **Medium**. Kiến trúc và quy tắc SSF format, component mapping, WoW pattern là generic. Source list, schema, timezone, scope, URL là config tenant.

### 2.4 `.skills/debug-metabase/` (Explain / Debug live card)

- **Mục đích**: giải thích giá trị card Metabase: summary → chọn card → deep-dive SQL + filter → đối chiếu blueprint contract (`SKILL.md` Bước 1-5).
- **Input**: URL/ID dashboard. **Output**: báo cáo markdown theo cấu trúc Bước 5; cache `.cache/metabase/dashboard-<id>.json` TTL 24h (`SKILL.md` phần Cache).
- **Script**: `scripts/metabase-dashboard-debugger.js` + `lib/dashboard-cache.js`. Không deploy.
- **Phase**: Bước 1-5 (không phải Phase 0-10).

Tenant-specific assumptions:

| Vị trí | Nội dung |
|---|---|
| `metabase-dashboard-debugger.js:19-20` | Ví dụ URL `bi.lan.fwg.vn/dashboard/43?scope=SHOPEE_VN` |
| `debug-metabase/SKILL.md:123` | Filter ví dụ `channel_code = 'SHOPEE_VN'` |
| `SKILL.md:141,150` | "date là ICT", `date_key` YYYYMMDD ICT |
| `SKILL.md:152` | scope map vào `channel_code`, `channel_brand`, `market` |
| `SKILL.md:153` | "US orders: net_revenue = 0, revenue thực ở `fact_us_shipment_economics`" |
| `SKILL.md:173-174` | Anti-pattern: `customer_type = 'RETAIL'`, `total_price / 1.08` (VAT 8%) |
| `SKILL.md:16,42,64`, `debugger:209` | Port 3001 và đọc `.env.docker` (xem Risks) |
| `SKILL.md` Bước 4 | Đường dẫn blueprint `docs/analytics-handbook/blueprints/` và contract `semantic/*.md` |

Reusability: **Medium**. Luồng Explain/Debug, cấu trúc báo cáo và kiểm tra contract compliance dùng được cho mọi tenant. Các bảng check (ICT, VAT, US shipment, channel_code) là tenant-specific.

### 2.5 Command wrappers (`.claude/commands/`)

| Wrapper | Trỏ tới | Ghi chú |
|---|---|---|
| `design-dashboard.md` | `analytics-design/SKILL.md` | Chỉ Phase 0-6, output Design Spec. Tốt. |
| `create-metabase-blueprint.md` | 2 skill | Định nghĩa Phase 7-10. **Output `blueprints/<name>.md` không có subfolder `metabase/`**, mâu thuẫn với `SKILL.md:80`. |
| `deploy-metabase-blueprint.md` | `deploy_from_markdown.js` | `localhost:3000` (dòng 27); prerequisite Metabase container |
| `capture-metabase-dashboard.md` | `capture_dashboard.js` | `bi.lan.fwg.vn` (dòng 12); `.env.docker` + port 3001 (dòng 16, 22) |
| `manage-metabase-resources.md` | `metabase_client.js` | `findDatabaseId("Sapo")` (dòng 35) |
| `setup-metabase-mcp.md` | `.skills/metabase-automation/SKILL.md` + `.agents/skills/setup_metabase_mcp/SKILL.md` | **File thứ hai không tồn tại** (`.agents/skills/` trống). |
| `debug-metabase.md` | `debug-metabase/SKILL.md` | Wrapper mỏng, tốt. |
| `deploy-evidence-page.md` | `evidence-automation/SKILL.md` | `scope_sales` (dòng 19), URL `fwg.vn` (dòng 25, 33-34) |

### 2.6 `.skills/data-pipeline/` (chỉ phần report-related)

- `SKILL.md:3`: description ghi "data-integration2 project", tên không khớp repo hiện tại.
- `SKILL.md:97`: ingest "Sapo 3-channel"; `SKILL.md:185` "Tenant seeds (budget, targets, SKU config)" trong `seeds/`.
- `SKILL.md:207-210`: `sapo_warehouse.duckdb` (dbt working DB), `serving/olap.duckdb` (Metabase đọc).
- `SKILL.md:249`: mart phải có `location="{{ get_rolling_location() }}"`, nếu không serving view bị drop.
- `references/serving-layer.md:33,126-150`: Metabase đọc `olap.duckdb`; view là Rolling Self-Refresh View; lock/coexist đã kiểm chứng.
- Plan liên quan (`../plan.md:36`): không đổi tên 76 serving view, 11 bảng Rill, và các bảng CRM/detailView/Evidence đang đọc. Đây là ràng buộc bắt buộc khi refactor report layer.

Reusability: **Low** cho ingest/model (Sapo-specific); **Medium** cho cơ chế serving (rolling snapshot, self-refresh view) vì đó là tầng report-agnostic.

## 3. Ma trận tái sử dụng

| Skill / thành phần | Rating | Lý do (evidence) |
|---|---|---|
| analytics-design: phương pháp + vocabulary | High | Logic không nhắc BI tool; `VISUALIZATION_VOCABULARY.md:15-17` là hợp đồng tool-agnostic |
| analytics-design: ví dụ + đơn vị VND | Medium | `COMPOSITION_PATTERNS.md:241`, `VISUAL_LANGUAGE.md:277,394`, `DOMAIN_MODELING.md:49,111` |
| metabase-automation: `MetabaseClient` + `lib/resources` | High | `metabase_client.js:12-58`, không hardcode tenant |
| metabase-automation: deploy/lint scripts | Medium | `deploy_from_markdown.js:256`, `:171-174`; `validate-collections.js:25` |
| metabase-automation: docs (STRATEGY, blueprint_template, filter refs) | Low | `STRATEGY.md:133-138`; `blueprint_template.md:178-181`; `filter-date-range-pattern.md:75-76` |
| metabase-automation: migrate-* | Low | one-off, `migrate-...js:19,24-26,48` |
| evidence-automation: kiến trúc 2 DuckDB + SSF format | Medium | `SKILL.md:17-42`; `SKILL.md` Format strings |
| evidence-automation: source list, schema, TZ, URL | Low | `SKILL.md:42,50-56,169-175`; `deploy-evidence-page.md:25` |
| debug-metabase: flow Explain/Debug + contract check | Medium | `debug-metabase/SKILL.md` Bước 1-5 |
| debug-metabase: check ICT/VAT/US/channel_code | Low | `SKILL.md:141,150-153,173-174` |
| Command wrappers | Medium | Cấu trúc tốt; chứa hostname, port, file thiếu (`setup-metabase-mcp.md`) |
| data-pipeline: serving-layer | Medium | `serving-layer.md:126-150` |
| data-pipeline: ingest/model | Low | `SKILL.md:97,185,207` |

## 4. Register tenant-specific assumptions (hợp nhất)

| # | Assumption | Vị trí chính | Hậu quả với tenant mới | Hướng chuẩn hóa |
|---|---|---|---|---|
| T1 | DB name `Sapo` | `deploy_from_markdown.js:256`, `deploy_from_config.js:11`, `manage-metabase-resources.md:35` | Deploy lỗi hoặc gắn nhầm DB | Đọc từ `tenant.outputs.metabase.database`; bỏ default |
| T2 | Scope enum `scope_sales/retail/b2b/filter_us` | `create_blueprint.js:94,98`, `validate-analytics-artifacts.js:105`, `STRATEGY.md:36` | Không có ý nghĩa cho tenant khác | Thay bằng canonical dimension registry của tenant; enum sinh từ profile |
| T3 | Nhãn `[Retail]/[B2B]/[Cross]/[US]/[Internal]` | `validate-collections.js:25`, `create_blueprint.js:98` | Sai khi tenant không có kênh đó | Sinh suffix từ tenant profile (persona/channel canonical) |
| T4 | `customer_type='RETAIL'` và `WHOLESALE` cảnh báo cứng | `deploy_from_markdown.js:171-174`, `validate-analytics-artifacts.js:143-147` | Cảnh báo sai với schema khác | Chuyển thành rule dữ liệu: "dùng canonical column X thay vì raw Y" |
| T5 | `field_id` số cố định (324, 141/848, 287, 773, 758) | `STRATEGY.md:137-138`, `filter-date-range-pattern.md:75-76`, `blueprint_template.md:178-181`, `filter-category-dropdown-pattern.md:104-107` | Không tái lập được; stale sau rename | Resolve field theo `(table, column)` tại deploy time qua metadata API |
| T6 | Bảng nguồn cụ thể (`int_misa_sales_lines`, `int_shopee_order_fees`, `fact_us_shipment_economics`, `fact_orders`, `dim_channels`) | filter refs, debug SKILL, Evidence SKILL | Blueprint/SQL không chạy | Metric layer trỏ về canonical model; SQL sinh từ metric, không viết tay |
| T7 | Mã kênh `SHOPEE_VN`, `channel_code/channel_brand/market` | `metabase-dashboard-debugger.js:19-20`, `debug SKILL:123,152` | Debug sai ngữ cảnh | Dựa vào canonical `channel_std` (tenant label → canonical) |
| T8 | VAT `/1.08`, "M VND", `fmt="#,##0"` | `debug SKILL:174`, `VISUAL_LANGUAGE.md:277,394` | Sai với tenant khác (VAT, currency) | Đưa vào locale/tax config tenant |
| T9 | Timezone `Asia/Ho_Chi_Minh`, "ICT" | `evidence SKILL:169-175`, `debug SKILL:141,150` | Sai nếu tenant ở múi giờ khác | `tenant.locale.timezone` |
| T10 | Host `*.lan.fwg.vn`, `localhost:3000/3001/3006` | `analytics-design/SKILL.md:205`, wrappers | Lộ hạ tầng nội bộ; port mâu thuẫn | Biến môi trường per tenant/output |
| T11 | Cycle-indicator "Chu kỳ báo cáo" | `Dashboard.js:81`, `deploy_from_markdown.js:566-577` | Tên tiếng Việt cố định | Config text per locale |
| T12 | Dashboard/page cụ thể (`ceo-weekly-pulse`, `finance-cashflow`, `shopee_channel_economics`, 22 design) | `evidence SKILL:218-219`, `designs/` | Ví dụ không áp dụng được | Đưa vào `tenants/<id>/reports/`, không để trong skill |
| T13 | Mart > 250MB, Evidence chọn theo archetype | `analytics-design/SKILL.md:209-226` | Ngưỡng hạ tầng riêng | Đưa vào renderer capability config |
| T14 | `shopee_service_fee`, `crossborder` trong migrate | `migrate-...js:24-26,48` | Script one-off | Archive sau migrate |

## 5. Mâu thuẫn và số liệu stale cần xử lý trước

1. **Design Spec có bắt buộc không?** `analytics-design/SKILL.md:12` nói "Workflow C (no design-spec intermediate layer)", nhưng `SKILL.md:80` và `manage-metabase-resources.md` (Step 1) yêu cầu Design Spec, và `STRATEGY.md:6` nói direct-deploy đang đến. Cần chốt một trạng thái.
2. **field_id của `fact_orders.ordered_at`**: `STRATEGY.md:138` ghi 141; `filter-date-range-pattern.md:76,78` ghi 848 sau v2 rename và cảnh báo 141 đã stale. Cùng một cột nhưng hai giá trị.
3. **Đường dẫn blueprint**: `SKILL.md:80`, `SKILL.md:12`, `deploy-metabase-blueprint.md` (`blueprints/metabase/`) vs `create-metabase-blueprint.md` (`blueprints/<name>.md`) và `create_blueprint.js:8` (`blueprints/<domain>_<purpose>.md`).
4. **Port Metabase**: default 3000 trong `SKILL.md` và `capture_dashboard.js:35`; 3001 trong `debug SKILL`, `patch-dashcard-viz.js:7`, `debugger:209`; `localhost:3000` trong `deploy-metabase-blueprint.md:27`.
5. **Rill**: `analytics-design/SKILL.md:205` ghi "rill deployed", có `blueprints/rill/*.yaml` (4 file), nhưng **không có skill automation Rill** trong `.skills/`.
6. **`setup-metabase-mcp.md`** trỏ tới `.agents/skills/setup_metabase_mcp/SKILL.md`, file không tồn tại; bản có thật là `.skills/setup-metabase-mcp/SKILL.md`.
7. **Phase 7-10** chỉ được định nghĩa trong wrapper, không ở `metabase-automation/SKILL.md`.
8. **Mapping filter**: `METABASE_VIZ_CATALOG.md §6` map `date/range → date/all-options` với `{{date_filter}}`; `filter-date-range-pattern.md` yêu cầu `field_id` để là dimension filter. Hai tài liệu không cùng quy ước.
9. **`DOMAIN_MODELING.md:111,131,137`**: `marts.sales.fact_orders` (path dbt) trong khi phần còn lại dùng `fact_orders`; Evidence dùng `main_marts.*`. Ba quy ước tên.
10. **Debug loader env**: `metabase-dashboard-debugger.js:52-57` đọc `path.join(__dirname, '../../.env.docker')`, tức `.skills/.env.docker`; còn `debug SKILL` và wrapper đọc `.env.docker` ở root (qua `grep` trong shell). Hai vị trí khác nhau. Không mở file (đúng quy tắc).
11. **data-pipeline `SKILL.md:3`**: "data-integration2 project" không khớp tên repo hiện tại.

## 6. Đề xuất: report factory toolchain

### 6.1 Nguyên tắc
- **Tenant = profile + data + config**; logic nằm trong pack/core. Khớp quyết định 14/10 trong `plan.md:80`: "Logic là pack, dữ liệu/cấu hình là tenant. Lõi giữ doanh thu; pack finance giữ chi phí và lợi nhuận."
- **Report template tool-agnostic** (Design Spec v2, có schema) → **renderer per engine** (Metabase, Evidence, Rill). Không nhúng SQL engine cụ thể vào template.
- **Standard report chỉ group theo canonical value** (`*_std`); nhãn gốc của tenant chỉ dùng ở tầng mapping.
- **Identity bằng `spec_id`** (lưu trong description/tag của Metabase), không bằng tên dashboard.
- **Không đổi tên public view/bảng** đang được đọc (`plan.md:36`).

### 6.2 Tenant profile (đề xuất, ví dụ)

```yaml
# tenants/<tenant_id>/profile.yaml  (đề xuất)
tenant_id: fine_japan
locale: {timezone: Asia/Ho_Chi_Minh, currency: VND, tax: {vat_rate: 0.08}}  # giá trị ví dụ
connectors: [sapo, misa, shopee]          # từ registry connector
packs: [core, finance, crm, hug]          # core bắt buộc; pack là logic
personas: [ceo, sales_ops, finance]
taxonomy:
  channel: {tenant_label_field: "...", canonical: channel_std}
metric_overrides: {}                       # chỉ ghi chỗ khác pack mặc định
outputs:                                   # đích deploy; secret đi qua env, không nằm trong repo
  metabase: {database: "<name>", collection_root: "<tenant>"}
  evidence: {schema: main_marts}
  rill: {...}
```

### 6.3 Report template (Design Spec v2, đề xuất)
Frontmatter: `spec_id`, `requires_packs`, `persona`, `archetype`, `metrics` (id từ metric registry), `dimensions` (chỉ canonical), `filters` (khai báo theo dimension, không field_id), `cards` (role, viz term từ `VISUALIZATION_VOCABULARY`, size token), `comparisons`. Body: narrative, action map.

### 6.4 Renderer contract
- `render(spec, profile, engine) → artifacts`.
- Capability matrix: mỗi viz term × engine (`supported | fallback(<term>) | unsupported`). Hiện có cho Metabase (`METABASE_VIZ_CATALOG.md §1`) và ghi chú Evidence (`SKILL.md` Tool Feasibility Exception); chưa có cho Rill.
- Lỗi cứng khi: metric/dimension không có trong profile, pack chưa bật, canonical value thiếu trong mapping, viz không có fallback.

### 6.5 Flow
```
profile + spec  →  validate (schema, pack, canonical)  →  compile (metric → SQL qua model; field theo (table, column))
                →  render (metabase | evidence | rill)  →  lint  →  deploy --tenant X --engine Y (idempotent theo spec_id)
```
Output có lock/hash để biết artifact nào đã deploy cho tenant nào.

## 7. Nâng cấp theo từng skill

**analytics-design**
- A1. Chốt trạng thái Design Spec (sửa `SKILL.md:12`), thêm JSON/YAML schema cho frontmatter Design Spec v2.
- A2. Đưa ví dụ tenant-specific (fact_orders, VND, scope) ra `tenants/<id>/examples/`; giữ skill chỉ có pattern tổng quát.
- A3. Thêm cột Evidence và Rill vào `VISUALIZATION_VOCABULARY.md` (hoặc file capability matrix riêng).
- A4. Thống nhất quy ước tên bảng (`marts.*` vs `main_marts.*` vs canonical) trong `DOMAIN_MODELING.md`.
- A5. Tách bảng "Tool Selection" khỏi skill vào config (ngưỡng 250MB, rule archetype → tool).

**metabase-automation**
- M1. Thay `"Sapo"` bằng `tenant.outputs.metabase.database` (T1), xóa default.
- M2. Sinh enum scope và suffix nhãn từ profile (T2, T3); `validate-*` đọc profile thay vì regex cứng.
- M3. Field resolution theo `(table, column)` qua metadata API tại deploy (T5); bỏ `field_id` số trong blueprint.
- M4. Dashboard identity theo `spec_id` (tag/description), không theo tên.
- M5. Chuyển cảnh báo RETAIL/WHOLESALE thành rule dữ liệu (T4).
- M6. Viết `deploy_from_design_spec.js` theo `STRATEGY.md:6` hoặc bỏ dòng "forthcoming" nếu không làm; cập nhật danh sách script trong `SKILL.md`.
- M7. Thêm test: parser (`markdown_parser.js`), deploy idempotency (dry-run với mock client), lint rules. Hiện không có.
- M8. Archive `migrate-segmentation-scope-to-semantic-contract.js` sau khi xong migrate.
- M9. Thống nhất default port qua env `METABASE_URL` (không hard-code 3000/3001).

**evidence-automation**
- E1. Sinh source list (`sources/datalake/*.sql`) từ metric registry theo tenant (T6), không viết tay.
- E2. Đưa timezone, scope filter, URL, và `main_marts` schema vào config tenant (T9, T10, T12).
- E3. Viết generator, hoặc ghi rõ "manual" trong tên skill; hiện mô tả "Generate" nhưng không có script.
- E4. Ghi rõ quy ước `fmt` theo locale (VND).

**debug-metabase**
- D1. Đưa bảng check ICT/VAT/US/channel_code (T7, T8) thành rule theo profile.
- D2. Thống nhất vị trí đọc env (xem mục 5.10); không đọc file secret từ thư mục `.skills/`.
- D3. Giữ flow Bước 1-5, thay ví dụ `SHOPEE_VN` bằng ví dụ trung tính.

**Command wrappers**
- W1. `create-metabase-blueprint.md`: sửa đường dẫn output theo `blueprints/metabase/` (mục 5.3).
- W2. Sửa `setup-metabase-mcp.md` trỏ đúng `.skills/setup-metabase-mcp/SKILL.md`.
- W3. Bỏ hostname/port cứng; đọc từ env tenant.
- W4. Thêm wrapper mới cho factory: `render-report`, `deploy-report --tenant`.

**data-pipeline (report-facing)**
- P1. Sửa mô tả "data-integration2" (`SKILL.md:3`).
- P2. Ghi rõ contract tầng serving (tên view public) làm input cho report factory; không đổi tên (`plan.md:36`).

## 8. Gaps

- Không có **tenant profile** và **pack manifest** (chưa có chỗ khai báo connector/pack/persona).
- Không có **metric registry** canonical tool-agnostic (metric hiện nằm trong `docs/analytics-handbook/domains/*.md` dạng markdown, máy khó đọc đầy đủ).
- Không có **schema validate** cho Design Spec và blueprint (chỉ lint regex).
- Không có **capability matrix** cho Evidence và Rill.
- Không có **Rill renderer/skill** dù đã có blueprint YAML.
- Không có **test harness** cho deploy/parse.
- Không có **cơ chế deploy per tenant** (hiện một Metabase, một collection root, một DB `Sapo`).
- Không có **lock/hash** giữa Design Spec và artifact đã deploy (chỉ check ngày `last_modified`, `STRATEGY.md §3`, và chỉ cảnh báo).
- Tài liệu chỉ tiếng Việt; chưa có cơ chế locale cho tenant khác.

## 9. Liên hệ với plan hiện tại

- Đợt 1 (`plan.md`) là module hóa hạ tầng Fine Japan; report factory là việc **sau Đợt 1** hoặc phase riêng. Không đưa vào phase 06 ngoài việc tách profile Fine Japan.
- Phase 06 (`phase-06-fine-japan-tenant-overlay.md`) là nơi tự nhiên để đặt profile Fine Japan đầu tiên.
- Mọi thay đổi trong report layer phải giữ invariant: không đổi số trên dashboard và không đổi tên public view (`plan.md:36`).

---

## Status
DONE_WITH_CONCERNS

## Summary
Đã kiểm kê 4 skill báo cáo, wrapper, và phần report của data-pipeline. Tái sử dụng cao ở phương pháp thiết kế, `MetabaseClient`, và kiến trúc serving; tenant-hardcoded ở DB name `Sapo`, enum scope, `field_id` số, tên bảng, múi giờ, VAT, và hostname. Đề xuất report factory dựa trên tenant profile, Design Spec v2 tool-agnostic, và renderer per engine, kèm các bước nâng cấp theo skill và 11 mâu thuẫn tài liệu cần chốt trước.

## Concerns
- Phạm vi đọc: đọc đầy đủ SKILL.md, STRATEGY.md, evidence/debug SKILL, toàn bộ wrapper; `VISUAL_LANGUAGE.md`, `COMPOSITION_PATTERNS.md`, `DOMAIN_MODELING.md`, `VISUALIZATION_VOCABULARY.md`, `COMPARATIVE_FRAMING.md`, `METABASE_VIZ_CATALOG.md` và thân script (`deploy_from_markdown.js`, `capture_dashboard.js`, `lib/*`) được đọc qua headings + grep có số dòng, chưa đọc từng dòng. Có thể còn tenant assumption ngoài các dòng đã grep.
- Số dòng trích dẫn lấy từ grep tại thời điểm audit; kiểm lại nếu file thay đổi.
- `debug-metabase` có hàm đọc `.env.docker`; chỉ đọc code, không mở file env. Đường dẫn trong code khác với hướng dẫn trong SKILL. Nên xác minh trước khi chuẩn hóa.
- Không gọi Metabase, không chạy script, không sửa file ngoài báo cáo này.
- Các đề xuất ở mục 6-7 là đề xuất thiết kế, chưa được user chốt; đặc biệt T5 (resolve field theo metadata) và M4 (identity theo `spec_id`) cần kiểm chứng với API Metabase trước khi áp dụng.

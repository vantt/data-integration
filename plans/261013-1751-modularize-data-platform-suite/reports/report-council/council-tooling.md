---
title: "Hội đồng phản biện — vai trò report tooling engineer"
reviewer: council-tooling
date: 2026-10-14
design_under_review: ../../report-product-design.md (draft v1)
method: đọc code read-only; không gọi Metabase, không gọi mạng, không đọc file env
---

# Phản biện từ góc công cụ (skills + scripts)

## 0. Kết luận

- **Khả thi, nhưng chưa thể "dùng script hiện có".** Phần dùng lại được thật là tầng gọi API Metabase (`MetabaseClient`, `lib/resources/*`, `Dashboard.syncCards`). Tầng này đã chạy được trên 0.62.3: commit `b261687e` (10/07/2026) deploy dashboard 147 bằng `deploy_from_markdown.js` sau khi bump lên 0.62.3 (`e3cf2248`, 07/07). **Bộ biên dịch metric → SQL chưa có dòng code nào.** `deploy_from_design_spec.js` (`STRATEGY.md:6`) không tồn tại.
- **Có 2 lỗi trong deployer hiện tại phải sửa trước bước "cài song song" ở §7.** Nếu không sửa, chính thí điểm sẽ ghi đè dashboard Fine Japan đang dùng (mục 2.2, lỗi D1 và D2).
- **Thiết kế bỏ sót plan cũ** `plans/260528-1325-tool-agnostic-design-spec/`. Plan này đã khoá 8 quyết định (D1–D8) cho đúng bài toán spec v2 → deployer. Nó đang ở trạng thái "deferred" (`analytics-design/SKILL.md:12`). Thiết kế mới cần ghi rõ là thay thế plan này hay kế thừa nó, nhất là D4 (`spec_version`), D6 (bảng portability), D7 (JSON Schema).
- Evidence: **đề xuất không đưa vào sản phẩm.** Ghim phiên bản ngay và đóng băng như bản phản chiếu của FJ (mục 3). Rill: sinh measures từ registry là khả thi, nhưng để sau Metabase (mục 4).
- Đường nhanh nhất tới thí điểm Weekly Pulse: **~9–11 ngày công**, không chờ registry đầy đủ hay `*_std` (mục 5).

## 1. Đã đọc (bằng chứng)

`metabase-automation/` gồm `deploy_from_markdown.js` (590 dòng), `lib/markdown_parser.js`, `lib/metabase_core.js`, `lib/resources/{Dashboard,Card,Collection,Table,Model,Metric}.js`, `lib/text-card-helpers.js`, `STRATEGY.md`, cùng phần đầu của `generate-design-spec-from-dashboard.js`. Ngoài ra: `debug-metabase/` (script và SKILL Bước 4), `evidence/` (package.json, Dockerfile.evidence, 4 trang, sources), `rill/` (metrics, dashboards, models, rill.yaml), blueprint `ceo_weekly_pulse.md` (1409 dòng) và `finance_cashflow.md`, design `ceo_weekly_pulse.md`, `semantic/metrics.md`, `transformation/models/core/marts/sales/_core__models.yml`, và plan 260528.

Phát hiện ngoài thiết kế:
- **Không có cột `*_std` nào** trong `transformation/models/` (grep không ra kết quả). Chiều chuẩn mà spec v2 dựa vào hiện chưa tồn tại.
- `fact_orders` là bảng fact theo star schema: chỉ có khoá (`channel_key`, `customer_key`…) và số đo. `channel_category` nằm ở `dim_channels`. Riêng Weekly Pulse có 9 JOIN `dim_channels` và 5 JOIN `dim_customers`. Vì vậy mô hình registry "mỗi metric một `model`" **không đủ**: cần khai báo đường join cho từng chiều.
- **Design spec Weekly Pulse đã lệch khỏi blueprint đang chạy.** Design ghi "báo cáo tuần trước trọn Mon–Sun" và lọc `channel_name != 'US'`. Blueprint dùng tuần-đến-hôm-nay và `scope_sales`, đồng thời có thêm khối Profitability, Forecast, Run-rate và danh sách đơn. Khi so số, **mốc so phải là blueprint đã deploy**, không phải design.
- Ngay trong blueprint: `Total Orders` không lọc `is_active_order`, trong khi Net/Gross Revenue có lọc. Registry phải giữ đúng khác biệt này, nếu không phép so số sẽ lệch.
- Viz `progress` của "MTD GMV vs Target" ghi cứng `goal = 600,000,000`. Đây là dữ liệu của khách nằm trong viz settings, nên phải chuyển thành tham số tenant.
- `linkTemplate: https://detailview.lan.fwg.vn/...` trong card danh sách đơn, cũng phải thành tham số tenant.

## 2. (a) Spec v2 → Metabase native query

### 2.1 Cái gì dùng lại được, cái gì phải viết mới

| Thành phần | Trạng thái | Việc phải làm |
|---|---|---|
| `MetabaseClient` + `lib/resources/{Collection,Card,Dashboard}` | Đã chạy trên 0.62.3 | Giữ. Sửa phạm vi tìm kiếm (D1, D2) |
| `Dashboard.syncCards` (tabs + dashcards trong một PUT) | Đã chạy | Giữ. Sửa lỗi nuốt lỗi (D3) |
| `markdown_parser.js` → object `{collections, dashboards[{questions{sql,viz,pos,tab}, filters, textCards}]}` | Đã chạy | **Dùng object này làm IR (dạng trung gian)**: renderer sinh đúng shape đó, không cần sinh file `.md` |
| `buildTemplateTags` + `resolveFieldId` | Chỉ nhận `field_id` số | Thêm `field_ref: {schema, table, column}`, tra lúc deploy (2.3) |
| `flattenViz`, `METABASE_VIZ_CATALOG.md` §5 (JSON template) | Có | Chuyển các JSON template thành bảng dữ liệu (viz term → JSON) mà renderer đọc được |
| Biên dịch metric + chiều + cửa sổ thời gian + so sánh → SQL | **Không có** | Viết mới (2.4) |
| `Metric.js` (`/api/metric`) | Legacy metric. Theo changelog Metabase 0.50 đã bị bỏ (chưa thử trên 0.62.3) | Không dùng. Ghi rõ là dead code |
| `Model.js` (`dataset: true`) | Từ 0.49 dùng `type: "model"`. Chưa rõ 0.62 còn nhận `dataset` không | Kiểm trên container tạm. Weekly Pulse không cần model |
| Parser frontmatter tự viết (`deploy_from_markdown.js:13`) | Không đọc được YAML lồng nhau | Spec/registry YAML cần `js-yaml` (hiện không có `package.json` cho skill) |

Seam đề xuất: tách `main()` của `deploy_from_markdown.js` thành `deployConfig(config, {client, dbId, dryRun, identity})`. Sau đó cả hai đường cùng gọi hàm này: blueprint cũ (`parseMarkdownConfig`) và spec v2 (`renderMetabase(spec, registry, profile)`). Như vậy 45 blueprint đang chạy không bị ảnh hưởng.

### 2.2 Lỗi trong deployer hiện tại (chặn thí điểm)

| # | Mức | Vị trí | Lỗi | Hậu quả với §7 "cài song song" |
|---|---|---|---|---|
| D1 | **Critical** | `Dashboard.js:9-12, 15-29` | `find(name)` tìm theo tên trên **toàn bộ** `GET /api/dashboard`. Nếu tìm thấy thì `PUT collection_id` để **dời dashboard sang collection mới**, rồi ghi đè cards | Cài Weekly Pulse chuẩn với tên trùng sẽ dời và ghi đè dashboard FJ đang dùng thay vì tạo bản song song |
| D2 | **High** | `deploy_from_markdown.js:404` → `Card.findActiveInCollection` | Card chưa nằm trên dashboard thì tìm theo **tên trong cả collection** rồi PUT SQL mới. Collection `Executive` chứa 3 dashboard: ví dụ `Total Orders` có ở 2 dashboard, `New Customers` và `Return Count` ở 3 | Lần deploy đầu của dashboard B có thể ghi SQL của B vào card của dashboard A. Card trùng tên khác tab cũng bị gộp làm một |
| D3 | High | `Dashboard.js` catch trong `syncCards`; `deploy_from_markdown.js` dòng cuối `main().catch(console.error)` | Lỗi PUT bị nuốt, script vẫn in "Deployment Complete" và **exit code 0** | Test tự động và CI không phát hiện được deploy hỏng |
| D4 | High | `metabase_core.js:8` | `rejectUnauthorized: false` áp cho **mọi** HTTPS | Khi deploy sang Metabase của khách qua mạng, API key có thể bị MITM. Phải đổi thành opt-in theo profile |
| D5 | Medium | `deploy_from_markdown.js:203-268` | `--dry-run` vẫn connect và tra DB. Chỉ in "Would ensure", không so với trạng thái thật | Chưa đạt yêu cầu "in kế hoạch thay đổi" của ⑦ |
| D6 | Medium | Không có khoá | Hai lần deploy chạy cùng lúc lên một instance sẽ tạo bản trùng (logic find-then-POST) | Cần khoá theo tenant (file lock cục bộ là đủ) |

### 2.3 Tra field theo `schema.bảng.cột` (Metabase 0.62)

- Gọi **một lần** `GET /api/database/:id/metadata` (trả về `tables[].{schema,name,fields[].{id,name}}`) rồi cache trong lần chạy. Không dùng `Table.find` hiện có: nó gọi `GET /api/table` toàn instance, khớp cả `display_name` và không lọc theo DB (`Table.js:14-22`), nên dễ khớp nhầm.
- Khoá là `(db_id, schema, table, column)`. Các serving view được tạo trong schema mặc định của `olap.duckdb` (`bootstrap_serving_views.py`). `main_marts` chỉ là tên source của Evidence, không phải schema DuckDB. Cần xác nhận tên schema Metabase thấy trên container tạm (dự kiến `main`).
- Thiếu field (view vừa thêm cột, như sự cố ở commit `b261687e`): gọi `POST /api/database/:id/sync_schema`, đợi, thử lại một lần, sau đó **fail cứng** và ghi rõ cột thiếu. Không được rơi về biến `text`, vì `buildTemplateTags` hiện lặng lẽ làm vậy.
- Template tag vẫn là `dimension: ["field", <id>, null]`. Id chỉ tồn tại trong payload lúc deploy, không nằm trong file nào.
- Weekly Pulse **không có filter dashboard** ("zero-interaction"), nên tra field **không nằm trên đường găng của thí điểm**. Tuy vậy 26/45 blueprint có dùng `field_id` (riêng `848` xuất hiện 9 lần), nên phase 5 bắt buộc phải có.

### 2.4 Bộ biên dịch: phạm vi tối thiểu theo Weekly Pulse (30 card)

| Loại card (`kind`) | Card Weekly Pulse | Sinh từ registry? |
|---|---|---|
| `kpi_compare` (giá trị + kỳ trước) | Net/Gross Revenue, Total Orders, AOV, Cancelled, Discount Rate, Net Profit, Gross Margin %, New/Returning Customers, Return Count | Có, nếu registry có metric `ratio` và `segment` theo từng metric |
| `trend` (chuỗi theo ngày) | Daily Net Revenue 14d, New vs Returning 14d | Có |
| `breakdown` / `breakdown_compare` | Revenue by Channel Category, Category WoW, Top Channels, Channel Perf Table | Có, cần chiều kèm đường join `fact_orders.channel_key → dim_channels` |
| `derived` (khác model: target) | MTD vs Target, Pace Index, Forecast, Run-rate | Được nếu registry có metric `derived` tham chiếu metric khác. Nếu không thì `custom_sql` |
| `custom_sql` | Đơn hàng tuần này (bảng chi tiết), Loss-Making Channel Count (aggregate lồng) | Không, giữ SQL và khai báo cột đầu ra |
| `meta` | Chu kỳ báo cáo ×3, Độ tươi dữ liệu ×3 | Template theo `cadence`, như `tab_standards` của plan 260528 |

Ước lượng: ~18 card sinh trực tiếp, 4 card `derived`, 2 card `custom_sql`, 6 card `meta`.

Cửa sổ thời gian tối thiểu cần hỗ trợ: `wtd`, `prev_wtd`, `mtd`, `last_n_days`. Registry phải có thêm `dimensions.yaml`, mỗi chiều gồm `{model, column, join}` (chỉ một bước join). Nếu thiếu, renderer phải tự đoán join, dẫn tới lỗi đếm trùng.

Ranh giới tin cậy: nhãn, ngưỡng và tham số từ overlay hay hồ sơ khách **chỉ được đi vào SQL dưới dạng literal đã escape**. Định danh bảng và cột phải nằm trong whitelist lấy từ metadata ở 2.3. Không được nối chuỗi tự do vào SQL.

### 2.5 Idempotency theo `spec_id`: lưu ở đâu

| Lựa chọn | Đánh giá |
|---|---|
| Tên dashboard/card (hiện tại) | Loại. Gây lỗi D1 và D2; tên có thể bị overlay đổi nhãn |
| `entity_id` | Loại làm khoá chính: do Metabase tự sinh và chỉ có giá trị trong instance đó. Chưa xác minh `POST /api/card` có nhận `entity_id` do client đặt hay không. Có thể ghi vào file khoá làm con trỏ phụ |
| **Marker trong `description`** | **Chọn.** Dùng cùng kỹ thuật `<!-- text-id:... -->` đã chạy cho text card (`text-card-helpers.js`). Card: `[[spec:ceo_weekly_pulse#net_revenue_wow]]`. Dashboard: `[[spec:ceo_weekly_pulse@1.0.0]]`. Text card giữ `text-id` |
| File trạng thái phía repo | Phụ: `tenants/<id>/deployed/metabase.lock.json` gồm `{catalog_version, registry_hash, spec_id → {dashboard_id, card_ids, entity_id}}`. Đáp ứng yêu cầu "ghi lại phiên bản đã cài" của ⑦. Khi lệch với marker trên server thì **marker thắng**, đồng thời in cảnh báo drift |

Thuật toán: liệt kê `GET /api/collection/:root/items` (đệ quy, chỉ trong collection gốc của tenant) và lập map `marker → object`. Sau đó: có marker thì PUT; không có thì POST; marker có trên server nhưng không có trong bản render thì **archive** (không xoá). Phải kiểm trên container tạm xem description có render dạng markdown không và marker có hiện ra cho người dùng không. Nếu có hiện, dùng dạng chữ nhỏ ở cuối thay vì comment HTML.

### 2.6 Dry-run hai mức

1. `--render-only` (offline, không mạng): in IR và SQL đã biên dịch ra stdout hoặc file. Dùng cho golden test trong CI.
2. `--plan` (chỉ đọc server): đọc trạng thái thật trong collection gốc và in diff `create | update(field đổi) | archive | noop`. Không gửi PUT hay POST nào. Thay cho `--dry-run` hiện tại.

### 2.7 Test trên Metabase tạm

- Image: build từ `Dockerfile.metabase`, đúng 0.62.3 và driver DuckDB 1.5.3.0. App DB dùng H2 mặc định, không mount volume, nên tự xoá khi container dừng.
- Port cố định (vd. 3101). Kiểm port trước khi chạy, dừng container trong `finally` theo `.claude/rules/process-management.md`.
- Khởi tạo: `GET /api/session/properties` lấy `setup-token` → `POST /api/setup` tạo admin → dùng session token. Thêm DB DuckDB trỏ tới **fixture nhỏ** (vài nghìn dòng tổng hợp, cùng schema với các view công khai). Không dùng `olap.duckdb` thật, vì view của nó trỏ tới parquet theo đường dẫn tuyệt đối.
- Các test:
  - Deploy 2 lần thì số object bằng nhau và id giữ nguyên.
  - Mỗi card chạy `POST /api/card/:id/query` không lỗi.
  - Kiểm `--plan` sau lần deploy thứ 2 trả "noop".
  - Archive card bị bỏ khỏi spec.
  - Roundtrip `dataset_query` (để phát hiện thay đổi format MBQL của 0.62).
- **So số không cần Metabase.** Chạy SQL đã biên dịch và SQL blueprint cũ trực tiếp bằng DuckDB trên cùng một bản chụp `olap.duckdb`, so từng card. Cách này nhanh hơn và chặt hơn. Container Metabase chỉ dùng để kiểm phần wiring.
- Runner: dùng `node --test` có sẵn (Node 24), không cần framework. Thời gian khởi động Metabase ~1–2 phút, nên chạy theo yêu cầu hoặc nightly, không chạy mỗi commit.

## 3. (b) Evidence: giữ hay chuyển

| Dữ kiện | Bằng chứng |
|---|---|
| Có **2 dashboard thật**: `ceo-weekly-pulse` (411 dòng), `finance-cashflow` (618 dòng). `theme-mvp` (678 dòng) là trang thử theme dùng **dữ liệu giả**. `index.md` là trang điều hướng | `evidence/pages/` |
| Cả 2 dashboard thật **đều đã có bản Metabase**: `blueprints/metabase/ceo_weekly_pulse.md`, `finance_cashflow.md`. Playbook cashflow ghi rõ "metabase (primary), evidence (offline/static mirror)" | `playbooks/finance_cashflow.md:11` |
| **Không ghim phiên bản**: 3 gói `"latest"`, **không có `package-lock.json`**. `Dockerfile.evidence` chạy `npm install` lúc build, nên mỗi lần `docker compose build` có thể kéo về một phiên bản khác | `evidence/package.json`, `Dockerfile.evidence` |
| Không có script deploy hay generator. Trang viết tay; "blueprint" Evidence chính là nội dung trang | `blueprints/evidence/README.md` |
| Thứ Evidence có mà Metabase thiếu: link tĩnh hoặc offline, Sankey và period picker trong cashflow. Metabase ≥0.53 có viz Sankey (cần xác minh trên 0.62.3) | `evidence-automation/SKILL.md` (Limitations), `finance-cashflow` |
| Weekly Pulse bản Evidence đã lệch nhỏ so với bản Metabase (gộp KPI vào một query, thiếu khối Profitability) | So sánh trực tiếp hai file |

Chi phí chuyển hẳn sang Metabase: **gần 0** cho nội dung, vì Metabase đã có cả hai dashboard. Chỉ mất Sankey (nếu 0.62 không có), giao diện tài liệu tĩnh và truy cập không cần đăng nhập. Ngược lại, chi phí giữ Evidence trong sản phẩm là một renderer thứ hai, một capability matrix, phép so số giữa hai engine, và rủi ro gói legacy (theo `external-references.md`, bản cuối 06/02/2026 và Evidence mới không có connector DuckDB file; điều này chưa được xác minh trong review này).

**Đề xuất:**
- Ghim phiên bản ngay: lấy đúng các version đang có trong image hiện tại (`npm ls` bên trong container, do người vận hành chạy), ghi version cụ thể vào `package.json` và commit `package-lock.json`. Dùng `npm ci` trong Dockerfile.
- Đóng băng Evidence như **bản phản chiếu riêng của FJ, nằm ngoài sản phẩm**. Catalog chỉ ghi `engines: [metabase]` (thêm `rill` nếu có).
- Chỉ mở lại khi có khách thật cần báo cáo tĩnh hoặc offline.

## 4. (c) Rill: sinh metrics view từ registry

**Khả thi cho `measures`, effort 2–3 ngày.** Map một-một: `id → name`, `label → display_name`, `description`, `expression`, `unit → format_preset`. Cả Rill và Metabase đều chạy DuckDB SQL, nên cùng một `expression` dùng được cho cả hai.

Những điểm phải xử lý trước khi sinh:
1. **Model khác nhau.** Rill dựng metrics view trên `orders_enriched` (SQL join sẵn trong `rill/models/`), đọc parquet export, không đọc `olap.duckdb`. Đường join khai báo trong `dimensions.yaml` (mục 2.4) có thể sinh luôn `orders_enriched.sql`. Nên làm vậy, vì một nguồn join sẽ giảm lệch số.
2. **Định nghĩa đang lệch nhau.** Rill có `orders_count = count(*)`, còn `metrics.md` và blueprint dùng `COUNT(DISTINCT order_id)`. Rill không áp scope vào measure. Registry phải chốt một định nghĩa, và `filters` của metric phải sinh thành `... filter (where ...)` trong measure Rill.
3. **Phạm vi:** chỉ sinh `measures` và danh sách `dimensions`. File `dashboards/*.yaml` (dạng `explore`, `measures: "*"`) giữ nguyên.
4. **Test:** chạy container Rill đã ghim `v0.87.8` để parse project sau khi sinh (lệnh validate cụ thể cần xác minh). Đồng thời so một golden query giữa Rill và DuckDB.
5. **Thứ tự:** sau thí điểm Metabase (phase 7 như thiết kế). Đây không phải đường găng.

## 5. (d) Đường nhanh nhất tới thí điểm Weekly Pulse

Nguyên tắc: **cắt dọc**. Chỉ làm phần registry, renderer và deployer mà Weekly Pulse cần, mốc so là blueprint đang deploy. Không chờ hợp nhất đủ 56 + 53 metric, cũng không chờ `*_std`.

| Bước | Việc | Ngày |
|---|---|---|
| 0 | Sửa D1–D4 trong deployer: tìm dashboard trong phạm vi collection gốc, bỏ fallback tìm card theo tên trong collection (thay bằng marker), sửa exit code và nuốt lỗi, TLS verify thành opt-in. Thêm test `node --test` cho parser | 1 |
| 1 | Registry lát mỏng: ~16 metric Weekly Pulse dùng (có `ratio`, `derived` target/pace), 3 chiều (`order_date`, `channel_category` kèm join, `customer_lifecycle`), segment `sales_orders` (bản FJ = `scope_sales AND is_active_order`, `Total Orders` riêng chỉ dùng `scope_sales`). Kèm JSON Schema và validator | 1.5 |
| 2 | Spec v2 `ceo_weekly_pulse` viết theo **blueprint đang chạy**, có `spec_version: 2` (kế thừa D4 của plan 260528). Tham số tenant: `progress_goal`, `detailview_url` | 1 |
| 3 | Renderer Metabase cho các `kind` ở 2.4, sinh IR đúng shape `markdown_parser` | 2.5 |
| 4 | Tách `deployConfig()`, identity bằng marker, `--render-only` và `--plan` | 1.5 |
| 5 | So số: chạy SQL biên dịch và SQL blueprint trên cùng bản chụp DuckDB, yêu cầu **0 lệch** ở cả 30 card. Thêm harness Metabase tạm cho idempotency | 2 |
| 6 | Deploy vào collection mới (vd. `Sản phẩm › Điều hành › Tuần`), tên có hậu tố để không trùng. Chạy song song 2 tuần với bản cũ | 0.5 |

Tổng cộng **~10 ngày công**. Cổng nghiệm thu: bước 5 không lệch, deploy lần 2 cho `--plan` = noop, và dashboard FJ cũ không đổi (`updated_at` của dashboard và card cũ giữ nguyên).

## 6. (e) Danh sách nâng cấp theo skill

| Skill | Việc | Effort | Ưu tiên |
|---|---|---|---|
| metabase-automation | D1–D6 (mục 2.2) | 1.5d | P0, trước thí điểm |
| | `deployConfig()` dùng chung cho blueprint và spec v2 | 1d | P0 |
| | `render_metabase.js` (metric → SQL, `kind`, cửa sổ thời gian, join) | 2.5–4d | P0 |
| | Tra field qua `/api/database/:id/metadata` cùng `sync_schema` | 1d | P1 (phase 5) |
| | Marker idempotency, file khoá phiên bản, archive orphan | 1d | P0 |
| | Harness Metabase tạm cùng `node --test` | 1.5d | P0 |
| | `package.json` riêng cho skill, ghim `js-yaml` và `ajv`, có lockfile | 0.25d | P0 |
| | Bỏ `"Sapo"` mặc định, đọc DB, URL và TLS từ hồ sơ khách (T1, T10) | 0.5d | P1 |
| | `validate-*` và `create_blueprint` đọc enum từ profile (T2, T3, T4) | 1d | P2 |
| | Đánh dấu `Metric.js` là legacy; archive `migrate-*`; viết lại `STRATEGY.md:6` | 0.25d | P2 |
| analytics-design | Template spec v2 cùng JSON Schema. Phase 4–5 chọn **metric id** từ registry thay vì viết SQL. Sửa mâu thuẫn "Workflow C" (`SKILL.md:12`) | 1.5d | P0 |
| | Cột engine trong `VISUALIZATION_VOCABULARY.md` (Metabase, Rill) | 0.5d | P2 |
| | Tách ví dụ FJ (VND, `fact_orders`, `scope_*`) sang tenant | 1d | P2 |
| debug-metabase | Bước 4 tra spec theo marker `spec:` trong description, rồi về metric registry, thay vì `grep` tên trong `blueprints/` | 0.5d | P1 (gãy khi dashboard sinh từ spec) |
| | Bỏ đọc `.skills/.env.docker` (`metabase-dashboard-debugger.js:51`), chỉ dùng env; port lấy từ profile | 0.25d | P1 |
| evidence-automation | Ghim phiên bản cùng `npm ci`; ghi "đóng băng, FJ-only" | 0.25d | P0 (vận hành) |
| Rill (chưa có skill) | `render_rill.js`: measures và `orders_enriched.sql` từ registry | 2–3d | P2 |
| Mới: registry validator | `scripts/checks/check_reporting_registry.py`: schema, `model` thuộc `public_models.yaml`, cột tồn tại trong dbt manifest, sinh `semantic/metrics.md` | 1.5d | P0 |

## 7. (f) Trả lời §9

**Quyết định 2 (Evidence):** đề xuất **chuyển hẳn sang Metabase cho sản phẩm.** Evidence ghim phiên bản ngay và đóng băng như bản phản chiếu của FJ, không viết renderer Evidence ở v1. Lý do:
- Cả 2 trang thật đã có bản Metabase.
- Không có generator nào để bảo trì.
- Gói legacy chưa ghim và không có lockfile.
- Mỗi engine thêm vào làm tăng gấp đôi chi phí so số.

Điều kiện mở lại: có khách cần báo cáo tĩnh hoặc offline, và Evidence có đường chạy DuckDB file đã được xác minh.

**Quyết định 3 (vị trí catalog/registry):** đề xuất **module code có schema kiểm tra, không đặt trong `docs/`.** Cụ thể:
- Một thư mục riêng (vd. `reporting/`) chứa `registry/{metrics,dimensions}.yaml`, `catalog/catalog.yaml`, `specs/*.yaml`, `schemas/*.schema.json`.
- Validator Python đặt trong `scripts/checks/`, theo mẫu `check_taxonomy_inventory.py`. `pyyaml` và `jsonschema` 4.19 đã có trong môi trường Python (kéo theo cùng dbt-core), nên không cần thêm phụ thuộc.
- `docs/analytics-handbook/semantic/metrics.md` trở thành file **sinh ra**.

Không chọn `docs/` vì ở đó không có cổng CI. Không chọn dbt `semantic_models`/`metrics` ở v1 vì: MetricFlow chưa chính thức hỗ trợ DuckDB (thiết kế §4①), metric dbt kéo theo yêu cầu time spine khi parse (cần xác minh với dbt 1.11), và lỗi registry khi đó sẽ chặn `dbt parse` của pipeline sản xuất. Giữ cú pháp gần MetricFlow để có đường lui là đủ. Hồ sơ khách và overlay nằm ngoài image, cùng chỗ với luật phân loại, như §4④.

## 8. (g) Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| D1 và D2 ghi đè dashboard FJ đang dùng khi cài song song | **Critical** | Bước 0 của mục 5 là điều kiện tiên quyết |
| Registry thành "semantic layer tự chế" vì phải gánh join, derived, cửa sổ thời gian | High | Giới hạn: join một bước, `derived` chỉ gồm phép số học trên metric. Phần còn lại dùng `custom_sql` đã đánh dấu |
| Lệch số do định nghĩa ngầm (`is_active_order`, `count(*)` so với distinct, MTD `< current_date`) | High | So số theo từng card trên bản chụp DuckDB, cổng 0 lệch |
| `*_std` và cơ chế pack chưa có. Spec v2 "chỉ dùng chiều chuẩn" sẽ bị chặn | High | Thí điểm dùng chiều hiện có qua `dimensions.yaml` và ánh xạ trong overlay FJ. Chuyển sang `*_std` khi có |
| Format API 0.62 (MBQL, `type: model`, markdown của description, Sankey) chưa được kiểm | Medium | Harness Metabase tạm chạy trước khi viết renderer |
| Marker trong description bị người dùng sửa hoặc xoá | Medium | Đối chiếu với file khoá; khi lệch thì `--plan` báo drift, không tự tạo bản trùng |
| Hai plan song song (260528 và thiết kế này) cùng định nghĩa spec v2 | Medium | Ghi trong plan mới: thay thế 260528, liệt kê quyết định kế thừa |
| Evidence `latest` bị rebuild ngoài ý muốn | Medium | Ghim cùng lockfile ngay, việc độc lập |
| TLS bypass khi deploy sang khách qua mạng | High (khi có khách thứ 2) | D4 |

---

**Status:** DONE_WITH_CONCERNS
**Summary:** Spec v2 → Metabase khả thi. Tầng API hiện có đã chạy trên 0.62.3 và dùng lại được qua IR của `markdown_parser`, nhưng bộ biên dịch metric → SQL phải viết mới. Deployer có 2 lỗi nhận diện theo tên (D1, D2) sẽ ghi đè dashboard FJ khi cài song song, nên phải sửa trước. Đề xuất bỏ Evidence khỏi sản phẩm (ghim và đóng băng), Rill để sau, thí điểm Weekly Pulse ~10 ngày công theo lát cắt dọc, registry làm module có schema ngoài `docs/`.
**Concerns:**
- Các nhận định về API Metabase 0.62 (`/api/database/:id/metadata`, `sync_schema`, đặt `entity_id`, bỏ `/api/metric`, `type: model`, markdown trong description, Sankey) dựa trên hiểu biết về API và chưa chạy thử. Mỗi điểm đã ghi rõ phải kiểm trên container tạm.
- Không kiểm được phiên bản Evidence đang cài trong image (không chạy docker hay mạng). Nhận định "bản legacy cuối 02/2026" lấy từ `external-references.md` và chưa xác minh.
- Ước lượng effort giả định một người quen codebase. Bước 3 (renderer) có biên độ lớn nhất.
- Thiết kế không nhắc plan `260528-1325-tool-agnostic-design-spec`. Cần lead quyết định thay thế hay kế thừa.

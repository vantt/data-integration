# analytics — registry chỉ tiêu, compiler và renderer report

Module code của sản phẩm report (thiết kế: `plans/261013-1751-modularize-data-platform-suite/report-product-design.md`, plan `plans/261014-2225-report-productization/`; ranh giới: [docs/architecture/modules.md §13](../docs/architecture/modules.md#13-analytics-report)).

Một chỉ tiêu được định nghĩa **một lần** trong registry; SQL của mọi report, tài liệu chỉ tiêu và chú giải Việt–Anh sinh ra từ đó. Module chỉ đọc: nó sinh SQL và file, không ghi vào serving, `data_lake` hay Metabase.

## Thư mục

| Đường dẫn | Nội dung |
|---|---|
| `schema/*.schema.json` | JSON Schema 2020-12: lớp ngữ nghĩa, chỉ tiêu, hồ sơ khách, spec report v2, catalog |
| `registry/semantic/<model>.yml` | Lớp ngữ nghĩa: một file cho một mart |
| `registry/metrics/<domain>.yml` | Lớp chỉ tiêu: `metrics: [...]` theo miền (`sales`, `customers`, `finance`) |
| `compiler/loader.py` | Nạp registry và hồ sơ khách |
| `compiler/formula.py` | Cú pháp biểu thức của chỉ tiêu `derived` và kiểm giới hạn |
| `compiler/sql.py` | Biên dịch chỉ tiêu × cửa sổ thời gian → SQL DuckDB |
| `compiler/validate.py` | Validator (gọi từ `scripts/checks/check_analytics_registry.py`) |
| `compiler/spec_validate.py` | Kiểm spec v2 và catalog với registry và hồ sơ khách |
| `catalog/catalog.yml` | Catalog report: ô chức năng × nhịp, engine, khu vực quyền, spec, thẻ KPI |
| `specs/<report_id>.yml` | Spec v2, mỗi report một file |
| `compiler/cards.py` | Biên dịch từng card của spec thành một câu SQL (KPI, nhóm theo chiều/ngày, so kỳ, `inline_sql`) và câu meta |
| `renderers/docs.py` | Sinh `docs/analytics-handbook/semantic/metric-registry.md` và `glossary.md` |
| `renderers/evidence.py` | Sinh project Evidence cho từng khu vực quyền: `evidence/areas/<area>/` |
| `renderers/site.py` | Sinh `evidence/site/Caddyfile` (đăng nhập theo khu vực) |
| `renderers/message.py` | Dựng tin tóm tắt từ `kpi_tiles` |
| `tests/` | pytest: schema, validator, golden SQL |
| `../tenants/<t>/analytics/profile.yml` | Hồ sơ khách: múi giờ, tham số doanh thu ghi tường minh, ràng buộc phân đoạn |

## Hai lớp registry

**Lớp ngữ nghĩa** mô tả một mart dbt: `relation` (view serving, ví dụ `main_marts.fact_orders`), `grain`, `time_dimensions`, `dimensions`, `joins` (chỉ many-to-one, một bước), `measures` (`column` + `agg ∈ {sum, count, count_distinct, min, max}`; cột tỉ lệ theo dòng ghi `aggregatable: false`; cột giá vốn/lợi nhuận ghi `cost: true`), `gates` (bộ lọc có tên, dạng có cấu trúc `{column, via?, op, value(s)?}`, không chuỗi SQL), và `validity` cho bảng có hiệu lực theo kỳ (mục tiêu).

**Lớp chỉ tiêu** gồm bốn loại:

| `type` | Hình dạng | Ví dụ |
|---|---|---|
| `simple` | Một measure của một model + `filters` + `time_axis` | `net_sales` = tổng `fact_orders.net_revenue`, kênh bán, đơn hiệu lực |
| `ratio` | `numerator` / `denominator` là id chỉ tiêu (tỉ số của tổng, không bao giờ trung bình của tỉ lệ); `scale: 100` cho phần trăm | `aov`, `discount_rate`, `gross_margin_pct` |
| `derived` | `expression` tuyến tính trên chỉ tiêu khác, hệ số là số hoặc đại lượng lịch | `gmv_pace_index` |
| `snapshot` | Measure của bảng có `validity`, lấy dòng có hiệu lực tại ngày tham chiếu | `gmv_target` |

Trường bắt buộc của mọi chỉ tiêu: `id`, `version`, `label {vi, en}`, `description`, `type`, `additivity`, `null_policy`, `cost_sensitive`, `unit`, `status`. Chỉ tiêu có `cost_sensitive: true` phải có `coverage_metric` (độ phủ giá vốn). `legacy_names` giữ tên cũ (ví dụ `net_sales` có `legacy_names: [net_revenue]`, cột mart vẫn là `net_revenue`).

Phân đoạn của khách (ví dụ `in_sales_scope`) là tên trừu tượng trong `filters`; giá trị ràng buộc nằm trong hồ sơ khách theo từng model (`segments.in_sales_scope.orders: {column: scope_sales, op: is_true}`), để thí điểm không phụ thuộc cột chuẩn hoá `*_std`.

## Giới hạn cứng của compiler

Registry không phải semantic layer tự chế. Compiler chỉ làm:

- `sum`, `count`, `count_distinct`, `min`, `max` trên một cột;
- tỉ số của hai tổng;
- `derived`: biểu thức `+ - * /` trên id chỉ tiêu, số, và đại lượng lịch `day_of_month`, `days_in_month`, `days_left_in_month`; hai chỉ tiêu không được nhân nhau; chỉ tiêu chỉ được ở mẫu số khi phép chia nằm ở gốc (tỉ số của hai biểu thức tuyến tính); `greatest(x, 0)` là phép chặn dưới duy nhất;
- một trục thời gian cho mỗi chỉ tiêu `simple`, một bước join many-to-one.

Window, lịch sử, phân bổ chi phí, ghép hai fact khác grain phải làm trong dbt. Vượt giới hạn thì validator báo lỗi; lối thoát duy nhất là `inline_sql` ở spec report (có khai báo cột đầu ra, bị đếm là "không chuẩn").

## Spec v2 và catalog

**Spec v2** (`specs/<report_id>.yml`, schema `schema/report-spec.schema.json`) mô tả một report không phụ thuộc công cụ: `tabs[] → blocks[] → cards[]`. Định dạng do skill `.skills/analytics-design` sở hữu (hướng dẫn và template `templates/report_spec_v2_template.yml`); schema nằm ở đây để validator và sản phẩm đi cùng nhau.

| Trường | Ý nghĩa |
|---|---|
| `spec_id`, `spec_version: 2`, `title`, `question`, `cadence`, `period_mode`, `as_of: yesterday` | Danh tính và nhịp của report; dữ liệu tính đến hết hôm qua |
| `baseline` | Mốc so số khi report thay một dashboard đang chạy (`metabase_blueprint`/`metabase_live`), và đã kiểm với bản đang chạy chưa |
| `blocks[].time_axis` | Trục thời gian người đọc thấy (`order_date`, `return_date`, `settlement_date`); card khác trục ghi `time_axis` riêng |
| `cards[].card_id` | Slug ASCII, duy nhất trong report, là khoá danh tính ở mọi engine |
| `cards[].kind` | `kpi_compare`, `trend`, `breakdown`, `breakdown_compare`, `derived`, `table`, `inline_sql`, `meta_period`, `meta_freshness`, `text` |
| `metric_ref`, `dimensions`, `grain`, `window`, `comparison`, `pct_change_of` | Chỉ tiêu (id registry), chiều `<model>.<dimension>`, cửa sổ và kỳ so sánh |
| `goal: {param}`, `outputs[].link: {param}` | Giá trị riêng của khách lấy từ `tenant_params` trong hồ sơ (mục tiêu tháng, mẫu link), không ghi cứng |
| `inline_sql: {sql, outputs, reason}` | Bậc đệm khi registry không biểu diễn được; placeholder `{{as_of}}`, `{{window_start}}`, `{{window_end}}`, `{{tz}}`; bị đếm là "không chuẩn" |
| `viz`, `bands`, `decimals`, `sort`, `limit`, `size`, `position` | Trình bày (term của `VISUALIZATION_VOCABULARY.md`, ngưỡng màu, làm tròn hiển thị, lưới `grid_columns`) |
| `baseline_name`, `baseline_columns` | Tên question và cột trong mốc, để harness so số ghép đúng cặp |

Chú thích từng thẻ và chân trang "doanh thu được tính thế nào" do renderer sinh từ registry và hồ sơ khách, không viết trong spec.

**Catalog** (`catalog/catalog.yml`, schema `schema/catalog.schema.json`): mỗi report có `id`, `cell` + `primary_cell` (chức năng × nhịp, ví dụ `EXE-W`), `engine` (`evidence` | `metabase`), `area` (khu vực quyền), `question`, `metrics`, `kpi_tiles` (card dùng cho tin tóm tắt và trang chủ), `spec`, `cost_sensitive`, `status`.

Validator kiểm thêm: schema spec và catalog; mọi `metric_ref` có trong registry và `active`; chiều khai báo trong lớp ngữ nghĩa và tới được bằng một join; card nhóm (`trend`, `breakdown*`) chỉ dùng chỉ tiêu của một model; trục thời gian của chỉ tiêu khớp trục hiển thị; `card_id` duy nhất; `inline_sql` có `outputs`, không đọc đồng hồ (`current_date`, `now()`), chỉ dùng placeholder cho phép; tham số khách tồn tại trong mọi hồ sơ; `metrics` của catalog bằng hợp `metric_ref` của spec; `cost_sensitive` của report suy ra từ chỉ tiêu; `kpi_tiles` là card có thật; tỉ lệ card `inline_sql` trên card dữ liệu (cảnh báo khi > 30%).

Report đầu tiên: `ceo_weekly_pulse` (`EXE-W`, `engine: evidence`, `area: dieu-hanh`, `status: pilot`), viết theo dashboard đang chạy (Metabase id 43, đã chụp chỉ đọc 15/10/2026; SQL trùng blueprint, nhưng không có hai question Forecast và Run-rate của blueprint): 3 tab, 28 question đúng thứ tự và tên, 2/22 card dữ liệu dùng `inline_sql` (bảng đơn hàng, đếm kênh lỗ).

## Renderer Evidence

`python3 -m analytics render evidence --tenant fine_japan` (thêm `--check` để chỉ kiểm) ghi cho mỗi khu vực trong `access.areas` của hồ sơ (trừ khu vực `legacy: true`) và mỗi report `engine: evidence` thuộc khu vực đó:

- `evidence/areas/<area>/evidence.config.yaml` — `deployment.basePath: /<area>`;
- `evidence/areas/<area>/sources/datalake/<report>__<card>.sql` — SQL đã biên dịch của **một card**, `as_of` = hôm qua theo múi giờ khách lúc build; file dữ liệu trích chỉ chứa kết quả card (bảng chi tiết bị giới hạn theo cửa sổ của card); `<report>__meta.sql` cho dải "Dữ liệu đến hết ngày …", chu kỳ và độ tươi;
- `evidence/areas/<area>/pages/<report>/index.md` — trang đọc đúng các file trích đó; tab và khối theo spec, BigValue có % so với kỳ trước, mục tiêu lấy từ `tenant_params`, ngưỡng (`bands`) thành nhãn mức, chú thích từ mô tả chỉ tiêu, chân trang "Doanh thu được tính thế nào" sinh từ hồ sơ và registry; `pages/index.md` liệt kê report của khu vực.

Card dùng chỉ tiêu `cost_sensitive` (hoặc `inline_sql` có `cost_sensitive: true`) không được render vào khu vực `can_view_cost: false`: SQL không được ghi, trang thay bằng "Cần quyền xem chi phí". Viz chưa có component Evidence tương ứng được thay (`gauge` → số + nhãn mức, `donut` → cột ngang, `progress-toward-goal` → số + % mục tiêu). Render hai lần ra byte giống hệt; mọi file có banner GENERATED và hash đầu vào (spec + registry + hồ sơ). Kết quả spike Evidence: `evidence/README.md`.

## Renderer site và tin tóm tắt

- `python3 -m analytics render site [--check]` sinh `evidence/site/Caddyfile` cho container `report_site` từ `access.areas`: mỗi khu vực một đường dẫn `/<area>/` với `basic_auth` riêng (tài khoản từng người trong `app_data/secrets/report_site/<area>.caddy`), khu vực `legacy` ở các đường dẫn gốc, không có `legacy` thì 404.
- `renderers/message.py`: tin tóm tắt của report = các thẻ `kpi_tiles` (chỉ card một giá trị) biên dịch với `as_of` của bản build, định dạng kiểu Việt Nam, kèm link `access.site_url/<area>/<report>/`; thẻ chi phí bị bỏ với kênh `can_view_cost: false`. Gửi và lịch nằm ở `orchestration/reports/` (kênh, lịch trong `message` của hồ sơ khách).

## Thời gian: `as_of` và cửa sổ

Mọi SQL nhận `as_of` (ngày tham chiếu, kiểu DATE) ở hai dạng: literal (`--as-of 2026-10-11`, dùng cho so số và test) hoặc biểu thức lúc chạy (`--as-of runtime` → `CAST(timezone('<tz>', now()) AS DATE) - 1`, tức "đến hết hôm qua" theo múi giờ của khách). Ranh giới ngày được chuyển sang `TIMESTAMPTZ` bằng `timezone('<tz>', ...)` với múi giờ trong hồ sơ khách, nên kết quả không phụ thuộc múi giờ phiên DuckDB.

| Cửa sổ | Khoảng `[bắt đầu, kết thúc)` (A = `as_of`) |
|---|---|
| `wtd` | thứ Hai của tuần chứa A → A + 1 ngày |
| `prev_week_full` | thứ Hai tuần trước → thứ Hai tuần này |
| `prev_wtd_same_span` | thứ Hai tuần trước → A − 6 ngày (cùng số ngày với `wtd`) |
| `mtd` | ngày 1 của tháng chứa A → A + 1 ngày |
| `mtd_before_as_of` | ngày 1 của tháng → A (không gồm A; tái tạo card tháng của Weekly Pulse) |
| `prev_week_start_to_date` | thứ Hai tuần trước → A + 1 ngày (card "14 Days" của Weekly Pulse) |
| `month_full`, `prev_month_full` | trọn tháng chứa A, trọn tháng trước |
| `last_<n>_days` | A − n + 1 → A + 1 ngày |

Để tái tạo blueprint Metabase đang chạy, `as_of` = `current_date` của blueprint.

**NULL:** `null_policy: propagate` (không `COALESCE(x, 0)` theo dòng). Tổng trên tập rỗng của chỉ tiêu cộng dồn trả 0 (`empty_result: zero`, khớp blueprint); mục tiêu không có (tổng 0) là thiếu (`zero_as_missing`), nên chỉ tiêu dựa trên mục tiêu ra NULL.

## Lệnh

Chạy từ gốc repo. Cần Python ≥ 3.10, `pyyaml`, `jsonschema` (có trên host và trong image `data_platform`; không thêm phụ thuộc).

```bash
python3 scripts/checks/check_analytics_registry.py        # validator (cũng chạy trong scripts/checks/run-all.sh)
python3 -m analytics validate [--manifest transformation/target/manifest.json]
python3 -m analytics compile --metric net_sales --window wtd --as-of 2026-10-11 [--compare prev_week_full]
python3 -m analytics render evidence [--check]   # sinh lại evidence/areas/<area>/
python3 -m analytics render site [--check]       # sinh lại evidence/site/Caddyfile
python3 -m analytics docs           # sinh lại metric-registry.md, glossary.md
python3 -m analytics docs --check   # exit 1 nếu file sinh ra lệch registry
```

Validator kiểm: JSON Schema; mọi cột có trong khai báo cột của model trong `manifest.json` của dbt (cột chưa có docs: cảnh báo); không measure `aggregatable: false` nào bị dùng; `legacy_names` không trùng id đang `active`; chỉ tiêu `cost_sensitive` có `coverage_metric` và cờ khớp với measure `cost: true` (cột giá vốn, biên, lợi nhuận); biểu thức `derived` trong giới hạn; join một bước many-to-one; phân đoạn trong `filters` có ràng buộc trong mọi hồ sơ khách; `metric-registry.md` và `glossary.md` sinh lại không có diff.

pytest không có trên host; chạy trong image `data_platform` (chỉ đọc, không mạng) với pytest đã ghim ở `~/.cache/fg-dw-tools/deps/home/pylib` (`scripts/shadow/prepare-deps.sh`):

```bash
docker run --rm --network none -u "$(id -u):$(id -g)" -v "$PWD":/w:ro \
  -v ~/.cache/fg-dw-tools/deps/home/pylib:/pylib:ro -w /w \
  -e PYTHONPATH=/w:/pylib -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python \
  fg-dataware-house-data_platform -m pytest -p no:cacheprovider -q analytics/tests
```

Golden SQL ở `tests/golden/<metric>__<window>.sql`; sau khi đổi compiler có chủ đích, sinh lại bằng `python3 -m analytics.tests.regen_golden` rồi đọc diff.

## Ranh giới

`analytics/` không import `orchestration`, `ingestion`, `transformation` (`scripts/checks/check_boundaries.py`, luật `py-import`). Hồ sơ khách chỉ được đọc qua tham số `--tenant` / `--profile`, không nhập cứng tên khách trong code.

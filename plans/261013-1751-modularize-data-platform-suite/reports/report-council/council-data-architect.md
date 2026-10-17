---
title: "Hội đồng phản biện — góc nhìn data architect (dbt-duckdb, serving layer)"
role: data architect
date: 2026-10-14
reviews: report-product-design.md (§4 ①②④, §6, §9), taxonomy-engine-design.md (§3, §7), roadmap.md (Cơ chế pack, Đợt 7), references/reports/external-references.md §5–6, handbook-inventory.md §3
code_read: fg-dw-modular @111f1386 (transformation/models, scripts/provisioning/bootstrap_serving_views.py, refresh_rolling.py, orchestration/assets/serving.py); fg-dataware-house rill/, docs/analytics-handbook/semantic/metrics.md
---

# Góc nhìn data architect: metric registry, mart, serving view, pack, taxonomy

## 0. Kết luận ngắn

1. **Đồng ý hướng "registry YAML + mart + generator"**, nhưng câu "số tính sẵn trong dbt mart" cần sửa thành: **dbt tính sẵn mọi thứ có logic theo dòng hoặc theo lịch sử; BI chỉ được làm phép cộng/đếm/tỉ số của tổng trên cột mart, với SQL do generator sinh**. Nếu hiểu "tính sẵn" là pre-aggregate theo ngày × kênh thì sẽ phải rebuild khi đổi tham số doanh thu, và không cắt được theo chiều tuỳ ý.
2. **Tham số ghi nhận doanh thu không cần rebuild mart** nếu mart giữ đủ các mốc thời gian và các thành phần tiền tách cột. Tham số được áp **lúc generator sinh SQL** (đọc hồ sơ khách), không phải lúc người dùng xem dashboard và không phải dbt var. Chỉ những tham số làm đổi **trạng thái của thực thể** (ngưỡng hạng khách, phân vị RFM, múi giờ của `date_key`) mới đi vào dbt (var / `taxonomy_param`).
3. **MetricFlow: để sau** (xét ở Đợt 3, khi cần agent/MCP hỏi metric động). Không nhét `semantic_models` vào dbt project đang chạy nightly. Registry giữ hình dạng tương đương để dịch 1-1 về sau.
4. **Hôm nay đã có 3 định nghĩa lệch nhau cho cùng một chỉ tiêu** (chứng cứ ở §1). Đây là lý do mạnh nhất để registry trỏ vào **cột mart**, cấm engine tự dẫn xuất lại logic.
5. **Serving layer chưa có hợp đồng**: view là `SELECT *` trên file parquet mới nhất, mart không bật `contract`, ba BI đọc qua ba đường khác nhau. Trước khi deployer "tra field theo `schema.bảng.cột`" ở nhà khách, cần một schema serving có phiên bản, cột liệt kê tường minh.
6. §9.3: **registry/catalog là module code có JSON Schema và CI**, không nằm trong `docs/`. `metrics.md` sinh ra từ registry.

## 1. Bằng chứng từ code (đọc 14/10)

| # | Phát hiện | Vị trí | Hệ quả cho thiết kế |
|---|---|---|---|
| E1 | `scope_sales/retail/b2b` ở mart **không phụ thuộc trạng thái**; cổng trạng thái là cột riêng `is_active_order` = `status NOT IN ('CANCELLED','DRAFT')` | `core/marts/sales/fact_orders.sql:203-221` | Doanh thu đúng = `scope_* AND is_active_order` |
| E2 | Rill **tự dẫn xuất lại** `scope_*` = `is_sales_channel AND status NOT IN ('CANCELLED','Voided')`; `scope_retail` thiếu điều kiện `channel_format <> 'B2B'`, `scope_b2b` thiếu nhánh `channel_format = 'B2B'`; không loại `DRAFT` | `rill/models/orders_enriched.sql:79-83` | Rill và Metabase đang ra **số retail/B2B khác nhau**. Đây là lỗi thật, không chỉ rủi ro |
| E3 | `metrics.md` ghi `net_revenue` = `SUM(net_revenue)`, không cổng trạng thái; Rill `net_revenue` cũng không cổng | `semantic/metrics.md:165+`, `orders_core_metrics.yaml:88-90` | Định nghĩa thứ ba. Registry phải có `filters` bắt buộc, không để mỗi nơi tự nhớ |
| E4 | Cột tỉ lệ theo dòng: `gross_margin_pct`, `channel_net_margin_pct`, `order_discount_rate` | `packs/finance/marts/sales/fact_order_economics.sql` | BI mà `AVG()` các cột này là trung bình của tỉ lệ (sai). Registry phải đánh dấu `aggregatable: false` |
| E5 | `gross_profit` = NULL khi thiếu giá vốn (đúng), nhưng `channel_net_profit` dùng `COALESCE(cogs_amount, 0)` → **thiếu giá vốn thì lợi nhuận kênh = doanh thu** | cùng file, khối `channel_net_profit` | Mâu thuẫn trực tiếp với nguyên tắc "thiếu `enhances` → hiện –, không hiện số". Phải sửa ở mart trước khi registry trỏ vào |
| E6 | Phí sàn là cột Shopee cứng (`shopee_platform_fees`, `shopee_net_settlement`); công thức lặp 3 lần, có ghi chú "thêm Lazada thì sửa cả hai chỗ" | cùng file | Metric chuẩn `marketplace_fee_amount` chưa có cột chung để trỏ vào |
| E7 | `date_key` của đơn dùng `AT TIME ZONE 'Asia/Ho_Chi_Minh'` cứng; `date_key` của hoàn dùng `STRFTIME` dựa vào `TimeZone` của session dbt (`profiles.yml`) | `fact_orders.sql:167`, `fact_order_returns.sql` | Múi giờ là tham số khách nhưng đang nằm ở 3 nơi (SQL, profile, `SET TimeZone` trong bootstrap). Phải gom về một var |
| E8 | Mốc thời gian có sẵn: `ordered_at`, `first_shipped_at` (fact_orders), `delivered_at`, `is_delivered` (fact_fulfillments), `returned_at`/`return_date` (fact_order_returns); `return_amount` gắn theo đơn (fact_order_economics) | các file trên | Đủ nguyên liệu để đổi trục ghi nhận lúc query, thiếu `confirmed_at`, `paid_at`, `cancelled_at` |
| E9 | Serving view: `CREATE OR REPLACE VIEW <folder> AS SELECT * ... read_parquet(glob, union_by_name=true) WHERE filename = max(filename)`, cho **mọi** thư mục trong `rolling/`; thêm alias `main_marts.<t>` | `scripts/provisioning/bootstrap_serving_views.py` | Không có danh sách public, không có cột tường minh; kiểu cột có thể bị nới ngầm (đã ghi trong `refresh_rolling.py`) |
| E10 | Tạo view mới **phải dừng Metabase** (khoá DuckDB) | docstring cùng file | Mọi thay đổi hợp đồng serving là sự kiện có downtime → gắn vào `upgrade`, không vào nightly |
| E11 | Ba đường đọc: Metabase → `serving/olap.duckdb`; Evidence → bản copy `olap-serving.duckdb` lúc khởi động container; Rill → `export/rill/current/<t>.parquet` | `connection.yaml`, `docker-compose.yml:96`, `rill/models/src_*.yaml` | "Golden query" phải chạy trên cả ba; Rill nên đọc qua cùng hợp đồng |
| E12 | Mart không có `contract`, `access`, `group`; dbt-core 1.11.12, dbt-duckdb 1.10.1; **`duckdb` Python không ghim phiên bản** | `_core__models.yml`, `ingestion/requirements.txt` | CI không có danh sách cột đáng tin để kiểm registry; file `olap.duckdb` ghi bằng một bản DuckDB, Metabase đọc bằng bản trong driver MotherDuck |
| E13 | Tiền lệ "tham số khách làm đổi số qua dbt var": `cogs_primary_source` (`sapo_mac`/`misa`) | `var('cogs_primary_source', ...)` | Kiểu tham số này (chọn nguồn dữ liệu) đúng là phải ở dbt |

## 2. (a) Thiết kế registry

### 2.1 Hai tầng, giống MetricFlow: measure gắn mart, metric gắn measure

```yaml
# analytics/registry/semantic/orders.yml   — tầng "semantic model": một fact, một grain
id: orders
model: fact_orders                 # tên model dbt; serving view sinh từ đây (§5)
serving_relation: serving_v1.fact_orders
grain: order                       # khoá: order_id
time_dimensions:                   # các trục thời gian hợp lệ; tham số chọn trục nào
  ordered_at:   {column: ordered_at, default: true}
  shipped_at:   {column: first_shipped_at}
  delivered_at: {via: fulfillments.delivered_at}      # chỉ khi capability fulfillment_events
joins:                             # chỉ many-to-one, tối đa 1 bước
  - {to: dim_channels, on: channel_key}
  - {to: dim_customers, on: customer_key}
measures:
  net_revenue_sum: {column: net_revenue, agg: sum, unit: VND}
  order_count:     {column: order_id, agg: count_distinct}
gates:                             # bộ lọc có tên, dùng lại trong metric
  active_order: {column: is_active_order, eq: true}
```

```yaml
# analytics/registry/metrics/sales.yml   — tầng metric
- id: net_revenue
  version: 1
  label: {vi: "Doanh thu thuần", en: "Net sales"}
  description: "..."                # nguồn duy nhất; metrics.md sinh từ đây
  type: simple                      # simple | ratio | derived | snapshot
  measure: orders.net_revenue_sum
  filters: [gate: active_order]     # bắt buộc, generator không cho bỏ
  segment_filters_allowed: [order_scope_std, channel_format_std, customer_type_std]
  time_axis: {param: revenue_recognized_at}   # trục do tham số khách quyết định (§3)
  additivity: additive              # additive | semi_additive(time) | non_additive
  null_policy: propagate            # NULL → "–", cấm COALESCE 0 ở generator
  requires: [orders]
  enhances: []
  params: [revenue_recognized_at, return_deducted_at, include_platform_subsidy]
  owner: product
  status: active                    # draft | active | deprecated (replaced_by)
  golden: tests/golden/net_revenue.yml
- id: aov
  type: ratio
  numerator: net_revenue
  denominator: orders_active        # ratio of sums; generator không bao giờ AVG
- id: gross_margin_pct
  type: ratio
  numerator: gross_profit           # gross_profit có filter has_cogs
  denominator: net_revenue_with_cogs
  requires: [orders, unit_cost]
```

Trường bắt buộc bổ sung so với §4① của bản thiết kế: `version`, `type` (có `ratio(num, den)`), `gates`/`filters` có cấu trúc (không phải chuỗi SQL), `time_axis`, `additivity`, `null_policy`, `golden`. Bộ lọc viết dạng `{column, op, values}` để dịch được sang Metabase SQL, Rill `expression`, Evidence và MetricFlow `where`.

**Giới hạn cứng của generator** (để registry không thành semantic layer tự chế): chỉ `sum | count | count_distinct | min | max`, `ratio`, `derived` = tổ hợp tuyến tính của metric khác; một trục thời gian; join many-to-one tối đa một bước. Mọi thứ cần window, lịch sử, phân bổ, đối soát, hoặc ghép hai fact khác grain → **phải là cột/mart dbt**.

### 2.2 Cái gì materialize ở dbt, cái gì BI tính

| Loại | Ở đâu | Ví dụ |
|---|---|---|
| Logic theo dòng, tách thành phần tiền | dbt (cột fact) | `net_revenue` không VAT, `discount_amount`, `cogs_amount`, phí sàn chung, trợ giá sàn **cột riêng** |
| Cờ/trạng thái theo dòng | dbt | `is_active_order`, `is_first_order`, `has_cogs`, `order_status_std` |
| Lịch sử, cửa sổ, cohort, phân bổ | dbt (mart) | khách mới/quay lại, cohort, RFM, vòng đời, ABC 28 ngày, days of supply, phân bổ overhead, COGS đối soát |
| Semi-additive (tồn kho, số dư) | dbt snapshot theo ngày; registry `additivity: semi_additive` → generator lấy `last` theo thời gian | `fact_inventory_balance`, `fact_account_balance_monthly` |
| Tỉ số **giữa hai fact khác grain** (MER, CAC, NC-ROAS, CM3) | dbt mart grain chung `ngày × kênh` | ghép `fact_orders` với `fact_marketing_spend` trong BI sẽ fan-out |
| Cộng/đếm/tỉ số của tổng trên một fact | BI, SQL do generator sinh | doanh thu, đơn, AOV, tỉ lệ giảm giá, tỉ lệ huỷ |
| `count_distinct` khách | BI, tại đúng grain hỏi | không pre-aggregate rồi cộng lại |

Cột `*_pct` theo dòng ở E4 giữ lại cho drill-down nhưng `aggregatable: false`; generator từ chối dùng chúng làm measure.

### 2.3 Map tới serving view

Registry tham chiếu **tên model dbt**; generator dịch sang `serving_relation` theo phiên bản hợp đồng đã cài (§5). CI kiểm: mọi `column` trong registry tồn tại trong danh sách cột public của model (§5.2), mọi giá trị trong filter trên `*_std` thuộc `taxonomy_canonical` hiện hành.

## 3. (b) "Tính sẵn trong mart" có hợp với tham số doanh thu theo khách không?

**Có, với điều kiện mart lưu "nguyên liệu", không lưu "kết luận".** Lưu ý: mỗi khách là một bản cài riêng (single-tenant), nên "rebuild theo tenant" thực ra là rebuild bản cài đó; mart lại là `external` parquet, build lại toàn bộ mỗi đêm. Vấn đề thật không phải chi phí build mà là **đổi tham số = viết lại lịch sử ngầm** và **không cho được hai report dùng hai trục** (ext-ref §6.3 đề xuất `time_axis` theo từng report).

Phân loại tham số:

| Tham số | Áp ở đâu | Cách |
|---|---|---|
| `revenue_recognized_at` ∈ {order_created, shipped, delivered, paid} | **Generator** (lúc sinh SQL) | Chọn `time_dimension` + gate tương ứng (`is_delivered`…). Mart giữ đủ mốc: thêm `confirmed_at`, `paid_at`, `cancelled_at`, `delivered_at` vào `fact_orders` (cột mới, không đổi số) |
| `return_deducted_at` ∈ {return_date, order_date} | Generator | Theo ngày hoàn: `UNION ALL` giá trị âm từ `fact_order_returns` theo `return_date` (hành vi hiện tại, E8). Theo ngày đơn: trừ `return_amount` trên dòng đơn |
| `include_platform_subsidy` | Generator | `net_revenue` + `platform_subsidy_amount` (cột riêng, capability `marketplace_settlement`) |
| `aov_denominator` | Generator | đổi `denominator` của metric `aov` |
| Ngưỡng hiển thị (biên mục tiêu, cảnh báo) | Renderer, từ hồ sơ khách | Không chạm dữ liệu |
| Múi giờ (`date_key`), nguồn giá vốn, ngưỡng hạng khách / vòng đời / phân vị RFM | **dbt** (var từ `tenant.yaml`, hoặc `taxonomy_param` có phiên bản) | Đổi trạng thái thực thể đã materialize; đổi là sự kiện restate có ghi nhận |

Đề xuất thêm một model **`fact_revenue_events`** (dạng sổ sự kiện có dấu: `sale` tại các mốc, `return` âm tại ngày hoàn, `subsidy`), cùng ý với "sales agreements" của Shopify. Generator chọn loại sự kiện + mốc theo tham số; mọi biến thể đều là `SUM(amount)` trên một bảng, không cần `UNION` trong SQL của BI. Model mới, chạy song song, không đổi số mart hiện có.

Ràng buộc đi kèm:
- Tham số được **đóng băng lúc deploy**: deployer ghi `params_hash` cùng phiên bản registry đã cài; footer report hiện "Doanh thu ghi nhận theo: ngày tạo đơn". Không cho người xem tự bật tắt trên dashboard (dễ ra hai con số cùng tên).
- Đổi tham số = deploy lại các card bị ảnh hưởng, kèm `--dry-run` liệt kê card. Không rebuild dbt.
- `paid_at`/`delivered_at` phụ thuộc connector; nếu capability thiếu thì tham số đó **không chọn được** (validator chặn ở hồ sơ khách), thay vì ra số rỗng.

## 4. (c) MetricFlow: bây giờ hay sau?

**Sau. Spike ở Đợt 3, chỉ khi có use case truy vấn metric động (agent/MCP, ad-hoc).**

Lý do không làm bây giờ:
- Không BI nào trong stack đọc MetricFlow; vẫn phải tự viết generator cho Metabase/Rill/Evidence. MetricFlow chỉ thay phần "dịch metric → SQL", là phần dễ nhất.
- Khai báo `semantic_models`/`metrics` trong dbt project đang chạy nightly sẽ đưa validator của dbt (time spine, kiểm semantic) vào đường build: một lỗi định nghĩa metric có thể làm hỏng `dbt parse` của pipeline sản xuất.
- Docs dbt không liệt kê DuckDB; repo MetricFlow có extra `dbt-duckdb` (ext-ref [S51]). Theo hiểu biết của tôi, bộ test nội bộ của MetricFlow có chạy DuckDB, nhưng **chưa xác minh** với dbt-core 1.11.12 / dbt-duckdb 1.10.1 của dự án. Giấy phép đã đổi 2 lần.
- Không có khái niệm tenant/overlay; tham số doanh thu sẽ phải là var → kéo về đúng vấn đề §3.

Giữ đường lui: registry tầng semantic (`model`, `grain`, `time_dimensions`, `measures.agg`, `joins` theo entity) và tầng metric (`simple/ratio/derived`, filter có cấu trúc) **dịch 1-1** sang MetricFlow. Khi spike: sinh `semantic_models` vào **một dbt project riêng chỉ đọc serving**, so `mf query --explain` với SQL generator trên bộ golden; khớp 100% mới cân nhắc thay generator SQL.

## 5. (d) `*_std`, capability, hợp đồng serving view, phiên bản

### 5.1 `*_std` → filter/chiều của registry

- Registry chuẩn chỉ cho phép chiều và bộ lọc là `<domain>_std` hoặc chiều chuẩn (ngày, `order_status_std`). Nhãn riêng (`customer_type`) chỉ dùng ở drill-down hoặc report overlay.
- **`scope_*` hiện là phân loại riêng FJ** viết cứng trong `fact_orders` (E1) và bị chép lệch ở Rill (E2). Hướng: `scope` trở thành domain dẫn xuất của bộ máy phân loại (bảng quyết định trên `channel_format_std` × `customer_type_std`, đúng taxonomy §3.5), ra cột `order_scope_std`. Registry lọc bằng `order_scope_std`, không bằng boolean. Trước khi bộ máy có: lớp ánh xạ nhãn → mã chuẩn (ưu tiên 1 sau Đợt 1) sinh cột này từ `scope_*` hiện có, và **Rill phải bỏ việc tự tính `scope_*`** ngay (sửa E2 không cần chờ registry).
- Mâu thuẫn cần chốt: taxonomy §8 #1 nói "`*_std` chưa lên mart public tới khi kiểm bằng doanh nghiệp thứ hai", trong khi catalog chuẩn chỉ dùng `*_std`. Đề xuất: cột `*_std` có trên mart nhưng **ở hợp đồng serving `preview`** (§5.3), registry đánh dấu metric/report dùng chúng là `status: preview`; FJ dùng được, chưa hứa ổn định cho khách thứ hai.
- Filter giá trị mã chuẩn được kiểm với `taxonomy_canonical` (code tồn tại, chưa `deprecated_in`); mã bị thay (`replaced_by`) → CI báo report nào cần sửa.

### 5.2 Capability → `requires` / `enhances`

Ba mức, mỗi mức có nguồn riêng:

| Mức | Nguồn | Dùng để |
|---|---|---|
| declared | manifest connector ("cung cấp gì") | cài đặt: report nào được đưa vào |
| enabled | `enabled_packs` (`modules.yaml` → `tenant.yaml`); pack tắt → `pack_ref` trả bảng rỗng đúng cột | cài đặt |
| observed | model dbt mới `mart_capabilities` (capability, declared, enabled, coverage, last_seen_at), vd. % đơn có giá vốn, % đơn có `delivered_at`, độ tươi của ad spend | hiển thị: dưới ngưỡng → thẻ hiện "–" + "cần dữ liệu X" hoặc cảnh báo độ phủ |

- `requires` của report **suy ra** từ hợp các metric nó dùng (cộng phần khai báo thêm), không gõ tay hai lần. CI cảnh báo khi report khai báo thiếu so với metric.
- Pack tắt phải ra **NULL**, không ra 0, xuyên suốt từ `pack_ref` tới cột mart (vì vậy E5 là điều kiện tiên quyết). Generator cấm `COALESCE(x, 0)` trên measure có `null_policy: propagate`.
- `requires` ở mức cột: registry ghi `requires: [unit_cost]` cho `gross_profit`; validator đối chiếu với danh sách cột "hợp đồng lõi–pack" của `pack_ref` để biết cột nào sẽ là NULL khi pack tắt.

### 5.3 Hợp đồng serving view và phiên bản giữa các bản cài

Đề xuất thay `SELECT *` theo thư mục bằng **schema serving sinh từ registry + manifest**:

- `serving_v<N>`: chỉ các model có `access: public` (dbt), **liệt kê cột tường minh** kèm `CAST` kiểu theo contract; giữ cơ chế rolling `max(filename)` bên dưới. Schema `main`/`main_marts` hiện có giữ nguyên cho dashboard FJ cũ tới khi chuyển xong (§7 thiết kế).
- Bật `contract: enforced` **sớm hơn Đợt 3, chỉ cho các mart public mà registry tham chiếu** (fact_orders, fact_order_economics, fact_order_returns, dim_customers, dim_channels…). Đây là nguồn danh sách cột đáng tin duy nhất cho CI; `manifest.json` không có contract chỉ chứa cột được viết docs.
- Quy tắc phiên bản: thêm cột = minor, ở nguyên `serving_vN`; đổi nghĩa/kiểu/xoá cột = tạo `serving_vN+1` song song; deployer chuyển card theo `spec_id`; xoá `vN` khi inventory deployer cho thấy không còn card nào dùng. Đổi nghĩa metric = metric `version` mới, không sửa tại chỗ.
- Mỗi bản cài ghi `installed: {product_version, registry_version, serving_contract, params_hash}` (deployer §4⑦ đã có ý này) để `upgrade` biết cần tạo schema mới hay không.
- Tạo/đổi view cần dừng Metabase (E10) → chỉ chạy trong `upgrade`/`doctor` của Đợt 5, có cửa sổ bảo trì; nightly chỉ cảnh báo drift như hiện nay.
- Deployer tra field phải ghim **schema** (`serving_v1.fact_orders.net_revenue`), vì cùng bảng xuất hiện ở `main` và `main_marts`.
- Rill đổi sang đọc cột theo cùng hợp đồng (metrics view sinh từ registry), Evidence đọc `serving_vN` từ bản copy; golden test chạy trên cả ba đường (E11).
- Ghim phiên bản `duckdb` Python trong image, và kiểm tương thích file với DuckDB trong driver Metabase (E12); hôm nay hai bên có thể lệch phiên bản mà không ai biết.

## 6. (e) Trả lời §9

### 9.1 — Hệ quả kỹ thuật của từng lựa chọn mặc định (giá trị do user chốt)

| Lựa chọn | Hệ quả kỹ thuật |
|---|---|
| Ghi nhận **khi tạo đơn** (hiện trạng mart: `date_key` từ `created_at`) | Không đổi số FJ; số các ngày gần nhất ổn định; khớp cách xem "doanh thu hôm nay" của POS. Cần gate trạng thái (`is_active_order`) và huỷ muộn sẽ làm số ngày cũ giảm (restate) |
| Ghi nhận **khi giao thành công** | Cần capability `fulfillment_events` có `delivered_at` đáng tin cho mọi nguồn (Sapo có trong `fact_fulfillments`; đơn sàn chưa kiểm). Số 3–10 ngày gần nhất liên tục tăng (dữ liệu đến trễ) → report ngày/tuần vô nghĩa nếu dùng trục này; nên chỉ dùng cho report tháng/tài chính. Đơn nhiều lần giao: cần quy tắc "lần giao cuối" |
| Trừ hoàn **theo ngày hoàn** (hiện trạng `fact_order_returns`) | Kỳ đã đóng không đổi; khớp `freeze_after_close` cho kế toán. Doanh thu thuần theo kênh/khách phải lấy `channel_key` từ đơn gốc (đã có) |
| Trừ hoàn **theo ngày đơn** | Mọi kỳ cũ bị viết lại khi có hoàn mới; xung đột với khoá kỳ kế toán; tiện cho phân tích chất lượng đơn |
| Trợ giá sàn **cộng vào net** | Cần `marketplace_settlement` (trễ 1–2 tuần sau giao) → net revenue của đơn sàn thay đổi sau khi đã báo cáo. Không còn khớp `net_revenue` VAT-exclusive hiện tại |
| Trợ giá sàn **dòng riêng** | Không đổi số FJ; metric `net_revenue_incl_subsidy` là derived, không cần mart mới |
| AOV / `net_revenue` vs / doanh thu không trừ hoàn | Ratio of sums trong mọi trường hợp; chỉ đổi `denominator`/`numerator`. Lệch số với POS là vấn đề diễn giải, không phải kỹ thuật |

Khuyến nghị kỹ thuật cho mặc định: **tạo đơn + hoàn theo ngày hoàn + trợ giá dòng riêng + AOV = net_revenue / đơn active**. Đây là hiện trạng mart, nên chuyển FJ sang registry không đổi số. Các lựa chọn khác vẫn mở bằng tham số (§3). Một bất định cần kiểm: `is_active_order` loại `DRAFT`, Rill loại `Voided`; phải có `order_status_std` để cổng trạng thái không phụ thuộc chuỗi trạng thái của Sapo.

### 9.3 — Đặt ở `docs/` hay module code?

**Module code**, vì registry được generator, validator, deployer và CI đọc; nó là hợp đồng máy, không phải tài liệu.

```
analytics/                              (trong image, có phiên bản cùng sản phẩm)
  schema/{metric,semantic,report,tenant-profile}.schema.json
  registry/semantic/*.yml   registry/metrics/*.yml
  catalog/catalog.yml       catalog/reports/<id>.yml   (spec v2)
  generators/{metabase,rill,evidence,docs}/
  tests/golden/*.yml
tenants/<tenant>/analytics/              (ngoài image, cùng chỗ luật phân loại)
  profile.yml  overlay.yml  metrics/*.yml (id có tiền tố tenant)  reports/*.yml
docs/analytics-handbook/semantic/metrics.md   ← sinh ra, có banner "generated", CI so diff
```

CI tối thiểu: JSON Schema; cột tồn tại trong contract của model public; mã `*_std` thuộc bộ mã chuẩn; `requires` report ⊇ hợp `requires` metric; không metric nào `AVG` một cột `aggregatable: false`; overlay không định nghĩa lại id chuẩn; `metrics.md` sinh lại không có diff.

## 7. (f) Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Registry phình thành semantic layer tự chế | Cao | Giới hạn cứng của generator (§2.1); thứ gì vượt → mart |
| Generator sinh join fan-out (fact đơn × dòng hàng × hoàn) | Cao | `grain` + join many-to-one một bước; tỉ số khác grain bắt buộc qua mart ngày × kênh |
| Hợp nhất 56 + 53 định nghĩa sẽ lộ các chênh lệch đang có (E2, E3) và **đổi số dashboard FJ** | Cao | Bước 0 lập bảng đối chiếu; mỗi chênh lệch là quyết định của user, không để người làm registry tự chọn |
| Serving `SELECT *` + `union_by_name` nới kiểu ngầm | Trung bình | Schema `serving_vN` cột tường minh + contract |
| Tham số đổi làm số lịch sử đổi mà người xem không biết | Trung bình | `params_hash` + footer + dry-run |
| Thiếu giá vốn ra số giả (E5) | Cao | Sửa `channel_net_profit`/`fully_loaded_net_profit` theo `has_cogs` trước khi registry dùng; việc này **đổi số** → qua gate, user duyệt |
| `*_std` chưa ổn định khi khách thứ hai vào | Trung bình | hợp đồng `preview`, version mã chuẩn |
| DuckDB writer/reader lệch phiên bản | Trung bình | ghim `duckdb`, test mở file bằng driver Metabase trong CI image |
| Bootstrap view cần dừng Metabase | Thấp–TB | chỉ trong `upgrade`, có cửa sổ |

## 8. Lộ trình đề xuất (khớp §8 thiết kế, bổ sung bước dữ liệu)

| Bước | Việc | Đổi số? | Phụ thuộc |
|---|---|---|---|
| 0 | Bảng đối chiếu ba nguồn (metrics.md, Rill yaml, cột mart) cho từng metric; liệt kê chênh lệch → user quyết | Không | — |
| 0b | Sửa nhanh độc lập: Rill dùng `scope_*`/`is_active_order` của mart thay vì tự tính (E2); ghim `duckdb` | Có (Rill) | user duyệt |
| 1 | JSON Schema + registry tầng semantic cho `fact_orders`, `fact_order_returns`, `fact_order_economics`, `dim_customers`; metric của Weekly Pulse trước, rồi phần còn lại của 56 + 53; sinh `metrics.md` | Không | 0 |
| 2 | dbt bổ sung không đổi số: mốc `confirmed_at/paid_at/cancelled_at/delivered_at`, `order_status_std`, `platform_subsidy_amount`, `fact_revenue_events`, `mart_capabilities`, var `tenant_timezone`; `access: public` + `contract: enforced` cho mart registry dùng | Không | 1 |
| 2b | Sửa NULL-policy E5 (đổi số) | Có | gate S, user duyệt |
| 3 | Schema `serving_v1` sinh từ registry + manifest, chạy song song `main`; golden test 3 đường | Không | 2 |
| 4 | Generator Rill (rẻ nhất để so số) → generator/deployer Metabase (thí điểm Weekly Pulse) | Không (song song) | 3 |
| 5 | Domain `order_scope_std` qua lớp ánh xạ, thay boolean `scope_*` trong registry | Không (cùng giá trị) | cơ chế pack + lớp ánh xạ |
| Đợt 3 | Spike MetricFlow trên project dbt riêng đọc serving, khi có use case agent/MCP | — | 3 |

## Câu hỏi còn mở

1. `Voided` có phải trạng thái thật của Sapo không (Rill lọc, mart không lọc), và `DRAFT` có nên bị loại khỏi doanh thu ở Rill không? Cần số liệu.
2. Đơn sàn trong dữ liệu FJ có `delivered_at` qua `fact_fulfillments` không, độ phủ bao nhiêu? Quyết định trục "giao thành công" có khả thi.
3. User có chấp nhận bật `contract: enforced` cho các mart public trước Đợt 3 (nightly sẽ dừng khi cột lệch) không?
4. Chấp nhận `*_std` ở trạng thái `preview` trong hợp đồng serving để catalog chuẩn chạy được với FJ trước khi có khách thứ hai?

---

Status: DONE_WITH_CONCERNS
Summary: Đồng ý registry YAML + mart + generator, với giới hạn rõ: dbt giữ "nguyên liệu" (mốc thời gian, thành phần tiền tách cột, cờ), generator áp tham số doanh thu lúc sinh SQL nên không cần rebuild; MetricFlow để Đợt 3; registry là module code có JSON Schema; cần schema serving có phiên bản và contract cho mart public.
Concerns: (1) Rill đang tính lại `scope_*` khác mart (E2), Rill/Metabase ra số retail/B2B khác nhau ngay hôm nay. (2) `channel_net_profit` ra bằng doanh thu khi thiếu giá vốn (E5), trái nguyên tắc "–". (3) Hợp nhất định nghĩa sẽ đổi số dashboard FJ; mỗi chênh lệch cần user quyết. (4) Chưa chạy dbt/DuckDB để định lượng chênh lệch; các khẳng định dựa trên đọc code @111f1386.

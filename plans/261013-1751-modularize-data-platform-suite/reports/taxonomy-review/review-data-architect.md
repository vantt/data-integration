---
title: "Review thiết kế taxonomy engine — góc nhìn data/analytics engineer (dbt-duckdb, Dagster)"
reviewer: data-architect persona
date: 2026-10-14
reviewed: taxonomy-engine-design.md (§3–§8), standards-and-patterns.md §8, phase-04, phase-06, plan.md
code_basis: worktree /home/vantt/app/fg-dw-modular @ 75894f81 (read-only)
---

# Review: taxonomy engine (góc nhìn data/analytics engineer)

## TL;DR

- **Khả thi, nhưng không phải như bản thiết kế đang viết.** Ta tái tạo được đúng từng byte giá trị `customer_type` hôm nay bằng "macro sinh một model mỗi domain, luật join qua `ref()`". Muốn vậy thì 7 điểm của thiết kế phải đổi (§C), và có 3 điểm trong số đó mà nếu làm đúng như bản viết thì gate chắc chắn đỏ: chuẩn hoá chuỗi ở tầng feature; thêm cột `customer_type_std` vào mart; sinh mã `UNKNOWN` khi feature null.
- **Lớp compiled-SQL diff của gate S không áp dụng được cho engine**, vì SQL chắc chắn đổi. Bằng chứng còn lại là golden 83 bảng (chỉ trên dữ liệu của một ngày), nên phải bổ sung dbt unit test để chứng minh tương đương trên các ca biên.
- **Có ba nhận định trong tài liệu sai so với code**: thứ tự ưu tiên `customer_type`, lý do đặt engine trước phase 6, và "value_group có hai biến thể".
- Trả lời §8 (chi tiết ở §D): #1 đồng ý có điều kiện; #2 **không** chặn phase 6, làm engine sau phase 6; #3 đồng ý bỏ tách macro nguyên văn, kèm 3 điều kiện; #4 đồng ý hướng nhưng ngoài MVP; #5 đồng ý restate, nhưng phải gắn với cơ chế full-refresh các model incremental; #6 dùng hướng kết hợp, và luật **không** được ghi thành seed CSV vào checkout prod.
- Ước lượng: MVP engine + thí điểm `customer_type` với 0 khác biệt mất **7–9 ngày công**, chưa tính phase 4 đã rút gọn.

## A. Tái tạo `customer_type` đúng từng byte: đi qua từng bước

### A.1 Hiện trạng thật (grep ngày 14/10)

| Nơi | Input | Luật | Ghi chú |
|---|---|---|---|
| `core/marts/dim_customers.sql` L215-230 | `customer_group_code`, `customer_group_name` (đã parse) + `EXISTS us_channel_customers` (đọc `fact_orders` ⋈ `dim_channels`, `channel_name='US'`, `status != 'CANCELLED'`) | FIRST: WHOLESALE > PARTNER > STAFF > KOL > CROSSBORDER > ELSE RETAIL | Đây là cột public |
| `core/marts/dim_customers.sql` L330-332 `is_us_gift_recipient` | Cùng các vị từ CROSSBORDER, **không** qua thứ tự ưu tiên | OR của 5 vị từ, logic **3 giá trị** | Khách WHOLESALE vẫn có thể có cờ TRUE |
| `core/marts/sales/fact_orders.sql` L107-119 | `customer_group` = **blob JSON thô** | Như trên nhưng không có US | Chỉ dùng **bên trong** `scope_retail`/`scope_b2b` (kèm `COALESCE(...,'RETAIL')`), không xuất thành cột |
| `core/marts/intermediate/int_customer_benchmarks.sql` L47-54 | `customer_group` (blob) | Giống `fact_orders` từng ký tự | Dùng cho `benchmark_status` → `dim_customers` |

Hệ quả:
- Thực ra chỉ có **2 logic khác nhau** ở 3 chỗ (fact_orders ≡ benchmarks), cộng một **cách dùng thứ tư** là cờ `is_us_gift_recipient`. Hai logic khác nhau ở **hai trục**: (1) input (blob JSON so với cột code/name đã parse; `LIKE '%WHOLESALE%'` trên blob khớp cả các field JSON khác); (2) tín hiệu US.
- Thứ tự ưu tiên trong code là **WHOLESALE > PARTNER > STAFF > KOL > CROSSBORDER**. `standards-and-patterns.md` R1 (`STAFF > KOL > CROSSBORDER > WHOLESALE > RETAIL`) và thiết kế §3.2 (`STAFF > KOL > WHOLESALE > RETAIL`) đều **sai**. Nếu cài theo tài liệu thì số đổi ngay.

### A.2 Feature cần (pilot, chưa chuẩn hoá)

| Feature | Model | Nguồn | Vì sao giữ thô |
|---|---|---|---|
| `group_blob` | `feat_customer_profile` | `dim_customers_base.customer_group` | Biến thể của fact_orders/benchmarks match trên blob |
| `group_code`, `group_name` | `feat_customer_profile` | `dim_customers_base` | Biến thể dim; NULL phải giữ nguyên là NULL |
| `channels_ordered_on VARCHAR[]` | `feat_customer_orders` | `fact_orders` ⋈ `dim_channels`, `status != 'CANCELLED'` (giữ đúng `!=`, NULL status bị loại) | Đúng ngữ nghĩa khoá của `fact_orders.customer_key` (khách lạ → sentinel `Unknown`) và tên `'US'` sau logic "(Unspecified)" của `dim_channels` |

Phải tách **hai feature model**. Lý do: `feat_customer_orders` phụ thuộc `fact_orders`, mà `fact_orders` lại cần nhãn từ biến thể blob. Gộp chung thì sinh vòng (xem §B.1).

`has_order_on_source(<key>)` của thiết kế nên cài thành **feature dạng list + toán tử `has`** (`list_contains`), không phải feature có tham số: một feature có tham số buộc sinh cột theo dữ liệu luật, tức là đọc dữ liệu lúc compile. Về lâu dài nên khoá bằng `source_id` (`4110169`), không khoá bằng tên hiển thị `'US'`: chỉ cần ai thêm nguồn `US - xxx` vào seed là tên đó thành `US (Unspecified)` và luật CROSSBORDER gãy mà không báo. Ở pilot vẫn phải khoá theo tên để giữ đúng byte, rồi ghi vào Known divergences.

### A.3 Luật thành dòng dữ liệu (domain `customer_type`, biến thể dim)

`taxonomy_rule(rule_id, domain, layer, priority, label, enabled)` + `taxonomy_rule_condition(rule_id, feature, op, value)` (AND trong một rule; OR thì thành nhiều rule cùng nhãn, giữ đúng thứ tự nhánh):

```text
prio rule_id  label        feature              op    value
10   ct_w1    WHOLESALE    group_code           like  %WHOLESALE%
11   ct_w2    WHOLESALE    group_name           like  %WHOLESALE%
20   ct_p1    PARTNER      group_code           like  %TYPE_PARTNER%
21   ct_p2    PARTNER      group_name           like  %TYPE_PARTNER%
22   ct_p3    PARTNER      group_code           like  %KY_GUI%
23   ct_p4    PARTNER      group_name           like  %KY_GUI%
30/31         STAFF        group_code|name      like  %TYPE_STAFF%
40/41         KOL          group_code|name      like  %TYPE_KOL%
50..53        CROSSBORDER  group_code|name      like  %TYPE_CROSSBORDER% | %CTN00014%
54   ct_x5    CROSSBORDER  channels_ordered_on  has   US
domain.default = RETAIL     (không phải UNMAPPED, không có UNKNOWN)
```

Biến thể blob (`customer_type__group_blob`, dùng cho fact_orders và benchmarks): 9 rule `group_blob like ...`, không có rule US.

**Toán tử phải là `like` (đúng `LIKE` của SQL), không phải `contains`.** Trong `LIKE`, `_` là wildcard: `'%KY_GUI%'` khớp cả `KY GUI` và `KYxGUI`; `'%TYPE_KOL%'` khớp `TYPE-KOL`. Danh sách toán tử ở §3.5 (`contains`, `starts_with`) không có `like`. Nếu dùng `contains`/`strpos` thì đúng byte chỉ còn là chuyện may mắn của dữ liệu hôm nay. Tiền lệ trong repo: `int_order_tags.sql` L53-55 cũng dùng `LIKE m.pattern`.

### A.4 SQL do macro sinh (phác thảo, DuckDB)

```sql
-- lbl_customer_type  (sinh bởi {{ taxonomy_label_model('customer_type') }})
WITH f AS (
  SELECT p.customer_key, p.group_code, p.group_name,
         COALESCE(o.channels_ordered_on, []) AS channels_ordered_on   -- EXISTS không bao giờ NULL
  FROM {{ ref('feat_customer_profile') }} p
  LEFT JOIN {{ ref('feat_customer_orders') }} o USING (customer_key)   -- feature set khai báo TĨNH theo domain
),
r AS (SELECT * FROM {{ ref('taxonomy_rule') }} WHERE domain = 'customer_type' AND enabled),
c AS (SELECT c.* FROM {{ ref('taxonomy_rule_condition') }} c JOIN r USING (rule_id)),
cond_eval AS (            -- tri-state: TRUE/FALSE/NULL như SQL gốc; một nhánh mỗi (feature, op) đã khai báo
  SELECT f.customer_key, c.rule_id,
    CASE
      WHEN c.feature = 'group_code' AND c.op = 'like' THEN f.group_code LIKE c.value
      WHEN c.feature = 'group_name' AND c.op = 'like' THEN f.group_name LIKE c.value
      WHEN c.feature = 'channels_ordered_on' AND c.op = 'has' THEN list_contains(f.channels_ordered_on, c.value)
    END AS ok
  FROM f CROSS JOIN c                              -- ~7k khách × ~20 điều kiện
),
rule_eval AS (            -- AND theo SQL 3 giá trị; KHÔNG dùng bool_and (bool_and bỏ qua NULL)
  SELECT customer_key, rule_id,
    CASE WHEN count_if(ok = false) > 0 THEN false
         WHEN count_if(ok IS NULL) > 0 THEN NULL ELSE true END AS hit
  FROM cond_eval GROUP BY ALL
),
first_hit AS (
  SELECT e.customer_key, r.label, r.rule_id
  FROM rule_eval e JOIN r USING (rule_id)
  WHERE e.hit
  QUALIFY row_number() OVER (PARTITION BY e.customer_key ORDER BY r.priority, r.rule_id) = 1
)
SELECT f.customer_key,
       COALESCE(h.label, 'RETAIL') AS customer_type,
       h.rule_id,
       -- cờ "đã khớp ít nhất một rule của nhãn X", giữ logic 3 giá trị cho is_us_gift_recipient
       (SELECT CASE WHEN bool_or(e.hit) THEN true WHEN count_if(e.hit IS NULL) > 0 THEN NULL ELSE false END
          FROM rule_eval e JOIN r USING (rule_id)
          WHERE e.customer_key = f.customer_key AND r.label = 'CROSSBORDER') AS matched__crossborder
FROM f LEFT JOIN first_hit h USING (customer_key)
```

Cách cắm lại vào code hiện có:
- `dim_customers`: `LEFT JOIN lbl_customer_type` rồi lấy `customer_type`. Dòng nào không có nhãn thì giữ fallback hiện có. `is_us_gift_recipient := matched__crossborder`.
- `fact_orders.customer_type_info` và `int_customer_benchmarks.base`: thay `CASE` bằng `LEFT JOIN lbl_customer_type__group_blob`. Các `COALESCE(cu2.customer_type,'RETAIL')` trong `scope_*` giữ nguyên.

**Bẫy NULL đã kiểm trên code.** `is_us_gift_recipient` có giá trị **NULL** khi code hoặc name là NULL và khách không có đơn US. `mart_customer_action_queue.sql` L71 (`AND NOT d.is_us_gift_recipient`) và `mart_customer_sku_action_queue.sql` L53 đang **loại** các dòng đó. Engine trả FALSE thay vì NULL sẽ làm thay đổi số dòng của hai mart CRM. Đây là lý do engine phải đánh giá theo đúng SQL 3 giá trị như trên.

### A.5 Kết luận phần (a)

Đúng từng byte ở **golden**: **có**, với điều kiện: dùng toán tử `like`; dùng feature thô; dùng `default`; đánh giá 3 giá trị; tách 2 domain; khoá theo tên `'US'`; cờ `matched__<label>`. Đúng từng byte ở **compiled SQL**: **không, và không thể**. Gate của engine là: golden + dbt inventory với `--allow-new --allow-code-change`. `dim_customers` vẫn có `fact_orders` là tổ tiên (qua `int_customer_metrics`), nên luật "repointed dependency kept upstream" (`refactor-safety-harness.md` §6.2) cho qua. Cộng thêm dbt unit test ở §B.4.

## B. DAG, incremental, hiệu năng, test

### B.1 Vòng phụ thuộc

DAG thật: `dim_customers_base → fact_orders → int_customer_metrics → int_customer_benchmarks → dim_customers`. Ngoài ra `dim_customers` đọc thẳng `fact_orders` và `dim_channels`.

- Pilot không có vòng nếu: `lbl_customer_type__group_blob` chỉ ref `feat_customer_profile` (ở trên `fact_orders`), còn `lbl_customer_type` ref thêm `feat_customer_orders` (ở dưới `fact_orders`, ở trên `dim_customers`).
- **Feature set của mỗi domain phải khai báo tĩnh trong YAML.** Macro chỉ biết ref những feature model mà luật (là dữ liệu) dùng nếu được khai báo trước. Nếu macro ref mọi feature model thì vòng xuất hiện ngay cả khi không có rule nào dùng feature gây vòng. Hệ quả: nghiệp vụ thêm rule trên một feature mới thì phải đổi code. Thiết kế chưa nói điều này.
- **Thống nhất CROSSBORDER vào `fact_orders` (Đợt sau) sẽ tạo vòng `fact_orders → lbl → fact_orders`** nếu feature US đọc `fact_orders`. Nguyên tắc "feature chỉ từ `std_*`" (§3.1) nghe đúng, nhưng muốn làm được thì phải có model `int_orders_resolved` (std_orders + `customer_key` đã validate + `channel_key` đã resolve + `is_active`) đứng trước `fact_orders`, để cả fact lẫn feature cùng dùng. Nếu không có model này, feature từ `std_*` sẽ là **bản cài lại song song** logic resolve kênh/khách và sẽ lệch dần. Đây là việc phải có trước khi thống nhất, không phải trước pilot.
- **`entity_labels` (view UNION ALL) không được mart nào ref.** View này phụ thuộc mọi `lbl_*`, nên chỉ cần một mart upstream đọc nó là có vòng. Mart join thẳng `lbl_<domain>`; `entity_labels` chỉ dùng cho giám sát và giải thích.
- `scope_*` thành bảng quyết định trên subject `order`: nếu bảng đó cần `customer_type_std` (biến thể có US) thì cũng gặp đúng vòng trên. Phải chờ `int_orders_resolved`.

### B.2 Incremental (17 model; harness ghi 16)

- `int_customer_entry_attributes`: incremental, **bất biến**, lọc `dim_customers.customer_type = 'RETAIL'`, chỉ thêm khách chưa có (L128). Pilot đúng từng byte thì không ảnh hưởng. Nhưng **mọi lần đổi luật sau này sẽ không được restate** nếu không full-refresh: khách đã vào bảng thì ở lại dù đổi thành WHOLESALE. `int_customer_discount_metrics` cũng thế, vì chỉ tính lại khách có đơn mới, theo watermark `metric_calculated_at - 1 day`.
- Vì vậy "restate" (#5) **chưa phải mặc định tự có**. Cần cơ chế: `ruleset_version` của domain đổi thì Dagster chạy `dbt build --select lbl_<domain>+ --full-refresh`. Cách khác là gate onboarding chạy full-refresh. Hiện tại full-refresh rẻ: gate S, gồm cả full-refresh, xong trong 2 phút 18 giây.
- `lbl_*` của subject customer (khoảng 7k dòng) nên materialize **view** (hoặc table rẻ). Không để thư mục mặc định `intermediate/` biến nó thành `external` parquet (`dbt_project.yml` cấu hình theo layer), và không làm incremental. Job chính chọn `all_dbt_assets`, nên model mới tự vào job. Job hourly theo tag không đụng tới.

### B.3 Hiệu năng

- Customer: 7k × khoảng 20 điều kiện = 140k dòng, không đáng kể.
- Order hoặc discount_line (vài trăm nghìn đến 1 triệu dòng × 50–60 điều kiện): `CROSS JOIN` rồi `CASE` cho ra 30–60 triệu lần so sánh. DuckDB vẫn xử lý được trong vài giây, nhưng nên để macro sinh **UNION ALL theo (feature, op)**: `eq`/`in` thành hash join, chỉ `like`/`regex` mới cần nested loop.
- Đọc `taxonomy_domain` lúc compile **phải lấy từ YAML (`vars` hoặc macro trả dict), không lấy từ seed.** Đọc seed lúc compile chính là `run_query` trên một relation. Trên lake trống (gate 6.6) hoặc trong bước `dbt parse` của op Dagster, relation đó chưa tồn tại và compile sẽ fail. Thiết kế §4 ghi "YAML hoặc seed", chỗ này phải sửa.

### B.4 Chiến lược test

1. **Tương đương:** dbt unit test (dbt-core 1.11.12 đã hỗ trợ) với fixture cho từng ca biên: wildcard `_`; code NULL và name khớp; Unknown sentinel; khách WHOLESALE có đơn US (nhãn WHOLESALE, cờ TRUE); khách không có nhóm, không có đơn US (nhãn RETAIL, cờ **NULL**); blob khớp nhưng code/name không khớp. Lý do: golden chỉ phủ dữ liệu của một ngày, rule nào hôm nay không khớp dòng nào thì golden không thấy.
2. **Đối chiếu song song một vòng:** giữ CASE cũ thành một model tạm `audit_customer_type_legacy` và test `equal_rowcount` + `EXCEPT` = 0 so với `lbl_*` trên prod trong 1–2 tuần, rồi xoá.
3. **Hợp lệ hoá dữ liệu luật:** mỗi `feature`/`op` thuộc danh sách khai báo của domain; `(domain, priority)` unique, hoặc tie-break bằng `rule_id`. Hiện `ref_tag_categories` có 28 dòng cùng `priority=10`, và `int_order_tags` L46-49 không có tie-break, tức là đã có rủi ro không tất định. Thêm: `label` thuộc `taxonomy_label`; `value` ép kiểu được.
4. **Mức độ:** test seed luật ở `error` sẽ làm `dbt build` **SKIP mọi model phía sau** trong nightly. Lỗi luật vì vậy phải bị chặn ở bước kiểm tra trước khi nạp (CI hoặc validator). Test chạy lúc build để `error` cho tính hợp lệ cú pháp, `warn` cho độ phủ.
5. **Seed:** khai báo `+column_types` varchar cho **mọi** cột luật. Repo đã có tiền lệ `id` bị parse thành INTEGER làm mất `_` (comment ở `dim_channels.sql` L21-24). Ô rỗng trong CSV thành NULL, nên luật `province = ''` (`geo_region` L292) không biểu diễn được nếu không có toán tử `is_null_or_empty`.

## C. Những chỗ sai hoặc thiếu đặc tả trong thiết kế

| # | Mục | Vấn đề | Đề xuất |
|---|---|---|---|
| C1 | §3.1 chuẩn hoá chuỗi ở tầng feature | `LOWER`/`TRIM`/gộp khoảng trắng/bỏ dấu **đổi kết quả khớp**. Ví dụ `LIKE` hiện phân biệt hoa thường; luật discount `'% us%'` dựa vào khoảng trắng đứng trước (`fact_orders` L56-59); bỏ dấu biến `mẫu` thành `mau`. | Feature thô và feature `_norm` song song. Pilot chỉ dùng feature thô. Chuyển sang `_norm` là một thay đổi có đổi số. |
| C2 | §3.3 `UNKNOWN` khi feature bắt buộc null | Hôm nay `ELSE 'RETAIL'` nuốt cả NULL. | Mỗi domain khai báo `null_policy` và `default_label`. Pilot dùng `default=RETAIL`. Hệ quả: `UNMAPPED` không bao giờ xuất hiện, nên chỉ số độ phủ của `customer_type` vô nghĩa cho tới khi bỏ default. |
| C3 | §3.7 "có thêm `customer_type_std`" trong mart | Golden so `columns` theo thứ tự (§6.1), nên thêm cột public là FAIL. Nó còn đổi serving view. | Pilot để `_std` trong `lbl_*`. Đưa vào mart ở một bước riêng, khi harness đã có cờ cho phép thêm cột. |
| C4 | §3.5 toán tử | Thiếu `like`, `lt/lte/gt/gte`. `between [a,b)` không tương đương `<=` trên số thực. Không so được hai feature với nhau (`next_purchase_signal`: `recency_days >= avg_days_between_orders * 1.5`); đổi thành tỉ số thì lệch ở biên số thực. | Thêm toán tử. Luật dạng feature-so-feature thì thành feature boolean do code sản phẩm viết. Chấp nhận rằng một phần luật sẽ ở lại trong SQL. |
| C5 | §3.5 "AND trong một dòng" | Chưa định nghĩa ngữ nghĩa NULL. `bool_and` của DuckDB bỏ qua NULL, khác `AND` của SQL. | Đặc tả: engine đánh giá theo SQL 3 giá trị, giống `CASE WHEN`. |
| C6 | §3.2 `cardinality single` + FIRST | Không biểu diễn được cờ kiểu `is_us_gift_recipient` ("rule nhãn X có khớp không, bất kể ưu tiên"). | Output thêm `matched__<label>` hoặc list `matched_labels` (giống COLLECT), giữ 3 giá trị. |
| C7 | §6.4 "biến thể thành nhãn riêng hoặc domain riêng" | Biến thể có cùng tập nhãn nhưng khác luật và khác feature, nên **chỉ có thể là domain riêng**. "Nhãn riêng" không dùng được ở đây. | Quy ước `<domain>__<variant>`, xoá khi thống nhất. |
| C8 | §3.1 feature chỉ từ `std_*` | Không đúng byte được cho CROSSBORDER (khoá `Unknown` của fact, logic "(Unspecified)" của `dim_channels`). | Pilot cho phép feature đọc mart. Đích là `int_orders_resolved` (§B.1). |
| C9 | §4 domain registry "YAML hoặc seed" lúc compile | Dùng seed thì vỡ trên lake trống và trong bước `dbt parse` (§B.3). | Chỉ YAML. |
| C10 | §5.3 `primary_rule` = MAX_BY | `MAX_BY(discount_type, amount)` không tất định khi `amount` bằng nhau. Engine đổi plan SQL thì có thể lật kết quả, golden báo khác biệt giả. | Thêm tie-break **trước** khi chuyển domain discount (đổi số ở các dòng hoà, cần duyệt riêng). |
| C11 | §2/§6 nhận định | CROSSBORDER "3 định nghĩa": thực ra là 2 logic + 1 cờ. `value_group` "hai biến thể" (phase 4 điểm 1): `COALESCE(x,0) >= T` và `x >= T` cho cùng kết quả vì T > 0 và có ELSE, nên **tương đương về ngữ nghĩa**, một domain là đủ. Thứ tự ưu tiên ở R1/§3.2 sai (§A.1). | Sửa tài liệu. |
| C12 | §7 lý do đặt engine trước phase 6 | Phase 6 **không** dời luật. Phạm vi dbt của nó là HUG, US shipment, CRM, cashflow, overhead, seed FJ; luật duy nhất được nhắc tới là hook `dim_customers` (CROSSBORDER). | Xem #2 ở §D. |
| C13 | §3.7 `ruleset_version` | Chưa nói tác động lên model incremental. | Gắn với full-refresh (§B.2). |
| C14 | §4 "Google Sheet → seed" | Job ghi seed vào checkout prod đang bind-mount (tiền lệ `sheets/assets.py` L272) là rủi ro đã nằm trong bảng Risks của plan. | Đi qua lake thô (`gsheet_raw`) → source → `std_taxonomy_rule`. Validate bằng dbt test và trước khi nạp. Không ghi CSV. |

## D. Trả lời 6 quyết định ở §8

1. **Nhãn riêng + mã chuẩn bắt buộc: đồng ý.** Về kỹ thuật, đây chỉ là một bảng `taxonomy_label` cộng một test hàm, rẻ. Điều kiện: `_std` chưa vào mart public ở pilot (C3). Bộ mã chuẩn của `customer_type` chỉ chốt khi có dữ liệu doanh nghiệp thứ hai. Pilot neo CROSSBORDER vào `OTHER` tạm thời, vì việc này không đổi giá trị đang chạy.
2. **Đặt engine trước phase 6: không.** Thứ tự đề xuất: phase 4 (rút gọn) → phase 6 → **phase mới "engine MVP + pilot customer_type"** → phase 7.
   - Phase 6 chỉ dời file và hằng số (gate M), không đụng luật (C12). Chặn nó bằng một phase gate S rủi ro hơn là đảo ngược thứ tự an toàn.
   - Engine được lợi khi phase 6 đã xong: seed luật của tenant có sẵn chỗ ở `seeds/tenants/fine_japan/`, và luật CROSSBORDER/US là phần tenant cần đặt vào lớp "riêng doanh nghiệp".
   - "Tách SQL custom rồi phải tách lần nữa" không xảy ra, vì phase 6 không tách các khối CASE.
3. **Bỏ tách macro nguyên văn ở phase 4: đồng ý, với 3 điều kiện.**
   - (a) Sửa Acceptance Criteria #5 của `plan.md` ("mọi luật nằm trong `macros/taxonomy/`"). Nếu không, phase 4 không thể đóng.
   - (b) `TAXONOMY.md` ghi chính xác file:dòng và một hash nội dung của từng khối CASE, kèm kết luận "tương đương ngữ nghĩa / khác" (ví dụ `value_group`, C11). Đây là phần giá trị thật của bước macro, và làm được mà không cần macro.
   - (c) Thêm một check nhẹ vào `check_boundaries.py`: cảnh báo khi có khối CASE mới gán vào các cột domain đã kiểm kê, để kiểm kê không cũ đi trong lúc chờ engine.
   - Lý do: macro nguyên văn chỉ cho "một chỗ" về mặt vị trí file, còn biến thể vẫn là biến thể. Engine thay hình dạng từ CASE inline sang `LEFT JOIN lbl_*`, nên macro sẽ bị xoá chứ không được tái dùng.
   - Rủi ro chấp nhận: nếu engine hoãn quá một quý thì xét lại. Có thể làm macro chỉ cho các domain engine chưa tới, vì gate compiled-diff làm việc đó gần như không có rủi ro.
4. **Kênh nhiều trục / `order_purpose`: đồng ý về hướng, nhưng ngoài MVP.**
   - Cột mới trên `fact_orders` là thay đổi schema của bảng public, nên cần cờ "thêm cột" của harness (C3).
   - `order_purpose` cần subject `order` và feature từ nguồn + tag, nên cùng loại vòng phụ thuộc như `scope_*`. Làm sau `int_orders_resolved`.
5. **Restate mặc định, chỉ khoá kỳ cho kế toán: đồng ý về ngữ nghĩa**, nhưng phải nói rõ là chưa tự có (§B.2):
   - đổi `ruleset_version` thì full-refresh các model incremental phía sau;
   - quyết định lại ngữ nghĩa "entry bất biến" của `int_customer_entry_attributes`: khi restate, khách đổi loại sẽ rời bảng cohort.
   - `freeze_after_close` cần snapshot riêng. Để tới domain GL.
6. **Ai nhập luật: kết hợp.**
   - MVP: mình cấu hình bằng seed trong git, đi qua gate.
   - Sau này: nghiệp vụ sửa trên Google Sheet, và luật đi **qua lake thô → source dbt**, không ghi CSV seed (C14). Validator cú pháp chạy trước khi nạp; test dbt chạy lúc build.
   - Preview tác động (bước ④): chạy `lbl_<domain>` của nhánh luật mới so với bản hiện hành bằng `EXCEPT`. Không cần dựng cả gate.

## E. Ước lượng (một kỹ sư quen repo, chưa tính phase 4 rút gọn ~2d)

| Hạng mục | Ngày công |
|---|---|
| Schema seed luật/nhãn/canonical (column_types, layer, priority band) + registry YAML | 0.5 |
| Macro `taxonomy_label_model`: FIRST/UNIQUE/COLLECT, đánh giá 3 giá trị, `matched__<label>`, sinh UNION theo op, `ruleset_version` | 2 |
| `feat_customer_profile`, `feat_customer_orders` | 0.5 |
| Luật FJ thành dữ liệu cho 2 domain; nối vào `dim_customers`, `fact_orders`, `int_customer_benchmarks` | 1 |
| Test: hợp lệ hoá luật, single-row, accepted values, unit test tương đương 6+ ca biên | 1–1.5 |
| Gate S (golden + full-refresh + empty lake), điều tra khác biệt | 1–1.5 |
| Tài liệu (yêu cầu bắt buộc): `docs/architecture/taxonomy-engine.md`, `modules.md`, `TAXONOMY.md` | 1 |
| Deploy + theo dõi nightly + model đối chiếu song song, rồi gỡ | 0.5 |
| **Tổng** | **7.5–8.5 (làm tròn 7–9)** |

Chưa gồm: `int_orders_resolved`, thống nhất CROSSBORDER, cột `_std` trong mart, các domain khác. Mỗi domain kiểu ánh xạ/ngưỡng sau pilot tốn khoảng 0.5–1 ngày; domain discount tốn thêm phần tie-break của C10.

## Câu hỏi còn mở

1. Có chấp nhận cờ harness "cho phép thêm cột public" (để có `_std`), hay `_std` chỉ sống trong `lbl_*` / `entity_labels` cho tới Đợt 4?
2. Khi restate làm khách rời `int_customer_entry_attributes`: nghiệp vụ có muốn cohort đổi theo hay không?
3. Việc thống nhất CROSSBORDER làm đổi `scope_retail`/`scope_b2b` của các đơn của khách có đơn US. Ai duyệt, và có làm cùng `int_orders_resolved` không?

---

Status: DONE
Summary: Engine kiểu "một domain một model, sinh từ macro, luật join qua ref()" tái tạo đúng từng byte được `customer_type` (2 domain biến thể, toán tử `like`, đánh giá 3 giá trị, cờ `matched__crossborder`, feature thô). Compiled-diff không áp dụng nên cần thêm unit test tương đương. Khuyến nghị: không chặn phase 6, bỏ tách macro ở phase 4 kèm điều kiện, MVP + pilot khoảng 7–9 ngày.
Concerns: (1) Ba điểm thiết kế làm gate đỏ nếu làm theo nguyên văn: chuẩn hoá chuỗi, `UNKNOWN`, `_std` trong mart. (2) Thứ tự ưu tiên `customer_type` trong tài liệu sai so với code. (3) Restate không tự có với 17 model incremental. (4) `is_us_gift_recipient` NULL đang loại khách khỏi 2 action queue CRM; engine phải giữ nguyên hành vi này, còn sửa nó là quyết định nghiệp vụ riêng. (5) Muốn thống nhất CROSSBORDER/`scope_*` thì trước hết cần `int_orders_resolved` để tránh vòng `fact_orders`.

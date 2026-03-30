# Báo cáo Sự cố: Lỗi Out of Memory (OOM) DuckDB — stg_sapo_orders

## 1. Mô tả sự cố

Model `stg_sapo_orders` liên tục crash với lỗi:

```
Out of Memory Error: failed to allocate data of size 16.0 MiB (6.5 GiB/6.5 GiB used)
```

Hệ thống chạm trần `memory_limit: '7GB'` (≈ 6.5 GiB) trong profiles.yml.

**Source:** Parquet files chứa cột `payload` là raw JSON blob từ Sapo API (~KB-MB/row).

---

## 2. Lịch sử các lần fix

### Fix #1: GROUP BY + ANY_VALUE(payload) — THẤT BẠI (deployed)

**Commit:** `2a6d211`

Thay `QUALIFY ROW_NUMBER()` bằng `GROUP BY` + `ANY_VALUE(s.payload)`.

```sql
SELECT s.entity_id, ANY_VALUE(s.payload) as payload, ...
GROUP BY s.entity_id, s.event_timestamp, s.ingest_method
```

**Tại sao thất bại:** `ANY_VALUE(s.payload)` lưu toàn bộ JSON blob vào hash table của GROUP BY. Hash table vượt 6.5GB.

---

### Fix #2: GROUP BY + ANY_VALUE(json_extract_string(...)) — THẤT BẠI (deployed)

Thay `ANY_VALUE(s.payload)` bằng `ANY_VALUE(json_extract_string(s.payload, ...))` cho 50+ fields.

```sql
ANY_VALUE(json_extract_string(s.payload, '$.id')) as order_id, ...
GROUP BY s.entity_id, s.event_timestamp, s.ingest_method
```

**Tại sao thất bại:** Hash table nhẹ hơn nhưng model vẫn scan source 3 lần. Mỗi scan decompress toàn bộ payload column từ parquet vào RAM. GROUP BY hash table (~1-2GB) + parquet decompression (~1GB/scan) × 2 payload scans = vượt 6.5GB.

**Bài học:** GROUP BY hash table là overhead ẩn (~1-2GB) mà có thể tránh được.

---

### Fix #3: Loại bỏ GROUP BY + Giảm source scan + Hạ memory_limit — CHƯA ĐỦ

**Thay đổi:**

| Thay đổi | Chi tiết |
|---|---|
| Giảm source scan từ 3 xuống 2 | Merge `pre_dedup_source` + `json_parsed` thành 1 CTE `extracted` |
| **Loại bỏ GROUP BY hoàn toàn** | Bỏ hash table (~1-2GB). Exact duplicates do ROW_NUMBER xử lý |
| Hạ memory_limit 7GB → 4GB | Buộc DuckDB spill to disk sớm hơn (DuckDB docs recommendation) |
| Bỏ ANY_VALUE wrappers | Không cần khi không có GROUP BY |

**Memory budget ước tính:**

| Operator | RAM |
|---|---|
| Parquet scan buffer (1 row group) | ~500MB |
| Hash table cho INNER JOIN (winner_keys) | ~30MB |
| ~~Hash table cho GROUP BY~~ | ~~1-2GB~~ → **0** |
| Sort buffer cho ROW_NUMBER (extracted strings) | ~1-1.5GB |
| **Tổng peak** | **~2GB** (dưới giới hạn 4GB) |

**Kết quả:** Giảm memory đáng kể nhưng vẫn rủi ro với data lớn — 1 model = 1 query = tất cả operators cùng pipeline.

---

### Fix #4 (RESOLVED ✓): Tách src_/stg_ — 2 model = 2 memory budget

**Ngày deploy:** 2026-03-30

**Giải pháp:** Tách `stg_sapo_orders` (1 model làm tất cả) thành 2 model tuần tự:

| Model | Materialization | Vai trò | unique_key |
|---|---|---|---|
| `src_sapo_orders` | **INCREMENTAL** (delete+insert) | Extract JSON + tech dedup (entity_id) + biz dedup (order_id) | `order_id` |
| `stg_sapo_orders` | **VIEW** | Enrichment joins only (ref_order_sources, ref_payment_methods, ref_branch_locations) | — |

**Tại sao gom cả biz dedup vào src_ (không để ở stg_):**
- Biz dedup (ROW_NUMBER by order_id) chạy trên **flat extracted data** — payload đã discard → memory negligible
- Nếu để biz dedup ở stg_, các unnest models (stg_sapo_order_items, stg_sapo_payments, stg_sapo_fulfillments) đọc từ src_ sẽ thấy **nhiều versions** của cùng 1 order → data inconsistency
- `unique_key='order_id'` cho phép incremental delete+insert đúng semantic: 1 row per order

**Thay đổi chi tiết:**

| File | Trước | Sau |
|---|---|---|
| `src_sapo_orders.sql` | VIEW, SELECT *, giữ payload, dedup entity_id | INCREMENTAL, extract 50+ JSON fields + 3 nested arrays, tech dedup + biz dedup, **không payload** |
| `stg_sapo_orders.sql` | INCREMENTAL, extract + dedup + enrich (nặng) | VIEW, enrichment joins only (rất nhẹ) |
| `stg_sapo_order_items.sql` | Unnest từ `json_extract_string(payload, ...)` | Unnest từ cột `order_line_items_json` (đã extract sẵn) |
| `stg_sapo_payments.sql` | Unnest từ payload, **bug duplicate unnest** | Unnest từ `payments_json`, **fix bug** |
| `stg_sapo_fulfillments.sql` | Unnest từ payload, **bug duplicate unnest** | Unnest từ `fulfillments_json`, **fix bug** |
| `profiles.yml` | memory_limit: 4GB | memory_limit: 5GB |

**Memory flow sau fix:**

```
Model 1: src_sapo_orders (INCREMENTAL)
  ├── Parquet scan (7-day window, có payload)     ~500MB
  ├── ROW_NUMBER tech dedup (sort trên keys nhẹ)  ~200MB
  ├── JSON extraction (streaming, payload discard) ~300MB
  └── ROW_NUMBER biz dedup (flat data, no payload) ~100MB
  Peak: ~1.1GB
  → Ghi disk → Giải phóng TOÀN BỘ RAM

Model 2: stg_sapo_orders (VIEW)
  ├── Đọc từ src_ table (flat, no payload)        ~200MB
  └── LEFT JOIN 4 ref tables                       ~10MB
  Peak: ~210MB
```

**Kết quả:**
- `dbt build` full pipeline: **109/109 PASS**, 0 errors
- `src_sapo_orders` full refresh: 12s, không OOM
- `src_sapo_orders` incremental: 3s
- 70 data tests pass (unique, not_null, relationships, accepted_values)

---

## 3. Kế hoạch dài hạn: Kiến trúc 4-layer src_ → stg_ → std_ → marts

### 3.1 Insight cốt lõi: 1 dbt model = 1 memory budget

Một file `.sql` trong dbt, dù có bao nhiêu CTE (WITH), **biên dịch thành 1 câu SQL duy nhất** gửi cho DuckDB. Các CTE KHÔNG được materialize ra disk giữa chừng. Tất cả operator (parquet scan, hash join, sort) chạy **đồng thời trong cùng 1 pipeline**, RAM cộng dồn.

```
Parquet Scan (~1GB) ──► Hash Join (~30MB) ──► Sort/ROW_NUMBER (~1GB)
                                                    │
                              Tất cả cùng lúc = ~2GB peak
```

**Tách thành 2 model = 2 query tuần tự:**
- Model 1 chạy xong → ghi disk → giải phóng TOÀN BỘ RAM
- Model 2 bắt đầu → memory budget riêng
- Peak = **max(model1, model2)** thay vì **sum()**

Đây là lý do kỹ thuật buộc phải tách `src_` và `stg_` — không phải chỉ về naming.

### 3.2 Vai trò 4 layers

| Layer | Vai trò | Đọc từ | Materialization | Biết gì |
|---|---|---|---|---|
| **`src_`** | Extract JSON + tech dedup + biz dedup + **tích lũy** | `source()` (parquet) | **INCREMENTAL** | Cấu trúc JSON, dedup rules |
| **`stg_`** | Enrichment joins (ref tables) | `src_` | VIEW | Ref tables mapping |
| **`std_`** | Normalize + status mapping + **standard interface** | `stg_` | VIEW | Business semantics (COMPLETED, SHIPPED, etc.) |
| **`marts`** | Dimensional models | `std_` | EXTERNAL (parquet) | Star schema |

**Tại sao giữ `std_` riêng (không gộp vào `stg_` hay `int_`):**
- `std_` là **standard interface** — contract duy nhất mà tất cả marts nên đọc
- Chứa business normalization phức tạp (VD: hybrid fulfillment logic 15-line CASE kết hợp financial_status + packed_status + received_status)
- Nếu thêm source system khác (không phải Sapo), `std_` là nơi normalize vào cùng schema
- `int_` dùng cho cross-entity transformations (VD: `int_customer_metrics` tính RFM từ fact_orders)

**Tại sao `src_` và `stg_` là 2 layer riêng (không gộp):**
- `src_` xử lý phần **I/O nặng** (đọc parquet, decompress payload, extract JSON, cả tech + biz dedup) → cần materialize để tích lũy
- `stg_` xử lý phần **logic nhẹ** (enrichment joins với ref tables) → đọc từ bảng đã materialize, không OOM risk
- Nếu gộp vào 1 model: tất cả operator chạy cùng lúc, RAM cộng dồn → OOM
- `src_` phục vụ nhiều consumer: `stg_sapo_order_items`, `stg_sapo_payments`, `stg_sapo_fulfillments` đều unnest từ `src_`
- Biz dedup nằm ở `src_` (không phải `stg_`) để đảm bảo unnest models chỉ thấy 1 version/order → data consistency

**Khi nào cần thêm step trong cùng 1 layer (hiếm):** dùng double underscore: `stg_sapo_orders__deduped.sql`. Nhưng thường 3 prefix (src_, stg_, std_) đã đủ cover.

### 3.3 Dependency graph (trạng thái 2026-03-30)

**HIỆN TẠI (vấn đề):**
```
source('sapo_raw', 'order')
    ├──► src_sapo_orders (VIEW — dedup, GIỮ payload)
    │        ├──► stg_sapo_order_items → std_order_items → fact_sales, dim_products
    │        ├──► stg_sapo_payments → std_payments (KHÔNG AI DÙNG)
    │        │                      → fact_payments (đọc stg_ trực tiếp, BỎ QUA std_!)
    │        └──► stg_sapo_fulfillments → std_fulfillments (KHÔNG AI DÙNG)
    │
    └──► stg_sapo_orders (INCREMENTAL — dedup RIÊNG + extract + enrich, KHÔNG dùng src_!)
             └──► std_orders → fact_orders, fact_sales, dim_geography, dim_promotions

source('sapo_raw', 'customer')
    ├──► src_sapo_customers (VIEW — KHÔNG AI DÙNG... nhưng sẽ dùng sau)
    └──► stg_sapo_customers (INCREMENTAL) → std_customers → dim_customers_base

source('sapo_raw', 'account')
    ├──► src_sapo_accounts (VIEW — KHÔNG AI DÙNG... nhưng sẽ dùng sau)
    └──► stg_sapo_accounts (INCREMENTAL) → dim_staff (BỎ QUA std_!)
```

Vấn đề:
- `src_` và `stg_` đọc cùng source độc lập (scan 2 lần)
- `src_` là VIEW giữ payload → mỗi query downstream re-decompress payload
- `fact_payments` và `dim_staff` bỏ qua `std_` layer
- `std_payments` và `std_fulfillments` tồn tại nhưng không ai dùng

**ĐỀ XUẤT:**
```
source('sapo_raw', 'order')
    │
    ▼
src_sapo_orders (INCREMENTAL — extract ALL + tech dedup + biz dedup, unique_key=order_id)
    │  Output: flat columns + order_line_items_json, payments_json, fulfillments_json
    │  KHÔNG CÒN payload
    │
    ├──► stg_sapo_order_items (VIEW — unnest order_line_items_json)
    ├──► stg_sapo_payments (VIEW — unnest payments_json)
    ├──► stg_sapo_fulfillments (VIEW — unnest fulfillments_json)
    │
    ▼
stg_sapo_orders (VIEW — enrichment joins only, KHÔNG dedup)
    │
    ▼
std_orders (VIEW — status mapping + normalize)
    │
    ├──► fact_orders
    ├──► fact_sales (+ std_order_items)
    ├──► dim_geography
    └──► dim_promotions

stg_sapo_order_items → std_order_items → fact_sales, dim_products, dim_product_types
stg_sapo_payments → std_payments → fact_payments (fix: đọc std_ thay vì stg_)
stg_sapo_fulfillments → std_fulfillments

source('sapo_raw', 'customer')
    → src_sapo_customers (INCREMENTAL — extract + tech dedup)
        → stg_sapo_customers (VIEW — cleaning)
            → std_customers → dim_customers_base

source('sapo_raw', 'account')
    → src_sapo_accounts (INCREMENTAL — extract + tech dedup)
        → stg_sapo_accounts (VIEW — cleaning)
            → std_accounts (MỚI) → dim_staff
```

### 3.4 Mapping model chi tiết

| Model | Trước | Sau (2026-03-30) | Trạng thái |
|---|---|---|---|
| `src_sapo_orders` | VIEW, giữ payload, dedup entity_id | INCREMENTAL, extract JSON, tech+biz dedup, unique_key=order_id, **không payload** | ✅ DONE |
| `stg_sapo_orders` | INCREMENTAL, extract + dedup + enrich | VIEW, enrichment joins only | ✅ DONE |
| `stg_sapo_order_items` | Unnest từ payload | Unnest từ `order_line_items_json`, fix bug | ✅ DONE |
| `stg_sapo_payments` | Unnest từ payload, bug duplicate | Unnest từ `payments_json`, fix bug | ✅ DONE |
| `stg_sapo_fulfillments` | Unnest từ payload, bug duplicate | Unnest từ `fulfillments_json`, fix bug | ✅ DONE |
| `std_orders` | VIEW | VIEW (giữ nguyên) | ✅ Không cần đổi |
| `src_sapo_customers` | VIEW | INCREMENTAL extraction | ⏳ TODO |
| `src_sapo_accounts` | VIEW | INCREMENTAL extraction | ⏳ TODO |
| — | — | `std_accounts` (MỚI) | ⏳ TODO |
| `fact_payments` | Đọc stg_ trực tiếp | Đọc std_payments | �� TODO |
| `dim_staff` | Đọc stg_ trực tiếp | Đọc std_accounts | ⏳ TODO |

### 3.5 Inconsistencies còn lại (TODO)

1. **`fact_payments`** đọc `stg_sapo_payments` trực tiếp → đổi sang đọc `std_payments`
2. **`dim_staff`** đọc `stg_sapo_accounts` trực tiếp → tạo `std_accounts`, đổi dim_staff đọc qua std_
3. **`std_payments`** và **`std_fulfillments`** tồn tại nhưng không ai dùng → kết nối vào marts
4. **`src_sapo_customers`** và **`src_sapo_accounts`** vẫn là VIEW → cần refactor thành INCREMENTAL extraction

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

### Fix #3 (hiện tại): Loại bỏ GROUP BY + Giảm source scan + Hạ memory_limit — CHƯA VERIFY

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
| **`src_`** | Extract JSON + tech dedup + **tích lũy** | `source()` (parquet) | **INCREMENTAL** | Cấu trúc JSON của source system |
| **`stg_`** | Business dedup + enrichment | `src_` | VIEW hoặc incremental | Quy tắc dedup, ref tables |
| **`std_`** | Normalize + status mapping + **standard interface** | `stg_` | VIEW | Business semantics (COMPLETED, SHIPPED, etc.) |
| **`marts`** | Dimensional models | `std_` | EXTERNAL (parquet) | Star schema |

**Tại sao giữ `std_` riêng (không gộp vào `stg_` hay `int_`):**
- `std_` là **standard interface** — contract duy nhất mà tất cả marts nên đọc
- Chứa business normalization phức tạp (VD: hybrid fulfillment logic 15-line CASE kết hợp financial_status + packed_status + received_status)
- Nếu thêm source system khác (không phải Sapo), `std_` là nơi normalize vào cùng schema
- `int_` dùng cho cross-entity transformations (VD: `int_customer_metrics` tính RFM từ fact_orders)

**Tại sao `src_` và `stg_` là 2 layer riêng (không gộp):**
- `src_` xử lý phần **I/O nặng** (đọc parquet, decompress payload, extract JSON) → cần materialize để tích lũy
- `stg_` xử lý phần **logic nhẹ** (business dedup, join ref tables) → đọc từ bảng đã materialize, không OOM risk
- Nếu gộp vào 1 model: tất cả operator chạy cùng lúc, RAM cộng dồn → OOM
- `src_` cũng phục vụ nhiều consumer: `stg_sapo_order_items`, `stg_sapo_payments`, `stg_sapo_fulfillments` đều unnest từ `src_`

**Khi nào cần thêm step trong cùng 1 layer (hiếm):** dùng double underscore: `stg_sapo_orders__deduped.sql`. Nhưng thường 3 prefix (src_, stg_, std_) đã đủ cover.

### 3.3 Dependency graph hiện tại vs đề xuất

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
src_sapo_orders (INCREMENTAL TABLE — extract ALL + tech dedup + tích lũy)
    │  Output: flat columns + order_line_items_json, payments_json, fulfillments_json
    │  KHÔNG CÒN payload
    │
    ├──► stg_sapo_order_items (VIEW — unnest order_line_items_json)
    ├──► stg_sapo_payments (VIEW — unnest payments_json)
    ├──► stg_sapo_fulfillments (VIEW — unnest fulfillments_json)
    │
    ▼
stg_sapo_orders (VIEW — biz dedup by order_id + enrichment)
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

| Model hiện tại | Đề xuất | Thay đổi |
|---|---|---|
| `src_sapo_orders` (VIEW, giữ payload) | `src_sapo_orders` (INCREMENTAL, extract JSON, không payload) | Vai trò mới: materialized extraction + tích lũy |
| `stg_sapo_orders` (INCREMENTAL, extract + dedup + enrich) | `stg_sapo_orders` (VIEW, biz dedup + enrich only) | Đơn giản hóa, đọc từ src_ |
| `std_orders` (VIEW) | `std_orders` (VIEW) | Giữ nguyên, hấp thụ thêm enrichment nếu cần |
| `stg_sapo_order_items` (VIEW, đọc src_) | `stg_sapo_order_items` (VIEW, đọc src_) | Đổi unnest source: payload → order_line_items_json |
| `stg_sapo_payments` (VIEW, đọc src_) | `stg_sapo_payments` (VIEW, đọc src_) | Đổi unnest source: payload → payments_json |
| `stg_sapo_fulfillments` (VIEW, đọc src_) | `stg_sapo_fulfillments` (VIEW, đọc src_) | Đổi unnest source: payload → fulfillments_json |
| `src_sapo_customers` (VIEW) | `src_sapo_customers` (INCREMENTAL, extract) | Vai trò mới: materialized extraction |
| `src_sapo_accounts` (VIEW) | `src_sapo_accounts` (INCREMENTAL, extract) | Vai trò mới: materialized extraction |
| — | `std_accounts` (MỚI) | Fix inconsistency: dim_staff đọc qua std_ |
| `fact_payments` (đọc stg_) | `fact_payments` (đọc std_payments) | Fix inconsistency: đi qua std_ layer |

### 3.5 Inconsistencies cần fix

1. **`fact_payments`** đọc `stg_sapo_payments` trực tiếp → đổi sang đọc `std_payments`
2. **`dim_staff`** đọc `stg_sapo_accounts` trực tiếp → tạo `std_accounts`, đổi dim_staff đọc qua std_
3. **`std_payments`** và **`std_fulfillments`** tồn tại nhưng không ai dùng → kết nối vào marts

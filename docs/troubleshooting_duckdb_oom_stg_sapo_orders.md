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

## 3. Kế hoạch dài hạn: Tách src_ → stg_ → std_

### Tại sao cần tách

Một dbt model = một SQL query = **một memory budget**. Các CTE trong cùng 1 model KHÔNG được materialize giữa chừng. Tất cả operator chạy đồng thời, RAM cộng dồn.

Tách thành 2 model = 2 query tuần tự = **memory peak = max() thay vì sum()**.

### Kiến trúc đề xuất

```
source('sapo_raw', 'order')
    │
    ▼
src_sapo_orders (INCREMENTAL TABLE)
    │  Extract JSON + tech dedup + tích lũy
    │  Source chỉ scan cho data mới → OOM-safe
    │  Output: flat columns + nested JSON arrays (line_items, payments, fulfillments)
    │
    ├──► stg_sapo_order_items (VIEW — unnest order_line_items_json)
    ├──► stg_sapo_payments (VIEW — unnest payments_json)
    ├──► stg_sapo_fulfillments (VIEW — unnest fulfillments_json)
    │
    ▼
stg_sapo_orders (VIEW)
    │  Biz dedup (order_id) + enrichment (ref tables)
    │
    ▼
std_orders (VIEW)
    │  Status mapping + normalize + canonical schema
    │
    ▼
fact_orders, fact_sales, ...
```

### Mapping model hiện tại → đề xuất

| Hiện tại | Đề xuất | Thay đổi |
|---|---|---|
| `src_sapo_orders` (VIEW, giữ payload) | `src_sapo_orders` (INCREMENTAL, extract JSON, không payload) | Vai trò mới: materialized extraction |
| `stg_sapo_orders` (INCREMENTAL, extract + dedup + enrich) | `stg_sapo_orders` (VIEW, biz dedup + enrich only) | Đơn giản hóa: đọc từ src_ |
| `std_orders` (VIEW) | `std_orders` (VIEW) | Giữ nguyên |
| `stg_sapo_order_items` (đọc từ src_) | `stg_sapo_order_items` (đọc từ src_) | Giữ nguyên |
| `src_sapo_customers` | `src_sapo_customers` (INCREMENTAL, extract) | Vai trò mới |
| `src_sapo_accounts` | `src_sapo_accounts` (INCREMENTAL, extract) | Vai trò mới |

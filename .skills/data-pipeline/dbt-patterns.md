# dbt Patterns & Lessons Learned

## Project Configuration

### profiles.yml — Critical Settings

```yaml
sapo_warehouse:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "{{ env_var('DBT_DATA_LAKE_PATH') }}/sapo_warehouse.duckdb"
      threads: 1                   # KHÔNG dùng > 1 — high threads = high buffer = OOM
      extensions: [parquet, httpfs]
      external_root: "{{ env_var('DBT_EXPORT_PATH') }}"
      settings:
        memory_limit: '5GB'        # Thấp hơn container limit → force spill-to-disk
        threads: 1
        preserve_insertion_order: false
        TimeZone: 'Asia/Ho_Chi_Minh'
```

**Lý do các setting:**
- `memory_limit=5GB` < container memory → DuckDB spill to disk thay vì crash
- `threads=1` → sequential processing, tránh concurrent buffer overflow
- `preserve_insertion_order=false` → optimizer tự do reorder, nhanh hơn

### dbt_project.yml — Materialization by Layer

```yaml
models:
  sapo_warehouse:
    +materialized: view              # Default (lightweight)

    staging:
      +schema: staging
      +materialized: view            # Override per model nếu cần incremental
      +tags: ["otp"]

    marts:
      +schema: marts
      +materialized: external        # Parquet output
      +options:
        format: "parquet"
      +tags: ["olap"]
      +on_schema_change: sync_all_columns  # Không cần full-refresh khi thêm column

vars:
  external_root: "{{ env_var('DBT_EXPORT_PATH') }}"
```

---

## 5-Hop Transformation Flow

| Layer | Prefix | Materialization | Purpose |
|-------|--------|-----------------|---------|
| **Source** | `src_` | `incremental` (delete+insert) | JSON extract + dedup từ raw Parquet. Output flat columns, no payload. |
| **Staging** | `stg_` | `view` | Enrichment joins (ref tables), unnest nested arrays. Đọc từ src_ (no payload). |
| **Standard** | `std_` | `view` | Golden layer: consolidate multi-source, normalize status/field names, cast types. |
| **Intermediate** | `int_` | `ephemeral` hoặc `table` | Metrics aggregation (CLV, RFM). **KHÔNG export** ra serving. |
| **Marts (Dim)** | `dim_` | `external` + `location=rolling` | BI dimension tables. Surrogate keys. |
| **Marts (Fact)** | `fact_` | `external` + `location=rolling` | BI fact tables. FK references to dims. |

---

## Lesson 1: Two-Phase Dedup (OOM-Safe)

**Vấn đề:** src_ model đọc raw Parquet có payload JSON lớn. Query đơn giản (dedup + extract + biz dedup) trong 1 SQL → single memory budget → OOM.

**Giải pháp:** Tách làm 2 phase trong cùng model.

```sql
-- Phase 1: Tech dedup (entity_id) — sort trên lightweight keys, payload chỉ carry
deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY event_timestamp DESC,
                CASE ingest_method
                    WHEN 'webhook' THEN 3
                    WHEN 'history_log' THEN 2
                    ELSE 1
                END DESC
        ) AS rn
    FROM raw_data
),
-- JSON extraction: payload DISCARD sau CTE này
extracted AS (
    SELECT entity_id, event_timestamp,
           json_extract_string(payload, '$.id') AS biz_key,
           json_extract_string(payload, '$.modified_on') AS modified_on,
           -- ... các fields scalar
    FROM deduped WHERE rn = 1
)
-- Phase 2: Business dedup — chạy trên flat data, KHÔNG có payload
-- modified_on first (entity timestamp = source of truth), event_timestamp second
SELECT * FROM extracted
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY biz_key
    ORDER BY
        try_cast(json_extract_string(payload, '$.modified_on') AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method WHEN 'webhook' THEN 3 WHEN 'history_log' THEN 2 ELSE 1 END DESC
) = 1
```

**Memory peak thực tế:** ~1.1GB (vs crash lúc trước) — well under 5GB limit.

---

## Lesson 2: src_/stg_ Split (Primary OOM Fix)

**Vấn đề:** Single model làm tất cả (extract + dedup + enrichment joins) = single SQL = single memory budget. CTE không materialize lên disk.

**Giải pháp:** Tách 2 model riêng biệt.

```
src_sapo_orders.sql   (INCREMENTAL)    → flat data, no payload, ~1.1GB peak
        ↓
stg_sapo_orders.sql   (VIEW)           → enrichment joins, ~210MB peak
```

**Memory peak = max(src_, stg_) thay vì sum()** — mỗi model là một query riêng, DuckDB giải phóng memory giữa các model.

**Rule of thumb:**
- src_ = heavy extraction + dedup + payload work
- stg_ = lightweight joins + enrichment
- Không bao giờ làm enrichment trong src_
- Không bao giờ extract JSON trong stg_

---

## Lesson 3: Incremental Filter bằng `_dlt_load_id` (thay 7-Day Lookback)

**Vấn đề:** Events từ webhook hoặc history_log có thể đến sau batch sync 1-5 ngày. Standard incremental (`WHERE ts > MAX(ts)`) bỏ sót. Nghiêm trọng hơn: full-refresh history_log tạo record với `event_timestamp` cũ nhưng `_dlt_load_id` mới — filter theo `event_timestamp` hoàn toàn bỏ sót chúng.

**Giải pháp:**
```sql
{% set existing_cols = (adapter.get_columns_in_relation(this) | map(attribute='name') | list) if is_incremental() else [] %}

WITH
{% if is_incremental() %}
_cursor AS (
    {% if '_dlt_load_id' in existing_cols %}
    SELECT COALESCE(MAX(_dlt_load_id), '') AS max_load_id FROM {{ this }}
    {% else %}
    SELECT '' AS max_load_id
    {% endif %}
),
{% endif %}
raw_data AS (
    SELECT ... FROM {{ source('sapo_raw', 'entity') }}
    {% if is_incremental() %}
    WHERE _dlt_load_id > (SELECT max_load_id FROM _cursor)
    {% endif %}
),
```

**3 bẫy DuckDB khi dùng `_dlt_load_id` incremental filter:**
1. **Aggregate trong WHERE subquery** — DuckDB reject `MAX()` inside WHERE subquery trên `read_parquet()` source. Fix: tách vào `_cursor` CTE.
2. **Column chưa tồn tại trong table cũ** — table materialized trước khi thêm `_dlt_load_id` vào SELECT. Fix: `adapter.get_columns_in_relation(this)` check compile-time, fallback `''` (reprocess all).
3. **UNION ALL column mismatch** — business dedup UNION ALL `extracted` (có `_dlt_load_id`) với `{{ this }}` (không có). Fix: guard UNION ALL bằng `'_dlt_load_id' in existing_cols`.

**Kết hợp `on_schema_change='append_new_columns'`** trong config → first run after migration tự heal: cursor='' + skip UNION ALL → reprocess all → column added → subsequent runs normal.

**Lý do dùng `_dlt_load_id`:** `_dlt_load_id` tăng đơn điệu theo từng dlt load (format `{unix_timestamp}.{sequence}`) — catches all new data regardless of `event_timestamp`. `event_timestamp` filter bỏ sót late-arriving data từ full-refresh hoặc history_log backfill.

**Trade-off:**
- `_dlt_load_id` filter chính xác hơn 7-day lookback — không bỏ sót, không scan thừa
- `delete+insert` strategy handle duplicates khi có data overlap
- Full refresh vẫn process toàn bộ — nếu OOM thì tăng `memory_limit` tạm thời

---

## Lesson 4: Ingest Method Priority khi Dedup

```sql
CASE ingest_method
    WHEN 'webhook'     THEN 3   -- Real-time event, mới nhất
    WHEN 'history_log' THEN 2   -- Gap-fill từ audit log
    ELSE 1                      -- batch_sync (có thể bị stale nhất); 'text' là legacy alias của batch_sync, cũng về ELSE
END DESC
```

**Lý do:**
- Webhook bắn real-time → fresh nhất
- History_log catch những events mà batch bỏ sót
- Batch sync scheduled → có thể stale đến vài giờ
- `'text'` là legacy alias của `batch_sync` — không cần case riêng, ELSE clause đã cover

Dùng trong ROW_NUMBER() ORDER BY phase tech dedup.

---

## Lesson 5: Rolling Location cho Marts (CRITICAL)

**Bug thực tế:** Mart model thiếu `location` → serving script báo "Empty folder" và drop view → Metabase dashboard trống.

**Root cause:** Global config `materialized: external` đúng, nhưng **path logic nằm trong macro** `get_rolling_location()`. Không khai báo trong model config → dbt default vào internal path → serving script không tìm thấy.

**Fix: MỌI mart model phải có:**
```sql
{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}
```

**Macro:**
```sql
{%- macro get_rolling_location() -%}
  {{ env_var('DBT_EXPORT_PATH') | replace('/rolling', '') }}/rolling/{{ this.name }}/{{ this.name }}_{{ run_started_at.strftime('%Y%m%d%H%M%S') }}.parquet
{%- endmacro -%}
```

**Output:** `rolling/dim_customers/dim_customers_20260407120000.parquet`

Timestamp-versioned → mỗi dbt run tạo file mới → rolling self-refresh view pick up latest → zero-downtime swap.

---

## Lesson 6: Circular Dependency Breaking

**Vấn đề:** `dim_customers` cần CLV/RFM metrics từ `fact_orders`. `fact_orders` cần `customer_key` từ `dim_customers`. → circular.

**Giải pháp:** 3-table split.
```
dim_customers_base.sql  (customer_key + profile, KHÔNG export)
        ↓
fact_orders.sql         (uses dim_customers_base.customer_key)
        ↓
int_customer_metrics.sql (aggregates from fact_orders)
        ↓
dim_customers.sql       (joins base + metrics, EXPORTS to rolling)
```

---

## Lesson 7: Unknown Key Handling

Missing dimension references sẽ làm fact rows bị drop khi inner join. Solution: UNION một row "Unknown" vào mỗi dim.

```sql
-- dim_customers.sql
SELECT
    {{ dbt_utils.generate_surrogate_key(['customer_id']) }} as customer_key,
    customer_id,
    name
FROM {{ ref('std_customers') }}

UNION ALL

SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as customer_key,
    'Unknown' as customer_id,
    'Unknown' as name
```

**Fact table:** COALESCE để fallback về Unknown key:
```sql
COALESCE(dc.customer_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as customer_key
```

---

## Lesson 8: sources.yml với Hive Partitioning

```yaml
sources:
  - name: sapo_raw
    schema: main
    meta:
      external_location: "read_parquet(
        '{{ env_var('DBT_DATA_LAKE_PATH') }}/sapo_raw/{name}/ingest_method=*/**/*.parquet',
        hive_partitioning=1,
        union_by_name=true
      )"
    tables:
      - name: order
      - name: customer
```

**Key patterns:**
- `{name}` auto-map với table name
- `ingest_method=*/**/*.parquet` — recursive glob (bypass `_delta_log`)
- `hive_partitioning=1` — đọc partition values từ folder names (year, month)
- `union_by_name=true` — safe union nếu schema evolution

---

## Lesson 9: Post-Hook Pattern (Alternative Export)

Thay cho `materialized: external`, có thể dùng post-hook để COPY sau khi dbt build:
```sql
{{ config(
    materialized='table',
    post_hook=[
        "COPY (SELECT * FROM {{ this }}) TO '{{ get_rolling_location() }}' (FORMAT PARQUET)"
    ]
) }}
```

**Khi nào dùng:** model cần query internal table sau đó (testing, dbt docs), nhưng vẫn cần export ra rolling.

---

## Lesson 10: JSON Extraction — Coalesce Fallbacks

API response có thể đặt field ở nhiều vị trí (root level hoặc nested). Cứng 1 path → null khi API thay structure.

```sql
-- BAD: fragile
json_extract_string(payload, '$.assignee.full_name') as salesperson_name

-- GOOD: robust with fallback chain
coalesce(
    json_extract_string(payload, '$.assignee.full_name'),
    json_extract_string(payload, '$.assignee.name'),
    json_extract_string(payload, '$.account.full_name')
) as salesperson_name
```

---

## Lesson 11: Testing Strategy theo Layer

| Layer | Tests bắt buộc |
|-------|---------------|
| `src_` | `unique` + `not_null` trên biz_key |
| `stg_` | `not_null` trên PKs (lightweight) |
| `std_` | `unique` + `not_null` + `accepted_values` cho status fields |
| `dim_` | `unique` + `not_null` trên surrogate key |
| `fact_` | `relationships` test tới tất cả dimension keys |

---

## Lesson 12: Reference Seeds Pattern

```
seeds/
├── ref_order_sources.csv      # Channel/source mapping
├── ref_brands.csv             # Vendor → brand normalization
├── ref_payment_methods.csv
└── properties.yml             # Column type declarations
```

**seeds/properties.yml:**
```yaml
seeds:
  - name: ref_order_sources
    config:
      column_types:
        id: integer
        is_generic_source: boolean
        mapping_tag: varchar
```

**Usage trong stg_:**
```sql
LEFT JOIN {{ ref('ref_order_sources') }} s ON o.source_id = s.id
```

---

## Lesson 13: Partition Pruning với Hive Partitioning

Raw Parquet được partition bởi `year/month` (derived từ `modified_on` trong dlt envelope). DuckDB với `hive_partitioning=1` tự động skip partition folders không match WHERE clause → giảm I/O 90-99% cho incremental runs.

**Enable partition pruning:**

```sql
-- sources.yml đã có hive_partitioning=1
-- src_ model chỉ cần thêm filter theo partition column:

WITH raw_data AS (
    SELECT * FROM {{ source('sapo_raw', 'order') }}
    WHERE year >= '2025'  -- Partition pruning — DuckDB skip year=2024/ và cũ hơn
    {% if is_incremental() %}
      AND event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})
    {% endif %}
)
```

**Quan trọng:** `year` và `month` là STRING (từ dlt envelope), không phải int. Filter đúng type:
```sql
WHERE year >= '2025' AND month >= '1'  -- Đúng, string comparison
WHERE year >= 2025                      -- SAI, cast mismatch
```

**Verify pruning:** `EXPLAIN ANALYZE` — xem `parquet_scan` có skip folders không.

---

## Lesson 14: Generated Time Dimension Pattern (SQL, không CSV)

**Pattern:** Tạo `dim_time` (minute-grain, 1440 rows/day) bằng SQL generator, KHÔNG dùng CSV seed. Cho phép thêm/thay đổi flag columns mà không cần regenerate CSV.

```sql
-- dim_time.sql
{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

WITH minutes AS (
    -- Generate 1440 rows (24h × 60min)
    SELECT range AS minute_of_day
    FROM range(0, 1440)
),
enriched AS (
    SELECT
        minute_of_day                                    AS time_key,      -- 0-1439
        (minute_of_day / 60)::INT                        AS hour_of_day,   -- 0-23
        (minute_of_day % 60)::INT                        AS minute_of_hour,-- 0-59
        LPAD((minute_of_day / 60)::TEXT, 2, '0') || ':'
            || LPAD((minute_of_day % 60)::TEXT, 2, '0')  AS time_label,    -- "09:30"

        -- Business hour flags — CUSTOMIZE theo business của bạn
        CASE
            WHEN (minute_of_day / 60) BETWEEN 9 AND 16 THEN TRUE
            ELSE FALSE
        END                                              AS is_business_hour,

        -- Peak hour flags — CUSTOMIZE (ở đây ví dụ lunch + dinner rush)
        CASE
            WHEN (minute_of_day / 60) BETWEEN 11 AND 13 THEN TRUE  -- lunch
            WHEN (minute_of_day / 60) BETWEEN 16 AND 18 THEN TRUE  -- dinner
            ELSE FALSE
        END                                              AS is_peak_hour,

        -- Day period
        CASE
            WHEN (minute_of_day / 60) < 6  THEN 'Night'
            WHEN (minute_of_day / 60) < 12 THEN 'Morning'
            WHEN (minute_of_day / 60) < 18 THEN 'Afternoon'
            ELSE 'Evening'
        END                                              AS day_period
    FROM minutes
)
SELECT * FROM enriched
```

**Tại sao SQL-generated, không CSV seed:**
- Thay đổi logic flag → chỉ sửa SQL, không phải regenerate CSV
- Không cần maintain 1440-row CSV file trong git
- Business flags (`is_peak_hour`, `is_business_hour`) là **business-specific** — dễ adapt cho tenant khác
- `range()` function trong DuckDB rất rẻ (no I/O)

**Fact table join:**
```sql
-- fact_orders.sql
SELECT
    ...,
    (EXTRACT(hour FROM created_at) * 60 + EXTRACT(minute FROM created_at)) AS time_key,
    ...
FROM std_orders
-- Join: fact.time_key = dim_time.time_key → `is_peak_hour`, `day_period` etc.
```

**Tương tự cho `dim_date`:** dùng `dbt_utils.date_spine()` macro thay vì CSV.

---

## Quick Reference: Materialization Decision Tree

```
Need incremental? 
  YES → materialized='incremental', incremental_strategy='delete+insert',
        unique_key='biz_key', 7-day lookback
  NO  → Heavy compute, used multiple times?
          YES → materialized='table'
          NO  → materialized='view' (default)

Mart model (dim_/fact_)?
  → materialized='external'
  → location="{{ get_rolling_location() }}" (REQUIRED)
  → tags=['mart', 'dim'|'fact']
```

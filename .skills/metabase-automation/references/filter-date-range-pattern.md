# Filter Date Range Pattern — Reference

> **Canonical example:** `docs/analytics-handbook/blueprints/channel_profitability_monthly.md` (dashboard 33)

Tài liệu này mô tả đầy đủ cách implement `date_range` filter động trong Metabase blueprint — từ filter definition, cycle-indicator, đến KPI cards và data queries. Follow đúng tài liệu này để filter hoạt động chính xác với mọi loại period (daily, weekly, monthly, quarterly, yearly).

---

## 1. Cơ chế hoạt động của Metabase Field Filter

Khi dashboard có filter kiểu `date/all-options` với `field_id`, Metabase inject điều kiện SQL dạng:

```sql
AND "main"."<table_name>"."<column_name>" >= ? AND "main"."<table_name>"."<column_name>" < ?
```

**Điều này có nghĩa:**
- Injection sử dụng **fully-qualified table name** — không dùng alias
- Injection chỉ hoạt động nếu `<table_name>` **nằm trong FROM clause** của query/CTE đang chứa `[[AND {{date_range}}]]`
- Nếu table không có trong FROM, hoặc có alias, DuckDB ném `Binder Error: Referenced table "main" not found`

---

## 2. Quy tắc bắt buộc (MUST follow)

| # | Quy tắc | Vi phạm gây ra |
|---|---------|----------------|
| R1 | `[[AND {{date_range}}]]` phải nằm trong WHERE của CTE/query có `<field_table>` trong FROM | `Binder Error` |
| R2 | `<field_table>` **không được có alias** trong FROM | `Binder Error` (L96) |
| R3 | Cột TIMESTAMP phải cast `::DATE` trước MIN/MAX | `BIGINT` cast error |
| R4 | `date_key` INTEGER (YYYYMMDD) dùng `make_date()` để convert | Query trả về sai data |
| R5 | `filter_bounds` luôn là CTE **đầu tiên** trong WITH chain | DuckDB CTE order |
| R6 | Template tag `{{date_range}}` phải có `field_id` khớp với table trong filter_bounds | Filter không wire |

---

## 3. Blueprint Filter Definition

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past3months",
  "field_id": 324
}
```

| Field | Mô tả |
|-------|-------|
| `slug` | Tên biến trong SQL: `{{date_range}}` |
| `type` | Luôn dùng `date/all-options` để hỗ trợ daily/weekly/monthly/quarterly/yearly |
| `default` | `thismonth` / `past3months` / `past1months` / `thisweek` v.v. |
| `field_id` | ID của cột DATE trong Metabase — xác định table nào được inject |

**Cách tìm field_id:**
```bash
curl -s "$METABASE_URL/api/database/<db_id>/metadata" -H "x-api-key: $KEY" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for t in d.get('tables',[]):
    for f in t.get('fields',[]):
        if f.get('base_type') in ('type/Date','type/DateTime','type/DateTimeWithTZ'):
            print(f['id'], t['name'], f['name'], f.get('base_type'))
" | grep -i "<table_name>"
```

**Field_id đã biết:**

| field_id | Table | Column | Type | Dùng cho |
|----------|-------|--------|------|----------|
| 324 | `int_misa_sales_lines` | `posting_date` | Date | Finance, Channel P&L, Product |
| 141 | `fact_orders` | `order_timestamp` | DateTimeWithTZ | Orders, US CrossBorder |

---

## 4. Pattern A — Cycle-Indicator (3-CTE chain)

Dùng cho widget "Chu kỳ báo cáo" — hiển thị kỳ hiện tại và kỳ trước.

```sql
WITH filter_bounds AS (
    -- [1] Raw data bounds — PHẢI query table khớp field_id, KHÔNG alias table đó
    SELECT MIN(<date_col>) AS p_start,   -- nếu TIMESTAMP: MIN(<col>)::DATE
           MAX(<date_col>) AS p_end      -- nếu TIMESTAMP: MAX(<col>)::DATE
    FROM <field_table>                   -- table tương ứng với field_id, KHÔNG alias
    WHERE <base_conditions>
      [[AND {{date_range}}]]             -- PHẢI có dòng này để wire filter
      [[AND {{channel}}]]                -- optional: các filter khác
),
-- [2] Clean period boundaries — detect weekly/monthly/quarterly/yearly từ data bounds
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE   -- weekly: Mon
             ELSE  date_trunc('month', p_start)::DATE    -- monthly+: 1st of month
        END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE  -- Sun
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
        END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
-- [3] Compute prev_start aligned to period boundary (01/ of month/week)
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6
                  THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE
             END,'%d/%m/%Y') || ' – ' ||
    strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
```

**Visualization settings:**
```json
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

**Position:** `{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }`

### period_adj heuristic logic

| Condition | Detected as | p_end result |
|-----------|-------------|--------------|
| `raw_dur ≤ 6` | Weekly | Sunday of the week |
| `p_end < today-30` | Closed "Previous X" | Last day of p_end's month |
| `raw_dur > 100 AND month(p_start)=1` | This Year | Dec 31 |
| `35 ≤ raw_dur ≤ 100` | This Quarter | Last day of quarter |
| else | This Month / rolling | Last day of p_end's month |

---

## 5. Pattern B — KPI Comparison Card (this vs prev)

Dùng cho scalar KPI card hiển thị kỳ này vs kỳ trước.

```sql
WITH filter_bounds AS (
    -- Phải là CTE đầu tiên, query table khớp field_id, KHÔNG alias
    SELECT MIN(<date_col>) AS p_start,
           MAX(<date_col>) AS p_end
    FROM <field_table>
    WHERE <base_conditions>
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
this_period AS (
    SELECT COALESCE(SUM(<metric>), 0) AS val
    FROM <data_table>
    WHERE <base_conditions>
      [[AND {{date_range}}]]        -- wire filter cho this_period
      [[AND {{channel}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(<metric>), 0) AS val
    FROM <data_table>, filter_bounds
    WHERE <base_conditions>
      AND <date_col> >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND <date_col> <  filter_bounds.p_start
      [[AND {{channel}}]]           -- optional filters, KHÔNG dùng [[AND {{date_range}}]]
)
SELECT
    t.val AS "Kỳ này",
    p.val AS "Kỳ trước",
    ROUND((t.val - p.val) * 100.0 / NULLIF(p.val, 0), 1) AS "% thay đổi"
FROM this_period t, prev_period p
```

**Note:** `prev_period` tính window bằng cách shift ngược cùng số ngày — không cần thêm `[[AND {{date_range}}]]`.

---

## 6. Pattern C — Direct Filter Query (không cần prev_period)

Dùng cho charts, tables, distributions — chỉ cần filter theo kỳ hiện tại.

```sql
SELECT ...
FROM <field_table>               -- KHÔNG alias nếu là field_id table
WHERE <base_conditions>
  [[AND {{date_range}}]]         -- inject trực tiếp
  [[AND {{channel}}]]
GROUP BY ...
```

Hoặc với JOIN:
```sql
SELECT ...
FROM <field_table>               -- field_id table, KHÔNG alias
JOIN dim_channels ON <field_table>.channel_key = dim_channels.channel_key
WHERE dim_channels.channel_name = 'US'
  [[AND {{date_range}}]]
```

---

## 7. Column Type Variants

### 7.1 DATE column (e.g., `posting_date`)
```sql
-- filter_bounds — dùng trực tiếp
SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
FROM int_misa_sales_lines
WHERE ...
  [[AND {{date_range}}]]
```

### 7.2 TIMESTAMP / DateTimeWithTZ column (e.g., `order_timestamp`)
```sql
-- Phải cast ::DATE trước MIN/MAX — TIMESTAMP - TIMESTAMP = INTERVAL, không cast được sang INTEGER
SELECT MIN(order_timestamp)::DATE AS p_start,
       MAX(order_timestamp)::DATE AS p_end
FROM fact_orders              -- KHÔNG alias fact_orders nếu field_id = 141
WHERE ...
  [[AND {{date_range}}]]
```

### 7.3 INTEGER date_key (YYYYMMDD format, e.g., `fact_us_shipment_economics.date_key`)
```sql
-- filter_bounds query table có DATE/TIMESTAMP (không phải date_key table)
WITH filter_bounds AS (
    SELECT MIN(order_timestamp)::DATE AS p_start,
           MAX(order_timestamp)::DATE AS p_end
    FROM fact_orders           -- KHÔNG alias
    WHERE ...
      [[AND {{date_range}}]]
),
-- Data query convert filter bounds → date_key integers
this_period AS (
    SELECT COALESCE(SUM(total_revenue), 0) AS val
    FROM fact_us_shipment_economics, filter_bounds
    WHERE date_key >= CAST(strftime(filter_bounds.p_start, '%Y%m%d') AS INTEGER)
      AND date_key <= CAST(strftime(filter_bounds.p_end,   '%Y%m%d') AS INTEGER)
)
```

**Convert date_key → display date (CAST AS DATE bị broken):**
```sql
-- SAI trong DuckDB:
CAST(CAST(date_key AS VARCHAR) AS DATE)

-- ĐÚNG:
make_date((date_key/10000)::INTEGER, ((date_key%10000)/100)::INTEGER, (date_key%100)::INTEGER)
```

---

## 8. Anti-Patterns (KHÔNG làm)

```sql
-- ❌ Alias table của field_id → Binder Error
FROM fact_orders o
WHERE [[AND {{date_range}}]]   -- injects "main"."fact_orders"."order_timestamp" — binder không tìm thấy 'o'

-- ✅ Không alias
FROM fact_orders
WHERE [[AND {{date_range}}]]

-- ❌ filter_bounds query table KHÁC với field_id table
WITH filter_bounds AS (
    SELECT MIN(posting_date) AS p_start FROM fact_us_shipment_economics  -- field_id 324 = int_misa_sales_lines!
    WHERE [[AND {{date_range}}]]   -- injects condition for int_misa_sales_lines, KHÔNG PHẢI fact_us_shipment_economics
)

-- ❌ Hardcode ngày thay vì dùng filter_bounds
WHERE posting_date >= date_trunc('month', current_date) - INTERVAL '3 months'   -- bất biến với filter

-- ❌ Dùng STRFTIME (uppercase) — DuckDB dùng lowercase strftime
CAST(STRFTIME(date, '%Y%m%d') AS INTEGER)   -- SAI

-- ✅ ĐÚNG
CAST(strftime(date, '%Y%m%d') AS INTEGER)
```

---

## 9. Checklist trước khi deploy

- [ ] Blueprint có `metabase-filter` block với đúng `field_id`
- [ ] Mỗi tab có cycle-indicator với `[[AND {{date_range}}]]` trong filter_bounds WHERE
- [ ] filter_bounds query đúng table tương ứng `field_id`
- [ ] Table trong filter_bounds WHERE **KHÔNG có alias** (L96)
- [ ] TIMESTAMP column có `::DATE` cast trong MIN/MAX (L95/L96)
- [ ] date_key dùng `make_date()` để display, `strftime()` để filter
- [ ] `prev_period` CTE dùng `filter_bounds.p_start` làm upper bound (không có `[[AND {{date_range}}]]`)
- [ ] Các filter khác (`{{channel}}`, v.v.) có `[[AND]]` cả trong filter_bounds lẫn this_period

---

## 10. Ví dụ hoàn chỉnh — Dashboard 33

File: `docs/analytics-handbook/blueprints/channel_profitability_monthly.md`

```sql
-- ✅ Cycle-indicator (Tab: Channel Overview)
WITH filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM int_misa_sales_lines           -- field_id 324 = posting_date, KHÔNG alias
    WHERE NOT is_promo_line
      [[AND {{date_range}}]]
      [[AND {{channel}}]]
),
period_adj AS ( ... ),
prev_calc AS ( ... )
SELECT '📅 Kỳ này: ...' AS "Chu kỳ báo cáo" FROM prev_calc

-- ✅ KPI card (Total Revenue)
WITH filter_bounds AS (
    SELECT MIN(posting_date) AS p_start, MAX(posting_date) AS p_end
    FROM int_misa_sales_lines WHERE NOT is_promo_line
      [[AND {{date_range}}]] [[AND {{channel}}]]
),
this_period AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines WHERE NOT is_promo_line
      [[AND {{date_range}}]] [[AND {{channel}}]]
),
prev_period AS (
    SELECT COALESCE(SUM(revenue_net_of_discount), 0) AS val
    FROM int_misa_sales_lines, filter_bounds
    WHERE NOT is_promo_line
      AND posting_date >= (filter_bounds.p_start - (filter_bounds.p_end - filter_bounds.p_start)::INTEGER - 1)
      AND posting_date <  filter_bounds.p_start
      [[AND {{channel}}]]
)
SELECT t.val AS "Doanh thu", p.val AS "Ky truoc" FROM this_period t, prev_period p

-- ✅ Chart card (direct filter)
SELECT channel_name, ROUND(SUM(gross_profit)*100.0/NULLIF(SUM(revenue_net_of_discount),0),1) AS "GM%"
FROM int_misa_sales_lines
WHERE NOT is_promo_line [[AND {{date_range}}]] [[AND {{channel}}]]
GROUP BY channel_name
```

---

## 11. Lessons liên quan

| Lesson | Nội dung tóm tắt |
|--------|------------------|
| L95 | `[[AND {{date_range}}]]` phải trong CTE có table khớp field_id; dùng `filter_bounds` làm bridge |
| L96 | Table của field_id KHÔNG được có alias — DuckDB binder resolve theo table name, không alias |

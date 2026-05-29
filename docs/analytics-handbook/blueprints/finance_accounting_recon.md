# Blueprint: Accounting Reconciliation Cockpit [Internal]

> **Target Collection:** `Finance`
> **Collection ID:** 92
> **Database:** Sapo
> **Role:** Accounting Manager, CFO
> **Archetype:** Operational Cockpit
> **Description:** Audience: Accounting/CFO. Scope: Internal recon. Câu hỏi: Sapo/MISA/Shopee có khớp không? Exception ở đâu?

## Proxy Mode Notice

`recon_sapo_orders_daily` and `recon_misa_daily` tables are **not yet built**.
All questions use `fact_order_economics` flags as proxy:
- `has_cogs` = Sapo order has MISA invoice matched
- `has_platform_fees` = Sapo order has Shopee payout matched
- True recon ledger: build dbt `recon_*` models when MISA/Shopee ingestion is stable.

---

## 📂 Collection: Finance

Dashboard đối soát nội bộ: Sapo ↔ MISA ↔ Shopee. Dành cho kế toán trưởng và CFO theo dõi tỷ lệ khớp invoice, đơn hàng exception, và xu hướng drift hàng ngày.

---

### 🖥️ Dashboard: Accounting Reconciliation Cockpit [Internal]

**Description**: Audience: Accounting/CFO. Scope: Internal recon. Câu hỏi: Sapo/MISA/Shopee có khớp không? Exception ở đâu?

---

#### Filter: Period

```json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past30days"
}
```

---

### 📑 Tab: Recon Status Overview

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_start,
           MAX(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_end
    FROM fact_order_economics
    WHERE status = 'COMPLETED'
      [[AND {{date_range}}]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```


#### 📝 Text: Recon Header

Trang thai doi soat: Sapo ↔ MISA ↔ Shopee — proxy tu fact_order_economics (recon tables chua build)

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

---

#### ❓ Question: MISA Coverage % — All Time

Ty le don hang COMPLETED co MISA invoice khop — proxy cho "Sapo↔MISA reconciled". Alert neu < 50%.

**Domain Reference**: [RC1 — MISA Coverage %](../domains/finance.md#rc1-misa-coverage--tỷ-lệ-khớp-misa)

```sql
SELECT
    ROUND(
        SUM(CASE WHEN has_cogs THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0),
        1
    ) AS "MISA Coverage %"
FROM fact_order_economics
WHERE status = 'COMPLETED'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "MISA Coverage %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 5, "size_y": 3 }
```

---

#### ❓ Question: Unmatched Rate % — All Time

Ty le don hang COMPLETED KHONG co MISA invoice. > 50% la alert.

**Domain Reference**: [RC2 — Unmatched Rate](../domains/finance.md#rc2-unmatched-rate--no-misa-tỷ-lệ-thiếu-misa-invoice)

```sql
SELECT
    ROUND(
        SUM(CASE WHEN NOT has_cogs THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0),
        1
    ) AS "Unmatched Rate %"
FROM fact_order_economics
WHERE status = 'COMPLETED'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Unmatched Rate %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 5, "size_x": 5, "size_y": 3 }
```

---

#### ❓ Question: Shopee Fee Coverage %

Ty le don Shopee co du lieu phat hanh (settlement fees). Thap → ảnh hưởng channel_net_profit.

**Domain Reference**: [RC3 — Shopee Fee Coverage %](../domains/finance.md#rc3-shopee-fee-coverage--tỷ-lệ-có-dữ-liệu-phí-shopee)

```sql
SELECT
    ROUND(
        SUM(CASE WHEN e.has_platform_fees THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0),
        1
    ) AS "Shopee Fee Coverage %"
FROM fact_order_economics e
JOIN dim_channels c ON e.channel_key = c.channel_key
WHERE c.channel_name ILIKE '%shopee%'
  AND e.status = 'COMPLETED'
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "Shopee Fee Coverage %": {
        "suffix": "%",
        "decimals": 1
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 5, "size_y": 3 }
```

---

#### ❓ Question: Unmatched Orders Count (Last 30 Days)

So don hang khong co MISA invoice trong 30 ngay gan nhat.

```sql
WITH filter_bounds AS (
    SELECT MIN(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_start,
           MAX(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_end
    FROM fact_order_economics
    WHERE status = 'COMPLETED'
      [[AND {{date_range}}]]
)
SELECT COUNT(*) AS "Don chua doi soat (30 ngay)"
FROM fact_order_economics, filter_bounds
WHERE status = 'COMPLETED'
  AND NOT has_cogs
  AND date_key >= CAST(strftime(filter_bounds.p_start, '%Y%m%d') AS INTEGER)
  AND date_key <= CAST(strftime(filter_bounds.p_end, '%Y%m%d') AS INTEGER)
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {}
}
```

```json metabase-pos
{ "row": 3, "col": 15, "size_x": 3, "size_y": 3 }
```

---

#### ❓ Question: Recon Status Distribution

Phan nhom trang thai doi soat: FULLY_RECONCILED / MISSING_MISA / MISSING_SHOPEE_FEES / UNRECONCILED.
Proxy tu has_cogs + has_platform_fees flags.

**Domain Reference**: [RC4 — Recon Status Distribution](../domains/finance.md#rc4-recon-status-distribution-phân-loại-trạng-thái-đối-soát)

```sql
SELECT
    CASE
        WHEN has_cogs AND has_platform_fees THEN 'FULLY_RECONCILED'
        WHEN has_cogs AND NOT has_platform_fees THEN 'MISSING_SHOPEE_FEES'
        WHEN NOT has_cogs AND has_platform_fees THEN 'MISSING_MISA'
        ELSE 'UNRECONCILED'
    END AS "Trang thai recon",
    COUNT(*) AS "So don hang",
    COALESCE(SUM(net_revenue), 0) AS "Doanh thu (VND)"
FROM fact_order_economics
WHERE status = 'COMPLETED'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Doanh thu (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    },
    "table.column_formatting": [
      {
        "columns": ["Trang thai recon"],
        "type": "single",
        "operator": "=",
        "value": "UNRECONCILED",
        "color": "#EF8C8C",
        "highlight_row": true
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 8, "size_y": 5 }
```

---

#### ❓ Question: Recon Status Donut

Bieu do tron — ty le theo trang thai doi soat.

```sql
SELECT
    CASE
        WHEN has_cogs AND has_platform_fees THEN 'FULLY_RECONCILED'
        WHEN has_cogs AND NOT has_platform_fees THEN 'MISSING_SHOPEE_FEES'
        WHEN NOT has_cogs AND has_platform_fees THEN 'MISSING_MISA'
        ELSE 'UNRECONCILED'
    END AS "Trang thai recon",
    COUNT(*) AS "So don hang"
FROM fact_order_economics
WHERE status = 'COMPLETED'
GROUP BY 1
```

```json metabase-viz
{
  "display": "pie",
  "visualization_settings": {
    "pie.dimension": "Trang thai recon",
    "pie.metric": "So don hang",
    "pie.colors": {
      "FULLY_RECONCILED":      "#84BB4C",
      "MISSING_SHOPEE_FEES":   "#F9D45C",
      "MISSING_MISA":          "#F2A86F",
      "UNRECONCILED":          "#EF8C8C"
    },
    "pie.show_legend": true
  }
}
```

```json metabase-pos
{ "row": 6, "col": 8, "size_x": 5, "size_y": 5 }
```

---

#### ❓ Question: Revenue at Risk by Recon Status

Doanh thu theo tung nhom trang thai — bao nhieu VND chua co COGS de tinh margin?

```sql
SELECT
    CASE
        WHEN has_cogs AND has_platform_fees THEN 'FULLY_RECONCILED'
        WHEN has_cogs AND NOT has_platform_fees THEN 'MISSING_SHOPEE_FEES'
        WHEN NOT has_cogs AND has_platform_fees THEN 'MISSING_MISA'
        ELSE 'UNRECONCILED'
    END AS "Trang thai recon",
    COALESCE(SUM(net_revenue), 0) AS "Doanh thu (VND)"
FROM fact_order_economics
WHERE status = 'COMPLETED'
GROUP BY 1
ORDER BY 2 DESC
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Trang thai recon"],
    "graph.metrics": ["Doanh thu (VND)"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "VND",
    "column_settings": {
      "Doanh thu (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 6, "col": 13, "size_x": 5, "size_y": 5 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_order_economics · **Cadence:** rolling-30d · **Scope:** has_cogs proxy for recon · **Caveats:** Recon mart not yet built — using proxy
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Exception Table

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_start,
           MAX(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_end
    FROM fact_order_economics
    WHERE status = 'COMPLETED'
      [[AND {{date_range}}]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```


#### 📝 Text: Exception Header

Don hang chua doi soat — Missing MISA invoice hoac Missing Shopee fee data

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

---

#### ❓ Question: Unmatched Orders — Missing MISA Invoice

Danh sach don hang COMPLETED khong co MISA invoice — 30 ngay gan nhat. Xem order_code + doanh thu de biet can hoi MISA team doi soat invoice nao.

```sql
WITH filter_bounds AS (
    SELECT MIN(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_start,
           MAX(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_end
    FROM fact_order_economics
    WHERE status = 'COMPLETED'
      [[AND {{date_range}}]]
)
SELECT
    e.order_code        AS "Ma don hang",
    (CAST(e.date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((e.date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(e.date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS "Ngay dat hang",
    COALESCE(c.channel_name, 'Unknown') AS "Kenh",
    e.gross_revenue     AS "Doanh thu gop (VND)",
    e.net_revenue       AS "Doanh thu thuan (VND)",
    e.status            AS "Trang thai don",
    'MISSING_MISA'      AS "Loai exception"
FROM fact_order_economics e
LEFT JOIN dim_channels c ON e.channel_key = c.channel_key
CROSS JOIN filter_bounds
WHERE e.status = 'COMPLETED'
  AND NOT e.has_cogs
  AND e.date_key >= CAST(strftime(filter_bounds.p_start, '%Y%m%d') AS INTEGER)
  AND e.date_key <= CAST(strftime(filter_bounds.p_end, '%Y%m%d') AS INTEGER)
ORDER BY e.date_key DESC, e.net_revenue DESC
LIMIT 200
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Doanh thu gop (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Doanh thu thuan (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 8 }
```

---

#### ❓ Question: Shopee Orders Missing Fee Data

Don Shopee khong co du lieu settlement fee — channel_net_profit se bi overstate. 30 ngay gan nhat.

**Domain Reference**: [RC6 — Shopee Fee Gap](../domains/finance.md#rc6-saposhopee-fee-gap-đơn-shopee-thiếu-dữ-liệu-phí)

```sql
WITH filter_bounds AS (
    SELECT MIN(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_start,
           MAX(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_end
    FROM fact_order_economics
    WHERE status = 'COMPLETED'
      [[AND {{date_range}}]]
)
SELECT
    e.order_code        AS "Ma don hang",
    (CAST(e.date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((e.date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(e.date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS "Ngay dat hang",
    e.gross_revenue     AS "Doanh thu gop (VND)",
    e.net_revenue       AS "Doanh thu thuan (VND)",
    e.gross_profit      AS "Gross Profit (VND)",
    'MISSING_SHOPEE_FEES' AS "Loai exception"
FROM fact_order_economics e
JOIN dim_channels c ON e.channel_key = c.channel_key
CROSS JOIN filter_bounds
WHERE c.channel_name ILIKE '%shopee%'
  AND e.status = 'COMPLETED'
  AND NOT e.has_platform_fees
  AND e.date_key >= CAST(strftime(filter_bounds.p_start, '%Y%m%d') AS INTEGER)
  AND e.date_key <= CAST(strftime(filter_bounds.p_end, '%Y%m%d') AS INTEGER)
ORDER BY e.date_key DESC, e.net_revenue DESC
LIMIT 200
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "Doanh thu gop (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Doanh thu thuan (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      },
      "Gross Profit (VND)": {
        "number_style": "currency",
        "currency": "VND",
        "decimals": 0,
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "row": 11, "col": 0, "size_x": 18, "size_y": 7 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_order_economics · **Cadence:** rolling-30d · **Scope:** has_cogs proxy for recon · **Caveats:** Recon mart not yet built — using proxy
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Drift Trend

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_start,
           MAX(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_end
    FROM fact_order_economics
    WHERE status = 'COMPLETED'
      [[AND {{date_range}}]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```


#### 📝 Text: Drift Trend Header

Xu huong ty le khong khop theo ngay — 30 ngay gan nhat. Spike = loi ingestion hoac lag du lieu.

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

---

#### ❓ Question: Daily Unmatched % Trend (Last 30 Days)

Line chart — ty le don khong co MISA invoice theo ngay. Spike bat thuong → kiem tra Dagster pipeline.

**Domain Reference**: [RC5 — Daily Unmatched Trend](../domains/finance.md#rc5-daily-unmatched-trend-xu-hướng-đơn-chưa-đối-soát-theo-ngày)

```sql
WITH filter_bounds AS (
    SELECT MIN(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_start,
           MAX(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_end
    FROM fact_order_economics
    WHERE status = 'COMPLETED'
      [[AND {{date_range}}]]
)
SELECT
    (CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS "Ngay",
    COUNT(*) AS "Tong don",
    SUM(CASE WHEN NOT has_cogs THEN 1 ELSE 0 END)       AS "Don chua khop MISA",
    ROUND(
        SUM(CASE WHEN NOT has_cogs THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0),
        1
    )                                                   AS "Unmatched %"
FROM fact_order_economics, filter_bounds
WHERE status = 'COMPLETED'
  AND date_key >= CAST(strftime(filter_bounds.p_start, '%Y%m%d') AS INTEGER)
  AND date_key <= CAST(strftime(filter_bounds.p_end, '%Y%m%d') AS INTEGER)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Ngay"],
    "graph.metrics": ["Unmatched %"],
    "graph.colors": ["#EF8C8C"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Unmatched %",
    "column_settings": {
      "Unmatched %": {
        "suffix": "%",
        "decimals": 1
      }
    },
    "graph.goal_value": 30,
    "graph.show_goal": true,
    "graph.goal_label": "Watch threshold (30%)"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: Daily Orders Volume vs Unmatched Count

Bar + line combo — tong don hang theo ngay (bar) vs don chua khop (line overlay).

```sql
WITH filter_bounds AS (
    SELECT MIN(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_start,
           MAX(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_end
    FROM fact_order_economics
    WHERE status = 'COMPLETED'
      [[AND {{date_range}}]]
)
SELECT
    (CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS "Ngay",
    COUNT(*) AS "Tong don",
    SUM(CASE WHEN NOT has_cogs THEN 1 ELSE 0 END)       AS "Don chua khop MISA"
FROM fact_order_economics, filter_bounds
WHERE status = 'COMPLETED'
  AND date_key >= CAST(strftime(filter_bounds.p_start, '%Y%m%d') AS INTEGER)
  AND date_key <= CAST(strftime(filter_bounds.p_end, '%Y%m%d') AS INTEGER)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "combo",
  "visualization_settings": {
    "graph.dimensions": ["Ngay"],
    "graph.metrics": ["Tong don", "Don chua khop MISA"],
    "series_settings": {
      "Tong don":            { "display": "bar",  "color": "#509EE3" },
      "Don chua khop MISA":  { "display": "line", "color": "#EF8C8C" }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "So don hang"
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 6 }
```

---


#### 📝 Text: Source & Freshness

**Source:** fact_order_economics · **Cadence:** rolling-30d · **Scope:** has_cogs proxy for recon · **Caveats:** Recon mart not yet built — using proxy
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```

### 📑 Tab: Reconciliation Funnel

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH filter_bounds AS (
    SELECT MIN(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_start,
           MAX(CAST(date_key/10000 AS INTEGER)::VARCHAR || '-' || LPAD(CAST((date_key/100)%100 AS INTEGER)::VARCHAR,2,'0') || '-' || LPAD(CAST(date_key%100 AS INTEGER)::VARCHAR,2,'0'))::DATE AS p_end
    FROM fact_order_economics
    WHERE status = 'COMPLETED'
      [[AND {{date_range}}]]
),
period_adj AS (
    SELECT
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN date_trunc('week',  p_start)::DATE
             ELSE  date_trunc('month', p_start)::DATE END AS p_start,
        CASE WHEN (p_end-p_start)::INTEGER<=6
               THEN (date_trunc('week', p_start) + INTERVAL '6 days')::DATE
             WHEN p_end < current_date-30
               THEN (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
             WHEN (p_end-p_start)::INTEGER > 100 AND EXTRACT(MONTH FROM p_start)::INTEGER = 1
               THEN make_date(EXTRACT(YEAR FROM p_start)::INTEGER, 12, 31)
             WHEN (p_end-p_start)::INTEGER BETWEEN 35 AND 100
               THEN (date_trunc('quarter', p_start) + INTERVAL '3 months' - INTERVAL '1 day')::DATE
             ELSE (date_trunc('month', p_end) + INTERVAL '1 month' - INTERVAL '1 day')::DATE END AS p_end,
        (p_end-p_start)::INTEGER AS raw_dur
    FROM filter_bounds
),
prev_calc AS (
    SELECT p_start, p_end, raw_dur,
        (EXTRACT(YEAR  FROM p_end)::INTEGER - EXTRACT(YEAR  FROM p_start)::INTEGER)*12 +
         EXTRACT(MONTH FROM p_end)::INTEGER - EXTRACT(MONTH FROM p_start)::INTEGER + 1 AS n_months
    FROM period_adj
)
SELECT
    '📅 Kỳ này: ' || strftime(p_start,'%d/%m/%Y') || ' – ' || strftime(p_end,'%d/%m/%Y') ||
    '  ·  Kỳ trước: ' ||
    strftime(CASE WHEN raw_dur<=6 THEN (p_start - INTERVAL '7 days')::DATE
                  ELSE (p_start - (n_months::VARCHAR||' months')::INTERVAL)::DATE END,'%d/%m/%Y') ||
    ' – ' || strftime((p_start-1)::DATE,'%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM prev_calc
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```


#### 📝 Text: Funnel Header

Reconciliation funnel: Tu tong don hang → Co MISA → Co Shopee fee → Fully reconciled

```json metabase-pos
{"row": 2, "col":0, "size_x":18, "size_y":1}
```

---

#### ❓ Question: Reconciliation Funnel — Completed Orders

Funnel: Tong don COMPLETED → Co MISA (has_cogs) → Co Shopee fee (has_platform_fees) → Fully matched (ca hai).
Giup CFO hieu bao nhieu % don co du data de tinh margin chinh xac.

```sql
SELECT 'Total COMPLETED Orders'       AS "Buoc",     COUNT(*)                                                           AS "So don", 1 AS sort_order FROM fact_order_economics WHERE status = 'COMPLETED'
UNION ALL
SELECT 'Have MISA Invoice (has_cogs)', COUNT(*),      2 FROM fact_order_economics WHERE status = 'COMPLETED' AND has_cogs
UNION ALL
SELECT 'Have Shopee Fees (Shopee only)', COUNT(*),    3 FROM fact_order_economics WHERE status = 'COMPLETED' AND has_platform_fees
UNION ALL
SELECT 'Fully Reconciled (MISA + Shopee fee)', COUNT(*), 4 FROM fact_order_economics WHERE status = 'COMPLETED' AND has_cogs AND has_platform_fees
ORDER BY sort_order
```

```json metabase-viz
{
  "display": "bar",
  "visualization_settings": {
    "graph.dimensions": ["Buoc"],
    "graph.metrics": ["So don"],
    "graph.colors": ["#509EE3"],
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "So don hang",
    "graph.x_axis.scale": "ordinal"
  }
}
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 10, "size_y": 6 }
```

---

#### ❓ Question: MISA Coverage by Channel

Ty le khop MISA phan theo kenh ban hang — kenh nao co MISA coverage thap nhat?

```sql
SELECT
    COALESCE(c.channel_name, 'Unknown')   AS "Kenh",
    COUNT(*) AS "Tong don",
    SUM(CASE WHEN e.has_cogs THEN 1 ELSE 0 END) AS "Co MISA",
    ROUND(
        SUM(CASE WHEN e.has_cogs THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0),
        1
    ) AS "MISA Coverage %"
FROM fact_order_economics e
LEFT JOIN dim_channels c ON e.channel_key = c.channel_key
WHERE e.status = 'COMPLETED'
GROUP BY c.channel_name
ORDER BY "Tong don" DESC
LIMIT 20
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "MISA Coverage %": {
        "suffix": "%",
        "decimals": 1
      }
    },
    "table.column_formatting": [
      {
        "columns": ["MISA Coverage %"],
        "type": "single",
        "operator": "<",
        "value": 50,
        "color": "#EF8C8C",
        "highlight_row": false
      }
    ]
  }
}
```

```json metabase-pos
{ "row": 3, "col": 10, "size_x": 8, "size_y": 6 }
```

---

#### ❓ Question: Recon Coverage Trend by Month

Xu huong MISA Coverage % theo thang — co cai thien khong?

```sql
SELECT
    date_trunc('month', CAST(CAST(date_key AS VARCHAR) AS DATE)) AS "Thang",
    COUNT(*) AS "Tong don",
    ROUND(
        SUM(CASE WHEN has_cogs THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0),
        1
    ) AS "MISA Coverage %",
    ROUND(
        SUM(CASE WHEN has_platform_fees THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0),
        1
    ) AS "Shopee Fee Coverage %"
FROM fact_order_economics
WHERE status = 'COMPLETED'
  AND date_key >= CAST(date_trunc('month', current_date) - INTERVAL '5 months' AS INTEGER)
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Thang"],
    "graph.metrics": ["MISA Coverage %", "Shopee Fee Coverage %"],
    "series_settings": {
      "MISA Coverage %":       { "color": "#509EE3" },
      "Shopee Fee Coverage %": { "color": "#F2A86F" }
    },
    "graph.x_axis.title_text": "",
    "graph.y_axis.title_text": "Coverage %",
    "column_settings": {
      "MISA Coverage %":       { "suffix": "%", "decimals": 1 },
      "Shopee Fee Coverage %": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 9, "col": 0, "size_x": 18, "size_y": 5 }
```

#### 📝 Text: Source & Freshness

**Source:** fact_order_economics · **Cadence:** rolling-30d · **Scope:** has_cogs proxy for recon · **Caveats:** Recon mart not yet built — using proxy
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
```


# 📘 Data Warehouse Blueprint

This document serves as the **Single Source of Truth** for our analytics environment.
It is parsed effectively by the `deploy_from_markdown.js` script to configure Metabase automatically.

## 📝 Syntax Guide

- **Headings**: define structure (`## Collection`, `### Dashboard`, `### Model`, `### 📑 Tab`).
- **Code Blocks**: define executable logic (`sql`, `json metabase-viz`, `json metabase-model`).
- **Text**: provides context and discussion (ignored by the parser).

### Heading Hierarchy

| Heading | Purpose | Example |
|---------|---------|---------|
| `## 📂 Collection:` | Target collection (supports nesting with `>`) | `## 📂 Collection: Operations > Daily Monitoring` |
| `### 🧊 Model:` | Metabase Model (dataset) | `### 🧊 Model: Today's Orders` |
| `### 🖥️ Dashboard:` | Dashboard definition | `### 🖥️ Dashboard: Daily Sales` |
| `### 📑 Tab:` | Dashboard tab (groups questions) | `### 📑 Tab: Overview` |
| `#### ❓ Question:` | Card/question on a dashboard | `#### ❓ Question: Revenue` |
| `#### 📝 Text:` | Text annotation / section heading | `#### 📝 Text: Revenue Performance` |
| `#### 📏 Metric:` | Metric on a model | `#### 📏 Metric: Average Build Time` |

### Code Block Types

| Block | Purpose |
|-------|---------|
| `` ```sql `` | SQL query for question/model |
| `` ```json metabase-viz `` | Visualization settings (display type, colors, axes) |
| `` ```json metabase-pos `` | Dashboard position (`row`, `col`, `size_x`, `size_y`) |
| `` ```json metabase-model `` | Model metadata (description, column settings) |

### Tab Support

Tabs organize dashboard cards into separate views. Place `### 📑 Tab:` headers between the `### Dashboard:` header and its `#### Question:` blocks. All questions after a tab header belong to that tab until the next tab header.

**Rules:**
- Tabs are optional — dashboards without tab headers work as a single flat layout
- Every question must be under a tab if tabs are used (questions before any tab header have no tab)
- Tab positions reset per tab — each tab has its own `row`/`col` grid starting at (0,0)
- Tabs and cards are deployed in a single API call to Metabase

### Tab Structure Standards

**Quy tắc: Mỗi tab BẮT BUỘC có 2 widgets — Chu kỳ báo cáo và Source & Freshness**

---

#### Widget 1 — Chu kỳ báo cáo (đầu tab, row 0–1)

Mục đích: Khai báo khung thời gian — người đọc biết chính xác mình đang xem dữ liệu của ngày/tuần/tháng nào.

**Type:** ❓ Question (SQL scalar) — không phải text card

**SQL mẫu (daily):**
```sql
SELECT
  '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"
```

**Visualization:**
```json
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

**Vị trí:** row: 0, col: 0, size_x: 18, size_y: 2 — bắt buộc size_y: 2 mới hiển thị đủ

**Nội dung SQL thay đổi theo loại dashboard:**
- Daily: hôm nay + hôm qua
- Weekly: tuần hiện tại (D-6 → hôm nay)
- Monthly: tháng hiện tại

**Ràng buộc:** Không đặt widget nào khác tại row 0 — Metabase ưu tiên text card khi conflict, Chu kỳ báo cáo sẽ bị đẩy xuống (đây là bug đã gặp và fix trong thực tế).

---

#### Widget 2 — Source & Freshness (cuối tab, row cuối)

Mục đích: Khai báo data frame — nguồn, scope filter thực sự, time window, caveats.

**Type:** Text card (plain text)

**Vị trí:** row cuối cùng, col: 0, size_x: 18, size_y: 1

**Format:**
```
Source: [bảng] · [cadence] · **Scope: [filters]** · [time window] · [caveats nếu có]
```

**Ràng buộc khi viết:**
- Chỉ ghi những gì query thực sự làm — không assume (bài học: "Excludes cancelled/voided" sai vì fact_orders không filter status)
- Nếu widgets trong tab dùng time window khác nhau → ghi rõ từng loại
- Nếu có widget dùng dim snapshot (không theo ngày) → note riêng

---

### Filter Support

Dashboard-level filters (parameters) are defined using `#### Filter:` headers with a `metabase-filter` JSON block. Place them before any Tab or Question headers.

**Auto-wiring:** The deploy script automatically maps dashboard filters to SQL `{{template_tags}}` by matching the filter `slug` to the template tag name. For example, a filter with `slug: "date_range"` will auto-wire to any question containing `{{date_range}}` in its SQL.

**Example:**

```
#### Filter: Date Range

\`\`\`json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past7days",
  "field_id": 141
}
\`\`\`
```

**Supported filter types:** `date/all-options`, `date/single`, `string/=`, `string/contains`, `number/=`, `number/between`

**`field_id` (required for `date/all-options` and `string/=`):** Binds the filter to a specific database field so Metabase generates a proper WHERE clause. Without `field_id`, the filter is created as a basic variable that fails on relative-date values (e.g. `past30days`).

**`field_id_map` (multi-table dashboards):** When questions on the same dashboard query different tables, declare per-table field IDs. The deploy script detects the table referenced in each question's SQL and binds the correct field. Falls back to top-level `field_id` if no table in the map matches.

```json
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past30days",
  "field_id": 141,
  "field_id_map": {
    "int_misa_sales_lines": 324,
    "int_shopee_order_fees": 287,
    "fact_orders": 141
  }
}
```

**Map ordering matters:** First key whose name appears in the question SQL wins. List the most specific tables first; place the fallback table (e.g. `fact_orders`) last.

**Limitation:** A single question joining two mapped tables (e.g. `fact_orders` + `int_misa_sales_lines`) cannot be filtered correctly by one dimension tag. Either (a) restructure the query to a single source table, or (b) remove `{{date_range}}` from that question and hardcode the window.

### Text Annotation Support

Text annotations (section headings, narrative dividers) are deployed as text cards on the dashboard. Use `#### 📝 Text:` headers with an optional `metabase-pos` block.

**Example:**

```
#### 📝 Text: Revenue Performance This Week

Track week-over-week revenue trends and identify anomalies.

\`\`\`json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
\`\`\`
```

**Rules:**
- Text content (lines after the heading) becomes the card's markdown content
- If no text content is provided, the heading name is used as `# Heading Name`
- Position block is optional — defaults to `row: 0, col: 0, size_x: 18, size_y: 1`
- Text cards are tab-aware — place them after a `### Tab:` header to scope to that tab

---

## 📂 Collection: Engineering Analytics

This collection contains internal metrics for the data engineering team.

### 🧊 Model: Dbt Manifest

Wraps the `dbt_manifest` table to track model build times.

```sql
SELECT * FROM public.dbt_manifest
```

#### 📏 Metric: Average Build Time

Tracks performance regression.

```sql --metric
AVG(build_time_seconds)
```

#### ⚙️ Settings

Metadata for the model columns.

```json metabase-model
{
  "description": "Logs from dbt runs.",
  "columns": {
    "build_time_seconds": {
      "display_name": "Build Time (s)",
      "semantic_type": "type/Quantity"
    },
    "status": { "display_name": "Run Status", "semantic_type": "type/Category" }
  }
}
```

---

### 🖥️ Dashboard: Data Pipeline Health

**Description**: monitors the health of our dbt pipelines.

### 📑 Tab: Overview

#### 📝 Text: Pipeline Health Overview

Monitor build failures and performance trends.

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Recent Failed Runs

Lists the last 10 failed model runs.

```sql
SELECT model_name, error_message, run_started_at
FROM public.dbt_run_results
WHERE status = 'error'
ORDER BY run_started_at DESC
LIMIT 10
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.cell_column": "model_name"
  }
}
```

```json metabase-pos
{
  "row": 1,
  "col": 0,
  "size_x": 12,
  "size_y": 6
}
```

#### ❓ Question: Build Time Trend

Line chart of average build time over the last 30 days.

```sql
SELECT run_date::date, avg(build_time)
FROM public.daily_build_stats
GROUP BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["run_date"],
    "graph.metrics": ["avg"]
  }
}
```

```json metabase-pos
{
  "row": 1,
  "col": 12,
  "size_x": 6,
  "size_y": 6
}
```

### 📑 Tab: Details

#### ❓ Question: All Runs This Week

Full run history for the current week.

```sql
SELECT model_name, status, build_time_seconds, run_started_at
FROM public.dbt_run_results
WHERE run_started_at >= current_date - INTERVAL '7 days'
ORDER BY run_started_at DESC
```

```json metabase-viz
{
  "display": "table"
}
```

```json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 18,
  "size_y": 8
}
```

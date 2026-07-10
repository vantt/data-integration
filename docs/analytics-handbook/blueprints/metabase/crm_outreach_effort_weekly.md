---
primary_scope: none
scope_indicator: "[CRM]"
layer: L2
uses_concepts: []
issues:
  - "[resolved] 2026-07-10: serving view was stale at deploy-write time (blocked on missing columns); fixed via bootstrap_serving_views.py same day ~15:41, deployed ~15:43 as dashboard id 147, verified live (queries 200/202, no Binder Errors) as of 22:54."
---

# 📘 Blueprint: Sprint Gọi Ra — KPI tuần

> **Database:** `Sapo`
> **Collection:** Operations > Periodic Reviews
> **Role:** Sales Ops Lead, CS Manager
> **Archetype:** Weekly Review Board (1 tab)
> **Source mart:** `mart_staff_performance_weekly` (`transformation/models/marts/crm/mart_staff_performance_weekly.sql`)
> **Related:** `plans/260709-1638-crm-outreach-effort-report/phase-04-reporting-surface-and-validation.md` (Track A scope)

Weekly review board cho Sprint Gọi Ra 45 ngày — thứ Hai hằng tuần. Đo nỗ lực gọi ra (calls_dialed → contacts_reached → conversations_count), tránh dùng doanh thu làm KPI sớm (doanh thu là lagging indicator 49-157 ngày). Không có filter — dashboard luôn hiển thị tuần dữ liệu mới nhất (`MAX(week_start_date)`) vs tuần liền trước.

**Scalar comparison note:** dùng pattern 2-cột "Tuần này / Tuần trước" đã proven trong `sales_ops_weekly_review.md` thay vì `scalar.comparisons` (Metabase v0.60.2) — quyết định này CHƯA thử `scalar.comparisons` vì deploy đang BLOCKED (xem `issues` ở frontmatter), không verify được end-to-end trước khi bàn giao. Cân nhắc thử `scalar.comparisons` ở lần sửa blueprint tiếp theo khi serving view đã fix.

---

## 📂 Collection: Operations > Periodic Reviews

### 🖥️ Dashboard: Sprint Gọi Ra — KPI tuần

**Description**: Weekly review cho Sprint Gọi Ra 45 ngày — dial → reach → conversation funnel theo staff. Chỉ số sớm, không dùng orders_sold/revenue_vnd để đánh giá sprint trong 6 tuần đầu (lagging 49-157 ngày).

---

### 📑 Tab: Tổng quan

#### ❓ Question: Chu kỳ báo cáo

```sql
WITH latest AS (
    SELECT MAX(week_start_date) AS this_week
    FROM main_marts.mart_staff_performance_weekly
)
SELECT
    '📅 Tuần: ' || strftime(latest.this_week, '%d/%m/%Y') ||
    ' – ' || strftime(latest.this_week + INTERVAL '6 days', '%d/%m/%Y') ||
    '  ·  Tuần trước: ' || strftime(latest.this_week - INTERVAL '7 days', '%d/%m/%Y') ||
    ' – ' || strftime(latest.this_week - INTERVAL '1 days', '%d/%m/%Y')
    AS "Chu kỳ báo cáo"
FROM latest
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
```

#### 📝 Text: Ghi chú Sprint Gọi Ra

Chỉ số sớm của Sprint Gọi Ra — doanh thu là chỉ số trễ 49-157 ngày, KHÔNG đánh giá sprint bằng orders trong 6 tuần đầu. Zalo-connect count sẽ bổ sung ở Track B.

```json metabase-pos
{ "row": 2, "col": 0, "size_x": 18, "size_y": 1 }
```

---

#### ❓ Question: Cuộc gọi

Tổng số cuộc gọi ra trong tuần (kể cả không nghe máy), toàn team.

```sql
WITH latest AS (
    SELECT MAX(week_start_date) AS this_week
    FROM main_marts.mart_staff_performance_weekly
),
this_week AS (
    SELECT COALESCE(SUM(calls_dialed), 0) AS val
    FROM main_marts.mart_staff_performance_weekly, latest
    WHERE week_start_date = latest.this_week
),
last_week AS (
    SELECT COALESCE(SUM(calls_dialed), 0) AS val
    FROM main_marts.mart_staff_performance_weekly, latest
    WHERE week_start_date = latest.this_week - INTERVAL '7 days'
)
SELECT tw.val AS "Cuộc gọi", lw.val AS "Tuần trước"
FROM this_week tw, last_week lw
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": {} }
```

```json metabase-pos
{ "row": 3, "col": 0, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Reach rate %

`contacts_reached / activities_outbound` toàn team (mọi channel — đúng định nghĩa `reach_rate_pct` trong mart, không riêng kênh gọi).

```sql
WITH latest AS (
    SELECT MAX(week_start_date) AS this_week
    FROM main_marts.mart_staff_performance_weekly
),
this_week AS (
    SELECT SUM(contacts_reached) AS reached, SUM(activities_outbound) AS outbound
    FROM main_marts.mart_staff_performance_weekly, latest
    WHERE week_start_date = latest.this_week
),
last_week AS (
    SELECT SUM(contacts_reached) AS reached, SUM(activities_outbound) AS outbound
    FROM main_marts.mart_staff_performance_weekly, latest
    WHERE week_start_date = latest.this_week - INTERVAL '7 days'
)
SELECT
    ROUND(tw.reached * 100.0 / NULLIF(tw.outbound, 0), 1) AS "Reach rate %",
    ROUND(lw.reached * 100.0 / NULLIF(lw.outbound, 0), 1) AS "Tuần trước"
FROM this_week tw, last_week lw
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "column_settings": {
      "[\"name\",\"Reach rate %\"]": { "suffix": "%", "decimals": 1 },
      "[\"name\",\"Tuần trước\"]": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 3, "col": 4, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: Hội thoại thật

`contact_outcome='answered' AND (contact_duration_s >= 60 OR có note outcome đính kèm)`.

```sql
WITH latest AS (
    SELECT MAX(week_start_date) AS this_week
    FROM main_marts.mart_staff_performance_weekly
),
this_week AS (
    SELECT COALESCE(SUM(conversations_count), 0) AS val
    FROM main_marts.mart_staff_performance_weekly, latest
    WHERE week_start_date = latest.this_week
),
last_week AS (
    SELECT COALESCE(SUM(conversations_count), 0) AS val
    FROM main_marts.mart_staff_performance_weekly, latest
    WHERE week_start_date = latest.this_week - INTERVAL '7 days'
)
SELECT tw.val AS "Hội thoại thật", lw.val AS "Tuần trước"
FROM this_week tw, last_week lw
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": {} }
```

```json metabase-pos
{ "row": 3, "col": 8, "size_x": 4, "size_y": 3 }
```

#### ❓ Question: SĐT chết

`contact_outcome='wrong_number'` — chỉ số làm sạch danh sách gọi.

```sql
WITH latest AS (
    SELECT MAX(week_start_date) AS this_week
    FROM main_marts.mart_staff_performance_weekly
),
this_week AS (
    SELECT COALESCE(SUM(wrong_number_count), 0) AS val
    FROM main_marts.mart_staff_performance_weekly, latest
    WHERE week_start_date = latest.this_week
),
last_week AS (
    SELECT COALESCE(SUM(wrong_number_count), 0) AS val
    FROM main_marts.mart_staff_performance_weekly, latest
    WHERE week_start_date = latest.this_week - INTERVAL '7 days'
)
SELECT tw.val AS "SĐT chết", lw.val AS "Tuần trước"
FROM this_week tw, last_week lw
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": {} }
```

```json metabase-pos
{ "row": 3, "col": 12, "size_x": 4, "size_y": 3 }
```

---

#### 📝 Text: Bảng chi tiết theo nhân viên

📋 Bảng chi tiết theo nhân viên — 8 tuần gần nhất, sắp xếp tuần mới nhất trước.

```json metabase-pos
{ "row": 6, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Staff x Tuần — Chi tiết

```sql
WITH latest AS (
    SELECT MAX(week_start_date) AS max_week
    FROM main_marts.mart_staff_performance_weekly
)
SELECT
    full_name                AS "Nhân viên",
    week_start_date           AS "Tuần",
    calls_dialed               AS "Cuộc gọi",
    contacts_reached           AS "Đã tiếp cận",
    reach_rate_pct             AS "Reach rate %",
    conversations_count        AS "Hội thoại thật",
    outcome_notes_count        AS "Note kết quả",
    health_concern_tags_new    AS "Tag sức khỏe mới",
    other_tags_new             AS "Tag khác mới",
    orders_sold                AS "Đơn bán"
FROM main_marts.mart_staff_performance_weekly, latest
WHERE week_start_date >= latest.max_week - INTERVAL '49 days'
ORDER BY week_start_date DESC, calls_dialed DESC
```

```json metabase-viz
{
  "display": "table",
  "visualization_settings": {
    "table.pivot": false,
    "column_settings": {
      "[\"name\",\"Reach rate %\"]": { "suffix": "%", "decimals": 1 }
    }
  }
}
```

```json metabase-pos
{ "row": 7, "col": 0, "size_x": 18, "size_y": 7 }
```

---

#### 📝 Text: Xu hướng phễu tiếp cận

📈 Xu hướng phễu tiếp cận theo tuần — Cuộc gọi → Đã tiếp cận → Hội thoại thật (toàn team, 8 tuần gần nhất).

```json metabase-pos
{ "row": 14, "col": 0, "size_x": 18, "size_y": 1 }
```

#### ❓ Question: Phễu tiếp cận theo tuần

```sql
WITH latest AS (
    SELECT MAX(week_start_date) AS max_week
    FROM main_marts.mart_staff_performance_weekly
)
SELECT
    week_start_date AS "Tuần",
    SUM(calls_dialed) AS "Cuộc gọi",
    SUM(contacts_reached) AS "Đã tiếp cận",
    SUM(conversations_count) AS "Hội thoại thật"
FROM main_marts.mart_staff_performance_weekly, latest
WHERE week_start_date >= latest.max_week - INTERVAL '49 days'
GROUP BY 1
ORDER BY 1
```

```json metabase-viz
{
  "display": "line",
  "visualization_settings": {
    "graph.dimensions": ["Tuần"],
    "graph.metrics": ["Cuộc gọi", "Đã tiếp cận", "Hội thoại thật"],
    "series_settings": {
      "Cuộc gọi": { "color": "#509EE3" },
      "Đã tiếp cận": { "color": "#7172AD" },
      "Hội thoại thật": { "color": "#84BB4C" }
    }
  }
}
```

```json metabase-pos
{ "row": 15, "col": 0, "size_x": 18, "size_y": 6 }
```

---

#### ❓ Question: Độ tươi dữ liệu

```sql
SELECT
    '🕐 Tuần dữ liệu mới nhất: ' || strftime(MAX(week_start_date), '%d/%m/%Y')
    || '  ·  Số staff có hoạt động: ' || COUNT(DISTINCT CASE WHEN week_start_date = (SELECT MAX(week_start_date) FROM main_marts.mart_staff_performance_weekly) AND calls_dialed > 0 THEN staff_key END)::VARCHAR
    AS "Độ tươi dữ liệu"
FROM main_marts.mart_staff_performance_weekly
```

```json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
```

```json metabase-pos
{ "row": 98, "col": 0, "size_x": 18, "size_y": 2 }
```
<!-- text-id:trust-block -->

#### 📝 Text: Source & Freshness

**Source:** mart_staff_performance_weekly (CRM activities + Sapo orders, grain staff × ISO week) · **Cadence:** weekly (review thứ Hai) · **Scope:** toàn bộ staff có `staff_key` khớp `dim_staff` (không lọc contact_quality — xem rủi ro dưới) · **Window:** 8 tuần gần nhất cho bảng/biểu đồ, tuần mới nhất vs tuần liền trước cho scalar
<!-- text-id:source-freshness -->

```json metabase-pos
{ "row": 100, "col": 0, "size_x": 18, "size_y": 1 }
```

---

## Rủi ro / câu hỏi mở (mang từ phase-04 plan)

- Reach rate % thấp có thể do data chất lượng contact kém (`contact_quality='masked'`), không hẳn do rep gọi kém — dashboard hiện CHƯA tách theo `contact_quality`. Cân nhắc thêm card riêng nếu review thực tế cho thấy cần.
- `activities_call` là proxy chính xác cho `channel_type='call'` nhưng KHÔNG tách được zalo/fb (cả hai gộp vào `activity_type='chat'`) — Track B (Zalo-connect count) sẽ bổ sung riêng, ghi rõ trong text card đầu dashboard.
- Ngưỡng 60s cho `conversations_count` là ước tính ban đầu (xem `schema.yml` — cần kiểm tra tỷ lệ NULL của `contact_duration_s` để chốt lại).

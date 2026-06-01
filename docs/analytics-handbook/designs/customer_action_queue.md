## Design Spec: Customer Action Queue [Retail]

> **Tài liệu này là bản thiết kế tool-agnostic cho dashboard/report.**
> Nó chuyển playbook thành cấu trúc trình bày cụ thể: views, card roles, loại biểu đồ chuẩn, bộ lọc, thứ tự đọc, so sánh cần có, màu sắc/kích thước theo semantic tokens và các yêu cầu trải nghiệm phân tích.
> Design spec là hợp đồng giữa Analytics Design và bước triển khai BI; nó không phụ thuộc vào bất kỳ công cụ BI hay nền tảng triển khai cụ thể nào, nhưng được dùng làm input để tạo blueprint triển khai cho công cụ BI được chọn.

---

## Overview

| Field | Value |
|-------|-------|
| **Audience** | Customer Success / Sales team |
| **Purpose** | Daily dispatch board — who to contact today and why |
| **Archetype** | Operational Queue (single-view dispatch board) |
| **Data Source** | `mart_customer_action_queue` (snapshot, refreshes daily) |
| **Scope** | RETAIL customers only, action_type IS NOT NULL |
| **Blueprint** | `blueprints/customer_action_queue.md` |

---

## Phase 3 — Design Brief

- **Hero metric**: Total customers in queue (count needing outreach today)
- **Key question**: Which customers do I contact today, and in what order?
- **Comparison frame**: Priority rank (urgency) + value at stake (revenue impact)
- **Time budget**: <2 min to open and begin calling
- **View grouping**: Single view (no tabs — dispatch boards must be instantly scannable)

---

## Phase 4 — Composition Design

### Card Roles

| Card | Role | Size |
|------|------|------|
| Chu kỳ báo cáo | annotation | `full-width` × `minimal` |
| Section header (queue today) | annotation | `full-width` × `minimal` |
| CALL_NOW count | supporting | `one-third` × `short` |
| REORDER_NUDGE count | supporting | `one-third` × `short` |
| WIN_BACK count | supporting | `one-third` × `short` |
| SECOND_ORDER count | supporting | `one-quarter` × `short` |
| HIGH_CANCEL_RISK count | supporting | `one-quarter` × `short` |
| Section header (value breakdown) | annotation | `full-width` × `minimal` |
| Value at stake by action type | breakdown | `half` × `medium` |
| Customer count by action type | breakdown | `half` × `medium` |
| Section header (queue list) | annotation | `full-width` × `minimal` |
| Queue table | detail | `full-width` × `tall` |
| Source & Freshness | annotation | `full-width` × `minimal` |

### Narrative Flow

1. **When** — Chu kỳ báo cáo: when was the queue generated?
2. **How many** — 5 KPI scalars: count per action type at a glance
3. **Where the money is** — Value at stake + count bars side by side
4. **Who exactly** — Queue table ranked by priority + CLV

---

## Phase 5 — Visualization Selection

| Card | Viz Type | Reasoning |
|------|----------|-----------|
| Count KPIs (5×) | `single-value` | Categorical count, no time series |
| Value at stake by action | `horizontal-bar` | Categorical ranking, labels need space |
| Customer count by action | `horizontal-bar` | Parallel categorical comparison |
| Queue table | `data-table-formatted` | Operational list + conditional formatting on value |

---

## Phase 6 — Enrichment

### Filters

| Filter | Type | Purpose |
|--------|------|---------|
| `action_type` | `category/single-select` | Focus on one action type |
| `value_group` | `category/single-select` | Narrow to customer tier |

### Comparative Framing

- Count KPIs have no time comparison (snapshot — no historical equivalent available)
- Horizontal bars are self-comparative (categories ranked by priority)
- Table sorted by priority_rank DESC, then lifetime_value DESC (highest value per tier first)

### Conditional Formatting (table)

- `value_at_stake`: green if > 0 (highlight revenue opportunity)
- `recency_days`: red if > 60 (long-absent customers)
- `cancel_rate`: red if > 0.5 (high cancel risk highlight)

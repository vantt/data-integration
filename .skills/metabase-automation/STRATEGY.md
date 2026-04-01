# Metabase Implementation Strategy (Engineer Brain)

This document provides the **Metabase-specific** strategy for implementing analytics. For **design thinking** (archetypes, viz selection, composition, visual language), see `.skills/analytics-design/SKILL.md`.

## 1. 2-Skill Collaboration

Trước khi tạo blueprint, agent phải hoàn thành Phase 0-6 (Analytics Design) để có Design Spec.

**Quy trình đầy đủ:**

```
Phase 0-6 (Analytics Design)  →  Design Spec  →  Phase 7-10 (Metabase Automation)
```

| Phase | Agent đọc | Agent KHÔNG đọc |
|-------|-----------|-----------------|
| 0-6 (Analyst) | `.skills/analytics-design/*` | `.skills/metabase-automation/*` |
| 7-10 (Engineer) | `.skills/metabase-automation/*`, Design Spec, domain files | `.skills/analytics-design/*` |

**Input cho Phase 7**: Design Spec tại `docs/analytics-handbook/designs/<name>.md` — chứa standard viz terms, color/size tokens, composition table.

**Translation reference**: `METABASE_VIZ_CATALOG.md` — mapping standard vocab → Metabase settings.

## 2. Semantic Layer Strategy (Data Modeling)

Do not pollute Metabase with raw SQL fragments. Use the **Pyramid Principle**:

1.  **Base (Models)**: Create a "Trusted Dataset" (Model) (`dataset: true`) for core entities (e.g., `Official Orders`).
    - _Why_: Hides complex Joins/Casting from non-technical users.
2.  **Middle (Metrics)**: Define standard calculations (e.g., `Revenue`, `AOV`) on the Model.
    - _Why_: Ensures "Revenue" is calculated identically everywhere.
3.  **Top (Questions)**: Only visuals should be "Questions".
    - _Rule_: A Dashboard Question should rarely have raw SQL. It should query a **Model**.

## 3. Automation Workflow

When receiving a request to create/update a blueprint:

1.  **Verify Design Spec exists** — Check `docs/analytics-handbook/designs/`. If missing, run Phase 0-6 first (or use `/design-dashboard`).
2.  **Check Semantic Layer** — Does a `Model` already exist for this data? If no, **Create Model First**.
3.  **Translate** — Map standard vocab → Metabase display types using `METABASE_VIZ_CATALOG.md`.
4.  **Configure** — Generate `metabase-viz` JSON with full settings (colors, axes, formatting).
5.  **Assemble** — Write blueprint with SQL + viz + pos blocks.
6.  **Deploy** — Use `deploy_from_markdown.js`.

### Pre-deploy Check (Phase 10)

Before deploying, verify design spec staleness:

1. Find corresponding design spec (`designs/<name>.md`)
2. Compare `last_modified` dates in frontmatter (blueprint vs design spec)
3. If blueprint is newer → warn: "Blueprint modified directly after design spec. Design spec may be out-of-sync."
4. If no design spec exists (legacy blueprint) → info: "No design spec for this blueprint."
5. Warning is **informational only** — does not block deploy.

## 4. Dashboard Archetypes (Quick Reference)

For full archetype definitions, card roles, and composition patterns, see `.skills/analytics-design/COMPOSITION_PATTERNS.md`.

| Archetype | Default For | Key Trait |
|-----------|-------------|-----------|
| **Executive Pulse** | CEO/Board asks | ≤10 cards, glanceable, no tables |
| **Operational Cockpit** | "Sales Dashboard" (default) | Filters + breakdowns + detail table |
| **Exploratory Tool** | Deep-dive requests | Many filters, pivot/scatter |

**Rule:** If user asks for "Sales Dashboard" without specifying → default to **Operational Cockpit**.

## 5. Parser Limitations & Post-Deploy Workarounds

Markdown parser (`lib/markdown_parser.js`) chỉ hỗ trợ một số block types. Các tính năng sau **KHÔNG được parser xử lý** và cần workaround thủ công.

### 5.1 Text Annotations (CRITICAL)

**Parser KHÔNG hỗ trợ `#### Text:` headers.** Khi blueprint chứa `#### Text:` với `metabase-pos` block, parser sẽ gán position đó cho question card trước đó → **ghi đè position, gây sai layout toàn bộ**.

**Quy tắc:** KHÔNG bao giờ đặt `#### Text:` sections trong blueprint. Thay vào đó:

1. Viết blueprint chỉ với `#### Question:` sections (không có text annotations)
2. Deploy blueprint bình thường
3. Thêm text cards qua API sau deploy:

```javascript
// Shift existing cards down để tạo chỗ cho text headings
// Rồi PUT /api/dashboard/:id với dashcards bao gồm text cards:
{
  id: -1,              // negative ID cho card mới
  card_id: null,       // null = text card, không phải question
  dashboard_tab_id: tabId,
  row: 0, col: 0, size_x: 18, size_y: 1,
  visualization_settings: {
    virtual_card: {
      name: null, display: "text",
      visualization_settings: {}, dataset_query: {}, archived: false
    },
    text: "# Section Heading"
  },
  parameter_mappings: []
}
```

**Lưu ý:** PUT `/api/dashboard/:id` phải gửi cả `tabs` VÀ `dashcards` cùng lúc (Metabase yêu cầu).

### 5.2 Dashboard Filters (`metabase-filter`)

**Parser KHÔNG xử lý `metabase-filter` blocks.** Template tags trong SQL (`{{date}}`) được tạo tự động, nhưng dashboard-level parameter và mapping thì không.

**Quy trình sau deploy:**

1. Thêm dashboard parameter:
```bash
curl -X PUT "$METABASE_URL/api/dashboard/:id" \
  -d '{"parameters": [{"id": "date_filter", "name": "Date", "slug": "date", "type": "date/single"}]}'
```

2. Map parameter tới cards bằng PUT dashboard với `tabs` + `dashcards` (thêm `parameter_mappings` cho mỗi card cần filter):
```json
{
  "parameter_mappings": [{
    "parameter_id": "date_filter",
    "card_id": 123,
    "target": ["variable", ["template-tag", "date"]]
  }]
}
```

**Lưu ý:** PUT `/api/dashboard/:id/cards` (endpoint riêng) KHÔNG hoạt động cho việc update parameter_mappings. Phải dùng PUT `/api/dashboard/:id` với full payload `{ tabs, dashcards }`.

### 5.3 Dashboard Update vs Create

Deploy script (`deploy_from_markdown.js`) luôn **tạo dashboard MỚI** nếu không tìm thấy dashboard cùng tên (chưa archived) trong collection. Nếu muốn cập nhật dashboard hiện tại:

- Script sẽ reuse dashboard nếu tên trùng khớp chính xác
- Nếu đổi tên dashboard → script tạo mới → cần archive dashboard cũ thủ công
- Archive dashboard + questions qua API: `PUT /api/dashboard/:id {"archived": true}` và `PUT /api/card/:id {"archived": true}`

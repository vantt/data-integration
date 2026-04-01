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

**Parser HỖ TRỢ `#### Filter:` headers và `metabase-filter` JSON blocks.**

Khai báo filters trong blueprint trước các Tab/Question headers:

```markdown
#### Filter: Date Range

\`\`\`json metabase-filter
{
  "slug": "date_range",
  "type": "date/all-options",
  "default": "past7days"
}
\`\`\`
```

**Auto-wiring:** Deploy script tự động match filter `slug` với SQL `{{template_tag}}` cùng tên. Ví dụ: filter slug `date_range` → auto-wire tới `{{date_range}}` trong SQL.

**Supported types:** `date/all-options`, `date/single`, `string/=`, `string/contains`, `number/=`, `number/between`.

### 5.3 Dashboard Update vs Create

Deploy script **HỖ TRỢ overwrite/update** — KHÔNG cần tạo mới + archive cũ.

**Cơ chế hoạt động:**

1. `Dashboard.ensure(name)` tìm dashboard theo tên (toàn hệ thống, không chỉ collection) → nếu tồn tại thì reuse (kể cả unarchive nếu cần)
2. Mỗi question được match theo `(tab_name, card_name)` → nếu đã tồn tại thì **PUT update SQL/viz**, không tạo mới
3. `syncCards()` PUT toàn bộ dashcards → **overwrite layout hoàn toàn**

**Khi nào script tạo mới (thay vì update):**

- Đổi tên dashboard trong blueprint (ví dụ: `Orders` → `Order Listing`) → `find("Order Listing")` không tìm thấy "Orders" → tạo mới
- Archive dashboard cũ trước khi deploy → `find()` không thấy → tạo mới

**Quy trình đúng khi đổi tên dashboard:**

1. Đổi tên trên Metabase trước (qua API): `PUT /api/dashboard/:id {"name": "Order Listing"}`
2. Rồi deploy blueprint với tên mới → script tìm thấy → overwrite

**Quy trình đúng khi update dashboard (không đổi tên):**

1. Sửa blueprint (SQL, viz, positions)
2. Deploy lại → script tự tìm dashboard + questions hiện tại → update in-place

**Chỉ cần archive thủ công khi:** muốn xóa dashboard hoàn toàn (không phải khi update).
```bash
# Archive dashboard + questions
curl -X PUT "$METABASE_URL/api/dashboard/:id" -d '{"archived": true}'
curl -X PUT "$METABASE_URL/api/card/:id" -d '{"archived": true}'
```

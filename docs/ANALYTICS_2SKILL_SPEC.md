# Analytics 2-Skill Architecture — Specification

> **Status**: v11 — fixed 5 more issues (Row F overflow, design spec frontmatter, pivot reverse disambiguation, planned metric lifecycle, e2e example size sync)
> **Created**: 2026-04-01
> **Updated**: 2026-04-01
> **Location**: `docs/ANALYTICS_2SKILL_SPEC.md` — meta-document, không thuộc riêng skill nào
> **Purpose**: Kiến trúc 2-skill cho analytics pipeline: Analytics Design (analyst brain, tool-agnostic) sở hữu và tạo ra toàn bộ analytics artifacts (domains, playbooks, guides, designs) + Metabase Automation (engineer brain, tool-specific) triển khai implementation.

---

## I. Chẩn đoán gốc rễ (Evidence-based)

### Triệu chứng 1: "Wall of Scalars" — mất visual hierarchy

CEO Weekly Pulse có **10 scalar liên tiếp** (Gross Revenue, Net Revenue, Total Orders, AOV, Cancelled Orders, Returns, New Customers, Returning Revenue %, Discount Rate) — tất cả cùng display type `"scalar"`, cùng kích thước tương đương, không có gì phân biệt đâu là con số quan trọng nhất. Mắt người đọc không biết nhìn vào đâu trước.

### Triệu chứng 2: Số liệu thiếu ngữ cảnh so sánh

"Net Revenue: ₫500M" một mình nó **không mang ý nghĩa gì**. Nó tốt hay xấu? Đang tăng hay giảm? So với target thì sao? Hầu hết scalar trong blueprint hiện tại là số trần, không có trend, không có period comparison, không có goal.

### Triệu chứng 3: Sai visualization cho data shape

- "MTD Revenue vs Target Pace" — chứa Achievement % và Pace Index — được hiển thị bằng **table**. Đây chính xác là use case của **progress bar** hoặc **gauge**.
- "Revenue by Channel Category" — comparison 3 categories với WoW% — là **horizontal bar** chứ không phải table.
- "Health Score" (0-100) — hiển thị scalar. Đây là use case kinh điển của **gauge** với color segments.

### Triệu chứng 4: Không có narrative structure

Không text card nào, không heading nào, không annotation nào. Dashboard là danh sách phẳng các con số, không dẫn dắt người đọc qua câu chuyện dữ liệu.

### Gốc rễ — 2 tầng

**Tầng 1 (Design)**: Agent thiếu knowledge framework để đưa ra quyết định thiết kế có chủ đích. STRATEGY.md hiện tại chỉ có ~10 dòng heuristic chung chung, không đủ để agent hiểu mỗi viz type truyền tải thông điệp gì, khi nào nên dùng, dashboard cần narrative structure ra sao.

**Tầng 2 (Architecture)**: Toàn bộ quy trình hiện tại trộn lẫn 2 mindset khác nhau trong cùng 1 skill (`metabase-automation`):
- **Analyst mindset**: Nghĩ về truyền thông dữ liệu, chọn visualization, thiết kế narrative — đây là kiến thức **không phụ thuộc vào tool**
- **Engineer mindset**: Triển khai trong Metabase, sinh JSON settings, gọi API — đây là kiến thức **phụ thuộc vào tool**

Hệ quả của việc trộn lẫn:
- Agent không phân biệt khi nào đang "nghĩ" vs "làm"
- Thuật ngữ viz bị gắn chặt vào Metabase (`"display": "scalar"` thay vì khái niệm `single-value`)
- Nếu đổi sang Superset/Looker/Power BI → mất toàn bộ design knowledge vì nó nằm lẫn trong Metabase docs
- Không có ngôn ngữ chung (contract) giữa bước thiết kế và bước triển khai

---

## II. Hiện trạng: Skill landscape & Analytics-handbook

### Skill hiện tại

Chỉ có **1 skill**: `.skills/metabase-automation/` — làm tất cả từ analytics thinking đến deploy.

### Analytics-handbook đã tự nhiên phân tách

`docs/analytics-handbook/` **đã có** sự phân tách nội dung, dù được tạo bởi cùng 1 skill:

| Thư mục | Số files | Bản chất | Mindset |
|---------|----------|----------|---------|
| `domains/` | 6 | Định nghĩa metrics, công thức, dbt models | **Analyst** — tool-agnostic |
| `playbooks/` | ~20 | Hướng dẫn vận hành, audience, mục đích | **Analyst** — tool-agnostic |
| `guides/` | 6 | Health Score, revenue terms, design patterns | **Hỗn hợp** — phần lớn tool-agnostic |
| `blueprints/` | ~12 | SQL + `metabase-viz` JSON + `metabase-pos` JSON | **Engineer** — 100% Metabase-specific |

**Nhận xét**: Artifact store (analytics-handbook) đã phân tách đúng. Vấn đề là **skill tạo ra chúng** thì không phân tách.

---

## III. Pipeline hiện tại và GAP

```
User request
  → ① Phân loại Archetype (Pulse / Cockpit / Tool)          ← analyst thinking, nhưng nằm trong metabase skill
  → ② Quyết định metrics/questions                          ← analyst thinking
  → ③ Viết SQL                                              ← engineering
  → ④ Gán display type (heuristic sơ sài)                   ← GAP: analyst decision bị làm bằng engineer mindset
  → ⑤ Sinh viz settings (gần như trống)                      ← GAP: engineer output thiếu chất lượng
  → ⑥ Gán position (cảm tính)                               ← GAP: không có composition thinking
  → ⑦ Assemble blueprint                                    ← engineering
  → ⑧ Deploy                                                ← engineering
```

**3 gaps liền kề** (bước 4-5-6) nhưng gốc rễ nằm **sớm hơn** — thiếu bước thiết kế tổng thể dashboard, và thiếu sự phân tách giữa THIẾT KẾ (analyst) và TRIỂN KHAI (engineer).

---

## IV. Kiến trúc đề xuất: 2 Skills + Standard Vocabulary

### Cấu trúc thư mục

```
.skills/
├── analytics-design/                  ← MỚI: Analyst Brain (tool-agnostic)
│   ├── SKILL.md                       ← Tổng quan + quy trình tạo TẤT CẢ artifact types
│   ├── DOMAIN_MODELING.md             ← Cách định nghĩa domains: metrics, formulas, dbt refs
│   ├── VISUALIZATION_VOCABULARY.md    ← Bộ thuật ngữ chuẩn 25 viz types + 1 composition concept (view-group)
│   ├── COMPOSITION_PATTERNS.md        ← Archetypes, card roles, narrative flow, view grouping, filter design
│   ├── VISUAL_LANGUAGE.md             ← Color semantics, size semantics, quy tắc sử dụng
│   ├── COMPARATIVE_FRAMING.md         ← Quy tắc ngữ cảnh hóa số liệu
│   └── templates/
│       ├── domain_template.md         ← Cấu trúc chuẩn cho domain file
│       ├── playbook_template.md       ← Cấu trúc chuẩn cho playbook file
│       ├── guide_template.md          ← Cấu trúc chuẩn cho guide file
│       └── design_spec_template.md    ← Format chuẩn cho Design Spec
│
├── metabase-automation/               ← CÓ SẴN: Engineer Brain (refactored)
│   ├── SKILL.md                       ← Giữ nguyên API reference
│   ├── STRATEGY.md                    ← Refactored: chỉ giữ Metabase-specific strategy
│   ├── METABASE_VIZ_CATALOG.md        ← MỚI: Mapping standard vocab → Metabase settings
│   ├── scripts/                       ← Giữ nguyên toàn bộ
│   ├── lib/                           ← Giữ nguyên toàn bộ
│   └── templates/                     ← Giữ nguyên

docs/analytics-handbook/               ← Artifact store — OWNED by analytics-design
├── domains/                           ← CREATED by: analytics-design
├── playbooks/                         ← CREATED by: analytics-design
├── guides/                            ← CREATED by: analytics-design
├── designs/                           ← CREATED by: analytics-design (MỚI)
└── blueprints/                        ← CREATED by: metabase-automation (duy nhất)
```

### Vai trò & ranh giới từng skill

**Analytics Design Skill** — "Tôi là analyst brain, tôi NGHĨ, ĐỊNH NGHĨA, và THIẾT KẾ"

| Sở hữu & Tạo ra | Không biết gì về |
|-------------------|-------------------|
| **Domains**: định nghĩa metrics, business concepts, formulas | Metabase API |
| **Playbooks**: operational context, audience, mục đích, cách đọc | `visualization_settings` JSON |
| **Guides**: reference material, methodology, terminology | `metabase-viz`, `metabase-pos` |
| **Design Specs**: composition, viz selection, visual language | Hex color codes, pixel values |
| Dashboard archetypes (Pulse/Cockpit/Tool) | Deploy scripts |
| Card roles (hero/supporting/trend/breakdown/detail) | Bất kỳ BI tool cụ thể nào |
| Standard visualization vocabulary | |
| Visual language: color semantics & size semantics | |
| Narrative flow & composition patterns | |
| Comparative framing rules | |

**Metabase Automation Skill** — "Tôi là engineer, tôi TRIỂN KHAI trong Metabase"

| Sở hữu & Tạo ra | Không quyết định |
|-------------------|-------------------|
| **Blueprints**: Metabase-specific implementation (SQL + JSON) | Nên dùng viz type nào |
| Mapping standard vocab → Metabase display types | Dashboard narrative structure |
| Mapping color/size tokens → concrete hex/px values | Card roles hay composition |
| Metabase-specific viz settings & JSON templates | Metric definitions |
| Tool limitations & alternative suggestions | Audience hay purpose |
| Blueprint format (Literate Configuration) | |
| Deploy scripts & API client | |

### Contract giữa 2 skills: Design Spec

Design Spec là artifact trung gian — output của Analytics Design, input của Metabase Automation. Dùng **thuật ngữ chuẩn**, không đề cập tool nào:

```markdown
---
title: CEO Weekly Pulse
archetype: Executive Pulse
status: final
last_modified: 2026-04-01
domain_refs: [domains/sales.md, domains/customer.md]
---

## Design Spec: CEO Weekly Pulse

### Brief
- Audience: CEO, Co-founders
- Time budget: 5 phút, Monday morning
- Primary question: "Tuần qua kinh doanh có on-track không?"
- Decision enabled: Can thiệp khẩn hay tiếp tục như hiện tại
- Comparison frame: WoW (tuần này vs tuần trước)
- Archetype: Executive Pulse
- Domain references: domains/sales.md, domains/customer.md

### Constraints & Filters

**Business Constraints** — luôn áp dụng, hardcode trong SQL, user không tương tác:

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude US channel | `channel_category != 'US'` | All cards | Đơn nội bộ, 100% discount |

**Interactive Filters** — user có thể thay đổi trên dashboard:

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| *(Không có — Executive Pulse cần zero-interaction)* | | | | |

### Views

Single view (≤10 cards, glanceable executive dashboard).

### Composition

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Revenue Performance This Week" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 2 | B | Revenue vs Target | hero | gauge | positive/warning/negative (zones) | one-third × medium, prominent | "Đang ở đâu so với mục tiêu tháng" | vs monthly target, 3 zones |
| 3 | B | Net Revenue | supporting | single-value-with-trend | primary, trend: positive/negative | one-quarter × short, standard | "Doanh thu thuần + hướng đi" | vs previous week |
| 4 | B | Total Orders | supporting | single-value-with-trend | secondary, trend: positive/negative | one-quarter × short, standard | "Volume + hướng đi" | vs previous week |
| 5 | B | AOV | supporting | single-value-with-trend | secondary, trend: positive/negative | one-quarter × short, standard | "Giá trị TB + ổn định?" | vs previous week |
| 6 | C | "Trend & Direction" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 7 | D | Revenue 14-day | trend | line-chart | primary, muted (previous week) | full-width × medium | "Xu hướng 2 tuần" | implicit (visual) |
| 8 | E | "What's Driving Results" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 9 | F | Revenue by Channel | breakdown | horizontal-bar | series-1..3 | half × medium | "Kênh nào đóng góp nhiều nhất" | WoW% per category |
| 10 | F | New vs Returning | breakdown | stacked-bar-time | series-emphasis (Returning), muted (New) | half × medium | "Cơ cấu khách thay đổi thế nào" | over time |
```

**Đặc điểm quan trọng**:
- **Frontmatter bắt buộc**: `title`, `archetype`, `status` (`final` | `draft` | `draft-from-capture`), `last_modified` (YYYY-MM-DD), `domain_refs` (danh sách domain files tham chiếu). Agent cập nhật `last_modified` mỗi khi sửa file.
- **Row column** chỉ rõ cards nào cùng hàng — cùng Row letter = cùng 1 hàng. Tổng width trong mỗi row phải = `full-width` (vd: Row B = one-third + one-quarter×3 = 6+4+4+4 = 18 ✓, Row F = half + half = 9+9 = 18 ✓)
- Không có `"display"`, `metabase-viz`, `metabase-pos`, hay bất kỳ JSON nào
- Text annotations có nội dung cụ thể ("Revenue Performance This Week"), không generic ("KPIs")
- Filters, Views, Composition đều dùng **thuần ngôn ngữ analyst**
- Nếu đổi từ Metabase sang Superset, Design Spec **không thay đổi** — chỉ thay skill triển khai

---

## V. Standard Visualization Vocabulary

Bộ thuật ngữ chuẩn mà Analytics Design Skill sử dụng. **Không phụ thuộc vào bất kỳ BI tool nào.**

| # | Standard Term | Communication Strength | Metabase Support |
|---|--------------|----------------------|------------------|
| 1 | `single-value` | Snapshot — "con số hiện tại" | ✅ Native (`scalar`) |
| 2 | `single-value-with-trend` | Snapshot + direction — "đang tăng hay giảm" | ✅ Native (`scalar` + comparison) |
| 3 | `progress-toward-goal` | Linear progress — "đã đạt bao nhiêu % mục tiêu" | ✅ Native (`progress`) |
| 4 | `gauge` | Position in range — "đang ở vùng nào (nguy hiểm/cảnh báo/tốt)" | ✅ Native (`gauge`) |
| 5 | `line-chart` | Trend — "biến động theo thời gian" | ✅ Native (`line`) |
| 6 | `multi-line-chart` | Multi-series trend — "so sánh xu hướng nhiều đối tượng" | ✅ Native (`line` multi-series) |
| 7 | `area-chart` | Volume trend — "xu hướng với emphasis vào khối lượng" | ✅ Native (`area`) |
| 8 | `stacked-area` | Composition over time — "thành phần nào drive thay đổi tổng" | ✅ Native (`area` + stack) |
| 9 | `vertical-bar` | Categorical comparison — "cái nào lớn hơn" | ✅ Native (`bar`) |
| 10 | `horizontal-bar` | Ranked comparison — "top N, bottom N" | ✅ Native (`row`) |
| 11 | `stacked-bar` | Categorical composition — "cấu thành của mỗi category" | ✅ Native (`bar` + stack) |
| 12 | `grouped-bar` | Side-by-side comparison — "so sánh trực tiếp 2+ nhóm" | ✅ Native (`bar` grouped) |
| 13 | `stacked-bar-time` | Composition over time (discrete) — "cấu thành thay đổi qua từng kỳ" | ✅ Native (`bar` + stack + time) |
| 14 | `combo-chart` | Dual-metric correlation — "2 metrics có tương quan không" | ✅ Native (`combo`) |
| 15 | `donut` | Part-to-whole (static) — "tỷ lệ phần trăm" (≤5 phần) | ✅ Native (`pie`) |
| 16 | `funnel` | Sequential conversion — "drop-off ở bước nào" | ✅ Native (`funnel`) |
| 17 | `waterfall` | Additive contributions — "yếu tố nào tăng/giảm tổng" | ✅ Native (`waterfall`) |
| 18 | `data-table` | Detail & lookup — "dữ liệu đầy đủ cho drill-down" | ✅ Native (`table`) |
| 19 | `data-table-formatted` | Detail + alerts — "highlight dòng/ô cần chú ý" | ✅ Native (`table` + conditional formatting) |
| 20 | `pivot-table` | Multi-dimensional — "cross-tab analysis" | ✅ Native (`pivot`) |
| 21 | `scatter-plot` | Correlation — "2 biến có liên hệ gì" | ✅ Native (`scatter`) |
| 22 | `geographic-map` | Spatial distribution — "phân bố theo địa lý" | ✅ Native (`map`) |
| 23 | `heatmap` | Intensity matrix — "đậm/nhạt theo 2 chiều" | ⚠️ Fallback (`pivot` + conditional formatting) |
| 24 | `sparkline` | Inline mini-trend — "trend nhỏ gọn kèm theo số" | ⚠️ Fallback (`scalar` + trend) |
| 25 | `text-annotation` | Narrative — "heading, ghi chú, giải thích" | ✅ Native (text dashcard) |

**Composition concept** (không phải viz type — không xuất hiện trong Phase 5 decision tree):

| Concept | Mô tả | Metabase Support |
|---------|-------|------------------|
| `view-group` | Logical grouping — nhóm cards thành 1 view riêng biệt. Quyết định ở **Phase 4d**, không phải Phase 5. | ✅ Native (dashboard tabs) |

Mỗi term trong `VISUALIZATION_VOCABULARY.md` được định nghĩa bằng:
- **Communication strength**: truyền tải thông điệp gì (1 câu)
- **Data shape**: cấu trúc dữ liệu cần thiết
- **Best for**: use cases phù hợp
- **Avoid when**: anti-patterns
- **Không có** bất kỳ tool-specific settings nào

---

## VI. Visual Language — Color & Size Semantics

Màu sắc và kích cỡ là **ngôn ngữ thị giác** — analyst quyết định ý nghĩa (semantic intent), engineer dịch sang giá trị cụ thể (concrete values). Analytics Design Skill sở hữu semantic layer, Metabase Automation sở hữu concrete mapping.

### Color Semantics

Analyst sử dụng **semantic color tokens**, không dùng hex values:

**Status Colors** — truyền tải trạng thái tốt/xấu của metric:

| Token | Ý nghĩa | Khi nào dùng |
|-------|---------|-------------|
| `positive` | Tốt, đạt mục tiêu, tăng trưởng | KPI vượt target, trend đi lên khi lên = tốt |
| `negative` | Xấu, dưới ngưỡng, sụt giảm | KPI dưới target, trend đi xuống khi xuống = xấu |
| `warning` | Cần chú ý, gần ngưỡng | KPI gần sát ngưỡng, biến động bất thường |
| `neutral` | Trung tính, không đánh giá | Metric mô tả, không có tốt/xấu rõ ràng |

**Structural Colors** — cho elements không mang data meaning:

| Token | Ý nghĩa | Khi nào dùng |
|-------|---------|-------------|
| `structural` | Nền, phân cách, heading | Text annotations, section dividers, card borders |

**Hierarchy Colors** — truyền tải mức độ quan trọng thị giác:

| Token | Ý nghĩa | Khi nào dùng |
|-------|---------|-------------|
| `primary` | Nổi bật nhất, thu hút mắt đầu tiên | Hero metric, series chính trong chart |
| `secondary` | Quan trọng nhưng không phải trọng tâm | Supporting metrics, series phụ |
| `muted` | Làm nền, không gây chú ý | Baseline, reference lines, previous period |
| `accent` | Điểm nhấn đặc biệt | Highlight một data point cụ thể, anomaly |

**Series Colors** — phân biệt categories trong chart:

| Token | Ý nghĩa | Khi nào dùng |
|-------|---------|-------------|
| `series-1` .. `series-N` | Phân biệt thị giác giữa N categories | Multi-series line, stacked bar, donut slices |
| `series-emphasis` | Nhấn mạnh 1 series so với phần còn lại | Khi muốn highlight 1 category cụ thể trong nhóm |

**Conditional Colors** — áp dụng động dựa trên giá trị data:

| Token | Ý nghĩa | Khi nào dùng |
|-------|---------|-------------|
| `conditional-above` | Giá trị vượt ngưỡng trên | Table cell formatting, bar highlight |
| `conditional-below` | Giá trị dưới ngưỡng dưới | Table cell formatting, bar highlight |
| `conditional-range` | Gradient theo range giá trị | Heatmap, intensity encoding |

**Quy tắc sử dụng color**:

1. **Status colors chỉ dùng khi có tiêu chí đánh giá rõ ràng** — nếu không xác định được "tốt" hay "xấu", dùng `neutral`
2. **Không dùng quá 2 status colors trên cùng 1 card** — tránh "Christmas tree effect"
3. **Series colors tối đa 5-7** — quá nhiều sẽ không phân biệt được
4. **Hierarchy colors phải nhất quán trong toàn dashboard** — `primary` luôn là cùng 1 color intent
5. **Color không bao giờ là kênh truyền tải DUY NHẤT** — luôn kết hợp với text, icon, hoặc position (accessibility)
6. **Colorblind safety** — trong cùng 1 card/chart, không dùng 2+ colors mà chỉ khác nhau ở red-green spectrum (vd: `positive` + `negative` cùng lúc phải kèm text label hoặc icon ▲/▼ để phân biệt)
7. **`structural` thay cho `neutral` ở non-data elements** — text annotations, section headings dùng `structural`, không dùng `neutral` (neutral chỉ dành cho metrics không có đánh giá tốt/xấu)

### Size Semantics

Analyst sử dụng **semantic size tokens** cho text/number prominence, không dùng pixel values:

**Text/Number Size** — mức độ nổi bật của con số hoặc label:

| Token | Ý nghĩa | Card Role phù hợp |
|-------|---------|-------------------|
| `prominent` | Lớn nhất, đập vào mắt ngay | Hero metric value |
| `standard` | Kích cỡ đọc bình thường | Supporting KPI values, chart labels |
| `compact` | Nhỏ, tiết kiệm không gian | Detail table values, secondary info |
| `caption` | Rất nhỏ, phụ trợ | Subtitle, footnote, last-updated timestamp |

**Card Size** — kích cỡ tương đối của card trên dashboard grid (tool-agnostic, không gắn với grid system cụ thể):

| Token | Ý nghĩa |
|-------|---------|
| `full-width` | Chiếm toàn bộ chiều ngang |
| `two-thirds` | Chiếm ~2/3 chiều ngang |
| `half` | Chiếm ~1/2 chiều ngang |
| `one-third` | Chiếm ~1/3 chiều ngang |
| `one-quarter` | Chiếm ~1/4 chiều ngang (grid-constrained: thực tế ~22% trên 18-col grid) |
| `one-sixth` | Chiếm ~1/6 chiều ngang |

**Card Height**:

| Token | Ý nghĩa | Phù hợp với |
|-------|---------|-------------|
| `tall` | Cao, cho viz cần vertical space | Funnel, vertical bar nhiều categories |
| `medium` | Cao vừa phải | Line chart, area chart, bar chart |
| `short` | Thấp, compact | KPI scalars, progress bars |
| `minimal` | Rất thấp | Text annotations, section headings |

**Quy tắc sử dụng size**:

1. **Hero card phải visually dominant** — dùng `one-third` trở lên cho width, `prominent` cho text size
2. **Supporting cards phải nhỏ hơn Hero** — nếu Hero là `one-third`, Supporting là `one-quarter` hoặc `one-sixth`
3. **Trend/Breakdown cards nên rộng** — `two-thirds` hoặc `full-width` để data series có chỗ render
4. **Annotations luôn `full-width` + `minimal` height** — heading/divider không chiếm nhiều space
5. **Tổng các cards trong 1 row phải = `full-width`** — tránh gaps hoặc overflow. **⚠️ Lưu ý 18-col grid**: `one-quarter` = 4 cols (22%), không chính xác 1/4. Các combo hợp lệ: `one-third + 3×one-quarter` (6+4+4+4=18), `half + half` (9+9=18), `one-third + two-thirds` (6+12=18), `6×one-sixth` (3×6=18). **Không dùng** `4×one-quarter` (4×4=16 ≠ 18).

### Visual Language trong Design Spec

Color và Size tokens được ghi trực tiếp trong bảng Composition của Design Spec (xem ví dụ canonical trong Section IV). Engineer đọc tokens này và dịch sang concrete values của tool (hex codes, grid units) theo mapping tables trong `METABASE_VIZ_CATALOG.md`.

---

## VII. Pipeline tối ưu — 2 Skills collaboration

```
User: "Tạo dashboard daily sales cho operations team"
  │
  ▼
┌──────────────────────────────────────────────────────────────┐
│  ANALYTICS DESIGN SKILL (Analyst brain — CHỦ ĐỘNG)           │
│  Đọc knowledge từ: .skills/analytics-design/*                │
│                                                              │
│  Phase 0: Domain Modeling                                    │
│    → Kiểm tra domain đã tồn tại? (domains/sales.md)         │
│    → Tạo MỚI hoặc CẬP NHẬT domain file                      │
│    → Định nghĩa metrics, formulas, dbt model references     │
│    OUTPUT: docs/analytics-handbook/domains/<domain>.md       │
│                                                              │
│  Phase 1: Playbook Creation                                  │
│    → Tạo MỚI hoặc CẬP NHẬT playbook                         │
│    → Xác định audience, purpose, cách sử dụng dashboard     │
│    OUTPUT: docs/analytics-handbook/playbooks/<name>.md       │
│                                                              │
│  Phase 2: Guide Creation (nếu cần)                           │
│    → Có concept phức tạp cần giải thích riêng?               │
│    → vd: Health Score methodology, revenue terminology       │
│    OUTPUT: docs/analytics-handbook/guides/<topic>.md          │
│                                                              │
│  Phase 3: Design Brief                                       │
│    → Audience, purpose, hero metric, comparison frame        │
│                                                              │
│  Phase 4: Composition Design                                 │
│    → Card roles, narrative flow, spatial grouping            │
│    → View grouping (single vs multi-view)                    │
│    → Filter design (what to filter, defaults, rationale)     │
│    → Companion cards (text annotations, comparisons)         │
│                                                              │
│  Phase 5: Visualization Selection                            │
│    → Standard vocabulary terms                               │
│    → Decision tree: role × data shape × comm goal            │
│    → Visual language: color & size semantics                 │
│    → Anti-pattern check                                      │
│                                                              │
│  Phase 6: Enrichment Check                                   │
│    → Comparative framing (mọi KPI cần ≥1 so sánh)           │
│    → Data completeness cho viz type đã chọn                  │
│    → Narrative support (text cards, labels)                  │
│                                                              │
│  OUTPUT: Design Spec (tool-agnostic)                         │
│  Lưu tại: docs/analytics-handbook/designs/<name>.md          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  METABASE AUTOMATION SKILL (Engineer brain — TRIỂN KHAI)     │
│  Đọc knowledge từ: .skills/metabase-automation/*             │
│  Input: Design Spec + Domain definitions                     │
│                                                              │
│  Phase 7: Translation                                        │
│    → Map standard vocab → Metabase display types             │
│    → Map color/size tokens → concrete hex/grid values        │
│    → Kiểm tra tool limitations, đề xuất alternatives         │
│                                                              │
│  Phase 8: Configuration Generation                           │
│    → Sinh metabase-viz JSON đầy đủ settings                  │
│    → Sinh metabase-pos với sizing theo card role              │
│    → Column formatting, colors, goal lines                   │
│                                                              │
│  Phase 9: Blueprint Assembly                                 │
│    → Viết/điều chỉnh SQL (dựa trên domain definitions)      │
│    → Filter wiring (parameters, template tags, mappings)     │
│    → Assemble Literate Configuration markdown                │
│    OUTPUT: docs/analytics-handbook/blueprints/<name>.md      │
│                                                              │
│  Phase 10: Deploy                                            │
│    → deploy_from_markdown.js (có sẵn)                        │
│    OUTPUT: Live Metabase Dashboard                           │
└──────────────────────────────────────────────────────────────┘
```

### Fast-track path (cho dashboard đơn giản)

Không phải mọi dashboard đều cần 11 phases đầy đủ. Áp dụng fast-track khi:

| Điều kiện | Phase bỏ qua | Lý do |
|-----------|-------------|-------|
| Domain đã tồn tại, đầy đủ metrics cần thiết | Phase 0 (skip) | Chỉ cần verify, không cần tạo/cập nhật |
| Playbook đã tồn tại cho audience + purpose này | Phase 1 (skip) | Chỉ cần verify |
| Không có concept phức tạp mới | Phase 2 (skip) | Mặc định đã skip nếu không cần |
| Dashboard ≤5 cards, single view, 1 archetype rõ ràng | Phase 3-6 (collapse thành 1 bước) | Gộp Brief + Composition + Viz Selection + Enrichment thành 1 Design Spec ngắn gọn |

**Full path** (11 phases): Dashboard mới, domain mới, >5 cards, hoặc multi-view.
**Fast-track** (5-7 phases): Domain + playbook sẵn có, ≤5 cards, single view → skip Phase 0-2, collapse Phase 3-6.
**Hotfix** (2 phases): Sửa SQL/settings nhỏ → Phase 9 + 10 only (Flow C trong Section XIV).

**Quy tắc**: Khi nghi ngờ, dùng full path. Fast-track chỉ khi **tất cả** điều kiện ở cột 1 thỏa mãn.

### Artifact creation summary

| Artifact | Created by | When |
|----------|-----------|------|
| `domains/<domain>.md` | Analytics Design (Phase 0) | Tạo mới khi metric chưa tồn tại; cập nhật khi thêm metric |
| `playbooks/<name>.md` | Analytics Design (Phase 1) | Tạo mới cho mỗi dashboard; cập nhật khi đổi audience/purpose |
| `guides/<topic>.md` | Analytics Design (Phase 2) | Chỉ khi có concept phức tạp cần giải thích riêng |
| `designs/<name>.md` | Analytics Design (Phase 3-6) | Tạo mới cho mỗi dashboard design |
| `blueprints/<name>.md` | Metabase Automation (Phase 9) | Tạo mới từ design spec; cập nhật khi sửa implementation |

### Thứ tự tạo artifact (bắt buộc)

```
domain → playbook → [guide] → design spec → blueprint → deploy
```

Mỗi artifact downstream **tham chiếu** artifact upstream:
- Playbook tham chiếu domain ("`xem domains/sales.md cho định nghĩa Net Revenue`")
- Design spec tham chiếu playbook + domain
- Blueprint tham chiếu design spec + domain

### Agent Orchestration — Cách 1 agent chạy 2 skills

Trong thực tế, **1 Claude agent duy nhất** chạy toàn bộ pipeline trong 1 conversation. "2 skills" không phải 2 agent riêng biệt — mà là **2 knowledge domains** mà agent đọc ở các thời điểm khác nhau. Cơ chế phân tách mindset dựa vào **slash command prompt** điều khiển agent đọc doc nào ở phase nào.

**Quy tắc đọc docs theo phase**:

| Phase | Agent đọc | Agent KHÔNG đọc |
|-------|-----------|-----------------|
| 0-6 (Analyst) | `.skills/analytics-design/*` | `.skills/metabase-automation/*` (trừ khi cần kiểm tra tool feasibility) |
| 7-10 (Engineer) | `.skills/metabase-automation/*`, Design Spec output từ Phase 6, domain files | `.skills/analytics-design/*` (đã internalize qua Design Spec) |

**Command prompt pattern** — mỗi slash command phải enforce thứ tự:

```
/create-metabase-blueprint:
  "Step 1: Read .skills/analytics-design/SKILL.md. Execute Phase 0-6.
   Output: domain file, playbook, design spec — save to disk.
   Step 2: Read .skills/metabase-automation/SKILL.md. Execute Phase 7-10.
   Input: Design Spec created in Step 1."

/design-dashboard:
  "Read .skills/analytics-design/SKILL.md. Execute Phase 0-6 only.
   Output: domain file, playbook, design spec."

/deploy-metabase-blueprint:
  "Read .skills/metabase-automation/SKILL.md. Execute Phase 10 only."
```

**Tại sao phân tách docs quan trọng**: Nếu agent đọc `METABASE_VIZ_CATALOG.md` (chứa Metabase display types) trong khi đang làm Phase 5 (viz selection), nó sẽ bị anchor vào Metabase terminology thay vì suy nghĩ bằng standard vocabulary. Design Spec sẽ chứa `"scalar"` thay vì `single-value-with-trend` — đúng vấn đề spec này muốn giải quyết.

**Exception duy nhất**: Trong Phase 5, nếu analyst cần kiểm tra "Metabase có hỗ trợ viz type này không?", agent có thể scan bảng Metabase Support trong Section V (đã tóm tắt sẵn trong vocabulary table) mà **không cần** đọc full `METABASE_VIZ_CATALOG.md`.

---

## VIII. Phase details — Analytics Design Skill (Phase 0-6)

### Phase 0 — Domain Modeling

**Input**: User request — xác định domain nào cần.

**Quy trình**:

1. **Kiểm tra domain đã tồn tại?** — Quét `docs/analytics-handbook/domains/` xem đã có file cho domain này chưa
2. **Nếu đã có** → Đọc file, kiểm tra metrics cần thiết cho dashboard mới đã được định nghĩa chưa. Nếu thiếu → cập nhật thêm.
3. **Nếu chưa có** → Tạo mới theo `templates/domain_template.md`

**Nội dung domain file** (agent đọc `DOMAIN_MODELING.md` để biết cách viết):
- Danh sách metrics với định nghĩa business, công thức tính
- Data source references (dbt model, table name)
- Relationships giữa metrics (Gross Revenue → Net Revenue → Total Collected)
- Phân loại: leading vs lagging, absolute vs relative

**Output**: `docs/analytics-handbook/domains/<domain>.md` — tạo mới hoặc cập nhật.

**Quy tắc**:
- 1 domain file = 1 business domain (sales, customer, logistics, finance...)
- Không duplicate metric definitions — nếu metric đã có trong domain khác, tham chiếu thay vì copy
- Mỗi metric phải có: tên, định nghĩa 1 dòng, công thức, đơn vị, source

**Metric status lifecycle** — mỗi metric trong domain file có thể mang 1 trong 3 trạng thái:

| Status | Ý nghĩa | Khi nào |
|--------|---------|---------|
| `active` | Metric đã có dbt model/table, sẵn sàng query | Mặc định khi tạo metric từ source đã tồn tại |
| `planned` | Metric được định nghĩa nhưng chưa có data source | Khi Phase 0 cần metric mà dbt model chưa tồn tại (xem failure modes, Section IX) |
| `deprecated` | Metric không còn dùng, giữ lại để tham khảo | Khi metric bị thay thế bởi metric khác |

Chuyển trạng thái: `planned` → `active` khi dbt model được tạo và data đã populate. Engineer (hoặc dbt developer) cập nhật status trong domain file sau khi model deploy thành công. Agent kiểm tra status trước khi viết SQL — nếu metric là `planned`, ghi rõ trong blueprint: "⚠️ Metric chưa có data source, SQL dùng giá trị ước lượng hoặc placeholder."

### Phase 1 — Playbook Creation

**Input**: Domain knowledge + user request (audience, mục đích dashboard).

**Quy trình**:

1. **Kiểm tra playbook đã tồn tại?** — Quét `docs/analytics-handbook/playbooks/`
2. **Nếu đã có** → Đọc, cập nhật nếu audience/purpose thay đổi
3. **Nếu chưa có** → Tạo mới theo `templates/playbook_template.md`

**Nội dung playbook file**:
- **Audience**: Ai đọc dashboard này, ở role gì
- **Purpose**: Dashboard trả lời câu hỏi gì
- **Frequency**: Xem lúc nào, bao lâu 1 lần
- **How to read**: Hướng dẫn đọc — nhìn đâu trước, flow đọc
- **Actions**: Khi thấy signal X → hành động Y
- **Domain references**: Link đến domain files cho metric definitions

**Output**: `docs/analytics-handbook/playbooks/<name>.md` — tạo mới hoặc cập nhật.

### Phase 2 — Guide Creation (conditional)

**Input**: Domain + playbook — xác định có concept phức tạp cần giải thích riêng không.

**Quy trình**:

1. **Có concept mới phức tạp không?** — vd: Health Score composite, revenue waterfall methodology
2. **Nếu không** → Bỏ qua, chuyển sang Phase 3
3. **Nếu có** → Tạo guide theo `templates/guide_template.md`

**Ví dụ khi cần guide**:
- Lần đầu dùng composite metric (Health Score) → tạo `guides/health_score.md`
- Thuật ngữ dễ nhầm lẫn (Gross vs Net vs Collected Revenue) → tạo `guides/revenue_terminology.md`
- Methodology phức tạp (cohort analysis, RFM scoring) → tạo guide riêng

**Output**: `docs/analytics-handbook/guides/<topic>.md` — hoặc bỏ qua.

### Phase 3 — Design Brief

**Input**: User request + domain knowledge + playbook context.

**Output**: Brief ngắn gọn xác định mục tiêu dashboard.

| Trường | Mô tả | Ví dụ |
|--------|-------|-------|
| **Audience** | Ai đọc, ở vai trò gì (từ playbook) | CEO — đọc 5 phút sáng thứ Hai |
| **Primary Question** | Câu hỏi chính dashboard trả lời | "Tuần qua kinh doanh có on-track không?" |
| **Decision Enabled** | Quyết định gì được kích hoạt | Can thiệp khẩn hay tiếp tục |
| **Hero Metric** | Con số quan trọng nhất (từ domain) | Net Revenue vs Target pace |
| **Comparison Frame** | So sánh với gì | WoW (tuần này vs tuần trước) |
| **Time Budget** | Bao lâu để đọc | Glanceable — dưới 5 phút |
| **Archetype** | Pulse / Cockpit / Tool | Executive Pulse |

### Phase 4 — Composition Design (dashboard-level)

**Input**: Danh sách metrics (từ domain, Phase 0) + Design Brief (Phase 3).

**Mục đích**: Tổ chức dashboard như một tác phẩm truyền thông thay vì danh sách phẳng.

**4a. Card Role Assignment** — Mỗi card được gán VAI TRÒ:

| Role | Chức năng | Đặc trưng thị giác |
|------|-----------|---------------------|
| **Hero** | Con số quan trọng nhất, trả lời Primary Question | Lớn nhất, vị trí trên cùng, nổi bật nhất |
| **Supporting KPI** | Metrics bổ sung cung cấp context cho Hero | Nhỏ hơn Hero, cùng hàng hoặc hàng kế |
| **Trend** | Biến động theo thời gian, cho thấy hướng đi | Trải rộng (wide), nằm ở mid-section |
| **Breakdown** | Phân tích theo dimension (kênh, sản phẩm, vùng) | Medium size, ở giữa dashboard |
| **Detail** | Dữ liệu chi tiết để drill-down | Dạng table, nằm cuối, full-width |
| **Annotation** | Text card — heading, ghi chú, cảnh báo | Không chứa data, chỉ chứa text |

**4b. Narrative Flow** — Sắp xếp cards theo arc kể chuyện:

```
[Annotation: Section heading]
  → Hero + Supporting KPIs     "Chúng ta đang ở đâu?"
[Annotation: Section heading]
  → Trends                     "Chúng ta đang đi theo hướng nào?"
[Annotation: Section heading]
  → Breakdowns                 "Điều gì đang drive kết quả này?"
  → Details                    "Chi tiết cho ai muốn đào sâu"
```

**4c. Spatial Grouping** — Cards cùng logic group đặt gần nhau. Xác định relative sizing (Hero chiếm 1/3 width vs Supporting chiếm 1/6 width).

**4d. View Grouping** — Khi dashboard quá nhiều cards cho 1 view, chia thành nhiều `view-group`:

| Pattern | Khi nào | Ví dụ |
|---------|---------|-------|
| **Single view** | ≤8 cards, audience đọc nhanh | Executive Pulse |
| **Multi-view** | >8 cards, hoặc có nhiều audience/purpose | Daily Ops (Overview → Trends → Analysis → Details) |

Mỗi view-group có:
- Tên view (tool-agnostic — Metabase sẽ dịch thành tabs)
- Narrative flow riêng (mỗi view kể 1 phần câu chuyện)
- Cards thuộc view đó

**4e. Constraints & Filter Design** — Xác định 2 loại data scoping:

**Business Constraints** — điều kiện luôn áp dụng, user không tương tác. Engineer hardcode trong SQL `WHERE`:

| Trường | Mô tả | Ví dụ |
|--------|-------|-------|
| **Constraint name** | Mô tả ngắn | "Exclude US channel" |
| **Rule** | Logic lọc | `channel_category != 'US'` |
| **Applies to** | Cards nào bị ảnh hưởng | "All cards" |
| **Rationale** | Tại sao | "Đơn nội bộ, 100% discount" |

**Interactive Filters** — user có thể thay đổi trên dashboard. Engineer dịch thành Metabase parameter types và SQL template tags:

| Trường | Mô tả | Ví dụ |
|--------|-------|-------|
| **Filter name** | Tên hiển thị | "Date Range", "Channel" |
| **Filter type** | Loại filter (date, category, text, number) | date/range, category/single-select |
| **Default value** | Giá trị mặc định | "Last 7 days", "All channels" |
| **Applies to** | Cards nào bị ảnh hưởng | "All cards" hoặc danh sách cụ thể |
| **Business rationale** | Tại sao cần filter này | "Cho phép xem theo khoảng thời gian khác nhau" |

Cả 2 loại đều là **analyst decision** (WHAT to scope) — engineer quyết định HOW (SQL WHERE vs Metabase parameter).

**4f. Companion Card Identification** — Xác định cần thêm card phụ trợ:
- Text cards cho section headings (nội dung cụ thể, không generic — "Revenue Performance This Week" thay vì chỉ "KPIs")
- Comparison cards (nếu Hero cần "vs target" nhưng chưa có)
- Summary/conclusion text

**Output**: Composition Plan — bảng liệt kê tất cả cards với role, view-group, relative size, grouping, narrative position + Filter list.

### Phase 5 — Visualization Selection (card-level)

**Input**: Mỗi card từ Composition Plan + **abstract data shape**.

**Về data shape**: Analyst không cần biết SQL cụ thể. Data shape được suy ra từ **domain definition** (metric là gì, đơn vị gì) + **design intent** (muốn thấy gì). Ví dụ:
- Domain nói "Net Revenue = SUM(net_revenue)" → analyst biết đây là **single value**
- Design intent "muốn thấy trend 14 ngày" → analyst biết cần **time series, daily, 14 points**
- Design intent "breakdown theo channel" → analyst biết cần **categories × 1 measure**

Engineer (Phase 9) sau đó viết SQL để produce đúng data shape mà analyst yêu cầu. Nếu data shape không khả thi (vd: data source không có chiều đó), engineer feedback lại và analyst điều chỉnh.

**Mục đích**: Chọn viz type bằng **standard vocabulary** dựa trên giao điểm:

```
Card Role  ×  Data Shape  ×  Communication Goal  →  Standard Viz Term
```

**Decision tree**:

```
1. Card là Annotation? → text-annotation, kết thúc
2. Data shape?
   ├── Single value → single-value / gauge / progress-toward-goal
   ├── Single value + target → progress-toward-goal / gauge
   ├── Time series → line-chart / area-chart / vertical-bar
   ├── Categories (≤7) → vertical-bar / donut / horizontal-bar
   ├── Categories (>7) → data-table / horizontal-bar (top N)
   ├── Categories × Time → stacked-bar-time / stacked-area
   ├── Sequential stages → funnel
   ├── Additive parts → waterfall
   └── Two measures → scatter-plot / combo-chart
3. Chọn từ candidates bằng Communication Goal:
   ├── "position vs target" → gauge (range) / progress-toward-goal (linear)
   ├── "trend direction" → line-chart / single-value-with-trend
   ├── "compare categories" → horizontal-bar
   ├── "composition" → donut (≤5) / stacked-bar (>5 or over time)
   ├── "ranking" → horizontal-bar (sorted)
   └── "detail lookup" → data-table-formatted
4. Cross-check với Role:
   ├── Hero → ưu tiên visual impact (gauge > single-value)
   └── Detail → ưu tiên density (data-table, pivot-table)
5. Anti-pattern check:
   ├── donut > 5 slices? → vertical-bar
   ├── line-chart cho non-temporal? → vertical-bar
   ├── gauge cho metric không có range rõ? → single-value-with-trend
   └── stacked-bar với 1 series? → vertical-bar
```

**Output per card**: Standard viz term + reasoning (1 dòng).

**Lưu ý về `view-group`**: `view-group` không xuất hiện trong decision tree vì nó là **composition decision** (Phase 4d), không phải card-level viz decision. Xem Phase 4d cho quy tắc chia views.

**Lưu ý**: Decision tree trên cover ~19/25 viz terms cho các use cases phổ biến. 6 terms edge-case được resolve bằng analyst judgment thay vì tree:
- `multi-line-chart`: chọn khi `line-chart` có ≥2 series (implicit từ data shape)
- `grouped-bar`: chọn khi cần side-by-side comparison thay vì stacked (analyst judgment)
- `pivot-table`: chọn khi cần cross-tab 2+ dimensions (thay vì `data-table` flat)
- `geographic-map`: chọn khi data có geographic dimension (tỉnh/thành, quốc gia)
- `heatmap` / `sparkline`: rare — xem full documentation trong `VISUALIZATION_VOCABULARY.md`

### Phase 6 — Enrichment Check (card-level)

**Input**: Card + viz type đã chọn.

**6a. Comparative Framing** — Bắt buộc: mọi KPI phải có ≥1 so sánh:

| Loại so sánh | Khi nào | Ghi chú |
|--------------|---------|---------|
| **vs Previous Period** | Mọi KPI periodic | "tăng/giảm bao nhiêu %" |
| **vs Target/Goal** | Khi có target rõ ràng | "đạt bao nhiêu % mục tiêu" |
| **vs Benchmark** | Khi có internal/external benchmark | "so với trung bình" |
| **Rank/Position** | Khi so sánh categories | "đứng thứ mấy" |

**6b. Data Completeness** — Viz type có yêu cầu data đặc biệt?

| Viz Type (standard) | Yêu cầu |
|---------------------|----------|
| gauge | min, max, goal, zone boundaries |
| progress-toward-goal | goal value |
| funnel | ordered stages |
| combo-chart | ≥2 metrics trên shared axis |
| stacked-bar / stacked-area | dimension column cho series |

**6c. Narrative Support** — cần text cards, labels, descriptions bổ sung?

**Output per card**: Danh sách điều chỉnh cần thiết (tool-agnostic).

---

## IX. Failure modes & feedback loops

Khi một phase không hoàn thành được, pipeline cần xử lý thay vì dừng lại:

### Analyst phases (0-6) — failures

| Phase | Failure | Xử lý |
|-------|---------|-------|
| Phase 0 | Metric cần dùng nhưng dbt model chưa tồn tại | Ghi metric vào domain file với `status: planned`. Tiếp tục design. Engineer (Phase 9) viết SQL ước lượng hoặc flag cần dbt work. |
| Phase 0 | Không xác định được domain nào (request mơ hồ) | Dừng, hỏi user clarify trước khi tiếp tục. |
| Phase 5 | Không tìm được viz type phù hợp trong vocabulary | Dùng `data-table` làm safe fallback — mọi data shape đều render được dạng table. Ghi note "needs better viz". |
| Phase 6 | KPI không có comparison frame khả thi (vd: metric hoàn toàn mới, không có period trước) | Chấp nhận `single-value` không trend. Ghi note: "comparison available after 1+ period of data". |

### Engineer phases (7-10) — failures

| Phase | Failure | Xử lý |
|-------|---------|-------|
| Phase 7 | Design spec yêu cầu viz type mà Metabase không support (heatmap, sparkline) | Dùng fallback mapping trong Phase 7 table. Ghi vào blueprint: "Design: X → Metabase: Y (fallback, vì Z)". |
| Phase 7 | Color/size token không có trong mapping table | Dùng `neutral` / `standard` làm default. Flag để cập nhật `METABASE_VIZ_CATALOG.md`. |
| Phase 9 | SQL produce data shape khác với design spec yêu cầu | **Feedback loop**: engineer điều chỉnh SQL nếu có thể. Nếu data source không hỗ trợ shape đó → feedback lại analyst (quay về Phase 5) để chọn viz type phù hợp với data shape thực tế. |
| Phase 10 | Deploy fail (API error, permission) | Retry. Nếu structural (vd: unsupported setting) → fix blueprint (Phase 9), không quay lại design. |

### Feedback direction

```
Analyst → Engineer: Design Spec (forward, bình thường)
Engineer → Analyst: Chỉ khi data shape KHÔNG KHẢ THI
                    → Analyst điều chỉnh viz type hoặc data shape requirement
                    → KHÔNG thay đổi business intent (hero metric, audience, purpose)
```

**Quy tắc**: Engineer không bao giờ tự ý thay đổi card roles, narrative flow, hay hero metric. Nếu implementation constraint buộc thay đổi design intent, phải escalate.

---

## X. Phase details — Metabase Automation Skill (Phase 7-10)

### Phase 7 — Translation (standard vocab → Metabase)

**Input**: Design Spec với standard viz terms.

Agent tra cứu `METABASE_VIZ_CATALOG.md` để dịch:

| Standard Term | Metabase Display | Ghi chú |
|--------------|-----------------|---------|
| `single-value` | `scalar` | |
| `single-value-with-trend` | `scalar` + trend settings | Cần cấu hình comparison |
| `progress-toward-goal` | `progress` | |
| `gauge` | `gauge` | |
| `line-chart` | `line` | |
| `multi-line-chart` | `line` (multi-series) | |
| `area-chart` | `area` | |
| `stacked-area` | `area` + stack settings | |
| `vertical-bar` | `bar` | |
| `horizontal-bar` | `row` | |
| `stacked-bar` | `bar` + stack settings | |
| `grouped-bar` | `bar` (grouped mode) | |
| `stacked-bar-time` | `bar` + stack + time axis | |
| `combo-chart` | `combo` | |
| `donut` | `pie` | |
| `funnel` | `funnel` | |
| `waterfall` | `waterfall` | |
| `data-table` | `table` | |
| `data-table-formatted` | `table` + conditional formatting | |
| `pivot-table` | `pivot` | |
| `scatter-plot` | `scatter` | |
| `geographic-map` | `map` | |
| `heatmap` | **Không hỗ trợ trực tiếp** → `pivot` + conditional formatting | Limitation |
| `sparkline` | **Không hỗ trợ trực tiếp** → `scalar` + trend | Limitation |
| `text-annotation` | text dashcard | |
| `view-group` | Dashboard tab (`### 📑 Tab:` in blueprint) | Tabs + dashcards in single PUT request |

Khi Metabase không hỗ trợ, skill phải:
1. Document limitation rõ ràng
2. Đề xuất alternative gần nhất
3. Ghi chú vào blueprint: "Design spec yêu cầu X, Metabase triển khai bằng Y vì Z"

**Color token → Metabase mapping** (trong `METABASE_VIZ_CATALOG.md`):

| Semantic Token | Metabase Hex | Ghi chú |
|---------------|-------------|---------|
| `positive` | `#84BB4C` | Metabase green |
| `negative` | `#EF8C8C` | Metabase red |
| `warning` | `#F9D45C` | Metabase yellow |
| `neutral` | `#98D9D9` | Metabase teal — metric trung tính, không tốt/xấu |
| `structural` | `#949AAB` | Metabase muted gray — text annotations, headings |
| `primary` | `#509EE3` | Metabase blue — brand primary |
| `secondary` | `#88BDE6` | Lighter blue |
| `muted` | `#C2D2E9` | Very light, background |
| `accent` | `#7172AD` | Deep purple — stand-out highlight, visually distinct from both `negative` (red) và `positive` (green) |
| `series-1` | `#509EE3` | Metabase palette slot 1 |
| `series-2` | `#88BDE6` | Metabase palette slot 2 |
| `series-3` | `#A989C5` | Metabase palette slot 3 |
| `series-4` | `#F2A86F` | Orange — tránh trùng `negative` (#EF8C8C) trên cùng dashboard |
| `series-5` | `#F9D45C` | Metabase palette slot 5 |
| `conditional-above` | `#84BB4C` | Table conditional formatting |
| `conditional-below` | `#EF8C8C` | Table conditional formatting |

**Quy tắc**: Tokens **trong cùng context group** phải map sang hex khác nhau (vd: status colors phải khác nhau, hierarchy colors phải khác nhau). Cross-group overlap là chấp nhận được — `series-1` có thể trùng `primary` vì chúng không bao giờ xuất hiện trên cùng 1 element (series dùng cho charts, hierarchy dùng cho card-level). Bảng trên là Metabase defaults — có thể customize theo brand palette trong `METABASE_VIZ_CATALOG.md`.

**Size token → Metabase mapping**:

| Semantic Token | Metabase Implementation | Ghi chú |
|---------------|------------------------|---------|
| `prominent` | Scalar with large font (default scalar behavior) | Metabase scalars auto-size to fill card |
| `standard` | Standard chart/table text | Default rendering |
| `compact` | Table with compact density | `table.cell_height: "compact"` nếu có |
| `caption` | Card description/subtitle | Dùng card description field |
| `full-width` | `size_x: 18` | Metabase grid = 18 columns |
| `two-thirds` | `size_x: 12` | |
| `half` | `size_x: 9` | |
| `one-third` | `size_x: 6` | |
| `one-quarter` | `size_x: 4` | Dùng `5` chỉ khi cần fit 3 cards trong 14-col layout (rare) |
| `one-sixth` | `size_x: 3` | |
| `tall` | `size_y: 9` | Dùng `10` cho funnel/bar >10 categories |
| `medium` | `size_y: 6` | Dùng `5` cho chart ít data points (<7) |
| `short` | `size_y: 3` | Dùng `4` cho scalar cards cần subtitle/description |
| `minimal` | `size_y: 1` | Dùng `2` cho text annotations dài hơn 1 dòng |

**Limitations**: Metabase có giới hạn trong việc control font size trực tiếp — scalar cards auto-resize text to fit. Engineer phải dùng card sizing (`size_x`, `size_y`) để gián tiếp control text prominence. Nếu tool không hỗ trợ granular font sizing, ghi chú limitation.

### Phase 8 — Configuration Generation

**Input**: Metabase display type + enrichment requirements + data columns.

Sinh `json metabase-viz` đầy đủ:

```json
{
  "display": "<metabase_type>",
  "visualization_settings": {
    // Layout & Axes
    "graph.dimensions": ["..."],
    "graph.metrics": ["..."],
    "graph.x_axis.title_text": "...",
    "graph.y_axis.title_text": "...",

    // Series & Colors
    "graph.colors": ["..."],
    "series_settings": {
      "<name>": { "color": "#...", "display": "line|bar|area" }
    },

    // Goal & Reference Lines
    "graph.goal_value": 1000000,
    "graph.goal_label": "Target",
    "graph.show_goal": true,

    // Column Formatting
    "column_settings": {
      "<column>": {
        "number_style": "currency|percent|decimal",
        "currency": "VND",
        "decimals": 0,
        "suffix": "%",
        "compact": true
      }
    },

    // Table-specific
    "table.pivot": false,
    "table.column_formatting": [
      { "columns": ["Status"], "type": "single",
        "operator": "=", "value": "Báo động",
        "color": "#EF8C8C", "highlight_row": true }
    ],

    // Gauge-specific
    "gauge.segments": [
      { "min": 0, "max": 40, "color": "#EF8C8C", "label": "Danger" },
      { "min": 40, "max": 70, "color": "#F9D45C", "label": "Warning" },
      { "min": 70, "max": 100, "color": "#84BB4C", "label": "Good" }
    ],

    // Stacking
    "stackable.stack_type": "stacked|normalized",

    // Progress-specific
    "progress.goal": 500000000,
    "progress.color": "#84BB4C"
  }
}
```

Sinh `json metabase-pos` — **priority order khi resolve sizing**:

1. **Design Spec explicit instruction wins** — nếu design spec ghi `one-third × medium`, dịch trực tiếp via Phase 7 token mapping (`one-third` → `size_x: 6`, `medium` → `size_y: 5-6`)
2. **Role-based defaults** — chỉ dùng khi design spec KHÔNG chỉ định size (vd: design spec chỉ ghi role mà không ghi size tokens)

Role-based defaults (fallback):

| Role | Default Size | Ghi chú |
|------|-------------|---------|
| Hero (gauge/progress) | `size_x: 6, size_y: 5` | 1/3 width, medium height |
| Hero (scalar+trend) | `size_x: 6, size_y: 4` | 1/3 width, short-medium |
| Supporting KPI | `size_x: 4, size_y: 3` | 1/4 width; dùng `3` nếu hàng có 6 cards |
| Trend (line/area) | `size_x: 12, size_y: 6` | 2/3 width; dùng `18` nếu là card duy nhất trong hàng |
| Breakdown (bar/donut) | `size_x: 9, size_y: 6` | 1/2 width; dùng `12` nếu cần thêm space cho labels |
| Detail (table) | `size_x: 18, size_y: 8` | Full width; dùng `10` nếu >10 rows visible |
| Annotation (text) | `size_x: 18, size_y: 1` | Full width; dùng `2` nếu text dài hơn 1 dòng |

### Phase 9 — Blueprint Assembly

**9a. SQL**: Viết/điều chỉnh SQL dựa trên domain definitions (Phase 0), abstract data shapes (Phase 5), và enrichment requirements (Phase 6). **SQL dialect: DuckDB** (target database "Sapo DuckDB"). DuckDB largely PostgreSQL-compatible nhưng có khác biệt — đặc biệt date/time functions (`DATE_TRUNC`, `INTERVAL`, `CURRENT_DATE` đều hỗ trợ). Xem DuckDB docs khi dùng advanced functions.

**9b. Filter Wiring**: Dịch filter design (Phase 4e) sang Metabase implementation:
- Filter type (date/range, category/single-select) → Metabase parameter type (`date/all-options`, `string/=`)
- "Applies to: All cards" → `parameter_mappings` cho mỗi dashcard
- SQL cần `template_tags` cho mỗi filter variable (vd: `{{date}}`, `{{channel}}`)
- Default values → dashboard parameter defaults

**9c. Assemble**: Kết hợp tất cả thành Literate Configuration markdown (blueprint).

### Phase 10 — Deploy

**Pre-deploy check** (mới): Trước khi deploy, kiểm tra design spec staleness:

1. Xác định design spec tương ứng (`designs/<name>.md`)
2. Nếu design spec tồn tại → so sánh **frontmatter `last_modified` date** giữa blueprint và design spec. Nếu blueprint `last_modified` > design spec `last_modified` → warn: "⚠️ Blueprint đã được sửa trực tiếp sau design spec. Design spec có thể out-of-sync."
   - **Không dùng file mtime** — git không preserve mtime, sau clone/checkout mtime = thời điểm checkout.
   - Nếu frontmatter thiếu `last_modified`, fallback: `git log -1 --format=%ai -- <filepath>` để lấy commit date.
3. Nếu design spec không tồn tại (blueprint legacy) → warn: "ℹ️ Không có design spec cho blueprint này. Xem xét tạo bằng reverse flow."
4. Warning chỉ là **informational** — không block deploy. Agent thông báo user, user quyết định có cần re-sync không.

**Frontmatter requirement**: Mọi design spec và blueprint phải có `last_modified: YYYY-MM-DD` trong frontmatter. Agent cập nhật field này mỗi khi sửa file. Đây là **best-effort** — nếu human edit file trực tiếp mà quên cập nhật frontmatter, `git log` fallback vẫn catch được. Priority: frontmatter (nhanh, không cần git) → `git log -1` (chính xác hơn, cần committed changes).

`deploy_from_markdown.js` — không thay đổi (pre-deploy check thực hiện ở agent level, không phải script level).

---

## XI. Analytics-handbook — Ownership model

Analytics-handbook là artifact store. Ownership dựa trên **skill nào tạo ra**:

```
docs/analytics-handbook/
│
│  ┌── OWNED & CREATED BY: Analytics Design Skill ──────────┐
│  │                                                         │
├── domains/        ← WHAT: metrics, definitions            │
├── playbooks/      ← WHY & WHO: audience, mục đích         │
├── guides/         ← HOW TO THINK: reference material      │
├── designs/        ← HOW TO SHOW: design specs (MỚI)       │
│  │                                                         │
│  └─────────────────────────────────────────────────────────┘
│
│  ┌── OWNED & CREATED BY: Metabase Automation Skill ───────┐
│  │                                                         │
└── blueprints/     ← HOW TO BUILD: implementation          │
   │                                                         │
   └─────────────────────────────────────────────────────────┘
```

**Thứ tự tạo artifact**: domain → playbook → [guide] → design → blueprint → deploy

**Quy tắc ownership** (knowledge boundary, không phải access control):

Ownership nghĩa là: artifact X được tạo **dưới sự hướng dẫn của knowledge** từ skill Y. Trong thực tế, 1 agent chạy cả pipeline sẽ tạo tất cả artifacts — nhưng phải đọc **đúng knowledge docs** khi tạo từng loại (xem Agent Orchestration, Section VII).

- Khi tạo `domains/`, `playbooks/`, `guides/`, `designs/` → agent đọc `.skills/analytics-design/*`
- Khi tạo `blueprints/` → agent đọc `.skills/metabase-automation/*` + Design Spec + domain files
- Metabase Automation **đọc** từ `domains/` và `designs/` để inform blueprint creation, nhưng **không sửa** nội dung analyst artifacts
- Cross-references giữa artifacts dùng relative links (`../domains/sales.md#net-revenue`)

---

## XII. Tác động đến commands hiện tại

| Command | Thay đổi |
|---------|---------|
| `/create-metabase-blueprint` | Agent chạy đầy đủ pipeline: Phase 0-6 (analytics-design) → Phase 7-10 (metabase-automation). Internally tạo/cập nhật domain, playbook, design spec TRƯỚC KHI tạo blueprint. |
| `/deploy-metabase-blueprint` | Không đổi — vẫn chỉ deploy blueprint có sẵn |
| `/capture-metabase-dashboard` | Có thể enhance: capture ngược lại thành design spec + blueprint |
| `/design-dashboard` **(MỚI)** | Chỉ chạy Phase 0-6 (analytics-design) → output domain + playbook + design spec. Chưa implement. Dùng khi muốn review design trước, hoặc khi target tool không phải Metabase. |

---

## XIII. Deliverables cho bước triển khai

### Skill 1: Analytics Design (MỚI — 6 knowledge docs + 4 templates)

| File | Nội dung | Ước lượng |
|------|---------|-----------|
| `SKILL.md` | Tổng quan, quy trình Phase 0→6, khi nào đọc file nào, artifact ownership, iteration workflows | ~150 dòng |
| `DOMAIN_MODELING.md` | Cách định nghĩa domains: metric naming conventions, formula patterns, dbt model references, khi nào tách domain mới, quy tắc không duplicate | ~150 dòng |
| `VISUALIZATION_VOCABULARY.md` | 25 viz types + 1 composition concept (`view-group`) × (comm strength, data shape, best for, avoid when) | ~300 dòng |
| `COMPOSITION_PATTERNS.md` | Archetypes, card roles, narrative flow, view grouping, filter design, spatial grouping, Design Brief template | ~250 dòng |
| `VISUAL_LANGUAGE.md` | Color semantics (status/hierarchy/series/conditional), size semantics (text/card), quy tắc sử dụng | ~200 dòng |
| `COMPARATIVE_FRAMING.md` | 4 loại so sánh, bảng quyết định, mandatory rules | ~100 dòng |
| `templates/domain_template.md` | Cấu trúc chuẩn cho domain file | ~40 dòng |
| `templates/playbook_template.md` | Cấu trúc chuẩn cho playbook file | ~40 dòng |
| `templates/guide_template.md` | Cấu trúc chuẩn cho guide file | ~30 dòng |
| `templates/design_spec_template.md` | Format chuẩn cho Design Spec (Brief + Filters + Views + Composition table với Color & Size columns) | ~70 dòng |

### Skill 2: Metabase Automation (REFACTOR — 3 thay đổi)

| File | Thay đổi |
|------|---------|
| `STRATEGY.md` | **Refactor chi tiết — xem bảng split bên dưới** |
| `METABASE_VIZ_CATALOG.md` **(MỚI)** | 25 viz types + `view-group` × (Metabase display type, available settings, JSON template, limitations, sizing) + color token → hex mapping + size token → grid mapping. Đây là bảng translation hoàn chỉnh. |
| `capture_dashboard.js` **(ENHANCE)** | Thêm reverse translation: capture → design spec (ngoài blueprint). Hỗ trợ migration. |

**STRATEGY.md split chi tiết**:

| Section hiện tại (heading trong file) | Hành động | Đích |
|---------------------------------------|----------|------|
| `## 1. Dashboard Archetypes (Architecture)` | **MOVE** | → `analytics-design/COMPOSITION_PATTERNS.md` |
| `## 2. Visualization Heuristics (Design Thinking)` | **MOVE + REPLACE** | → `analytics-design/VISUALIZATION_VOCABULARY.md` (thay thế bằng full vocabulary) |
| `## 3. Semantic Layer Strategy (Data Modeling)` | **KEEP** | Giữ nguyên trong `STRATEGY.md` — đây là Metabase-specific |
| `## 4. Automation Workflow` | **REFACTOR** | Giữ bước classify + model trong STRATEGY.md. Link đến analytics-design cho bước visualize. |

**Thêm vào STRATEGY.md sau refactor**:
- Link rõ ràng: "Trước khi tạo blueprint, đọc `.skills/analytics-design/SKILL.md` để chạy Phase 0-6"
- Mapping table reference: "Tra cứu `METABASE_VIZ_CATALOG.md` cho translation"

### Project-level updates

| File | Thay đổi |
|------|---------|
| `CLAUDE.md` | Thêm entry cho `.skills/analytics-design/` trong Key References và Deployment Commands. Thêm `/design-dashboard` vào bảng Commands. |
| `AGENTS.md` | Thêm section: (1) Mô tả analytics-design skill — vai trò, artifacts sở hữu, knowledge docs; (2) Collaboration flow giữa 2 skills — Agent Orchestration rules (đọc doc nào ở phase nào); (3) Cập nhật pipeline diagram hiện tại để phản ánh 2-skill architecture. |
| `.claude/commands/design-dashboard.md` **(MỚI)** | Command prompt: "Read `.skills/analytics-design/SKILL.md`. Execute Phase 0-6. Output: domain, playbook, design spec. Do NOT read metabase-automation docs." |
| `.claude/commands/create-metabase-blueprint.md` **(CẬP NHẬT)** | Thêm 2-step orchestration: "Step 1: Read analytics-design, execute Phase 0-6. Step 2: Read metabase-automation, execute Phase 7-10." (xem Agent Orchestration, Section VII). |

### Analytics-handbook

| Thay đổi | Chi tiết |
|---------|---------|
| Tạo `docs/analytics-handbook/designs/` | Thư mục cho Design Spec artifacts |
| Ownership clarification | `domains/`, `playbooks/`, `guides/`, `designs/` → owned by analytics-design. `blueprints/` → owned by metabase-automation. |

---

## XIV. Iteration, Update & Migration

### Iteration workflows

Ngoài tạo mới, pipeline cần hỗ trợ 3 flow cập nhật:

**Flow A: Thêm metric vào dashboard có sẵn**

```
User: "Thêm Discount Rate vào CEO Weekly Pulse"
  │
  ├── Phase 0: Cập nhật domain (nếu metric chưa có)
  ├── Phase 4-6: Cập nhật design spec — thêm card mới vào composition table
  │     → Gán role, viz type, color, size cho card mới
  │     → Kiểm tra narrative flow có cần điều chỉnh không
  ├── Phase 7-9: Cập nhật blueprint — thêm question + metabase-viz/pos
  └── Phase 10: Re-deploy
```

**Flow B: Redesign dashboard cũ (cải thiện visualization)**

```
User: "Cải thiện CEO Weekly Pulse cho đẹp/impactful hơn"
  │
  ├── Phase 3-6: Tạo MỚI hoặc cập nhật design spec
  │     → Giữ nguyên metrics, redesign composition + viz types
  │     → Apply full decision tree (Phase 5) cho từng card
  ├── Phase 7-9: Viết LẠI blueprint từ design spec mới
  └── Phase 10: Re-deploy
```

**Flow C: Hotfix blueprint trực tiếp (bypass design)**

```
User: "Fix lỗi SQL trong blueprint XYZ" hoặc sửa nhỏ
  │
  ├── Sửa trực tiếp blueprint (Phase 9 only)
  ├── Deploy (Phase 10)
  └── Đánh dấu design spec là STALE (nếu có)
      → Thêm note vào design spec: "⚠️ Blueprint modified directly on [date]. Design spec may be out of sync."
```

**Quy tắc sync**:
- Design spec là **source of intent**, blueprint là **source of implementation**
- Khi 2 cái out-of-sync, blueprint wins (nó là cái đang deployed)
- Để re-sync: chạy `/capture-metabase-dashboard` → tạo lại design spec từ blueprint hiện tại
- **Staleness detection**: Phase 10 pre-deploy check tự động phát hiện khi blueprint mới hơn design spec (xem Phase 10)

### Reverse flow: Capture → Design Spec

`/capture-metabase-dashboard` hiện tại capture dashboard → blueprint. Enhance để cũng tạo design spec:

```
Live Dashboard
  → capture_dashboard.js (có sẵn)
  → Blueprint (Metabase-specific)
  → Reverse Translation (Phase 7 ngược)
      → Metabase display types → standard vocab
      → Hex colors → semantic tokens
      → Grid sizes → size tokens
  → Design Spec (tool-agnostic)
```

**Lưu ý: Reverse translation inherently lossy.** Có thể reverse viz types, colors, sizes (structural), nhưng **không thể suy ra** card roles, communication goals, narrative flow, hay business rationale từ JSON. Design spec reverse-generated sẽ có cấu trúc đúng nhưng thiếu semantic layer — cần analyst review để bổ sung roles, intent, và narrative.

**Reverse disambiguation rules** — nhiều standard terms map sang cùng 1 Metabase type. Reverse mapper kiểm tra settings để phân biệt:

| Metabase `display` | Check | Standard Term |
|--------------------|---------|----|
| `bar` | `stackable.stack_type: "stacked"` + time x-axis | `stacked-bar-time` |
| `bar` | `stackable.stack_type: "stacked"` + categorical x-axis | `stacked-bar` |
| `bar` | `stackable.stack_type: null` + `graph.dimensions` grouped | `grouped-bar` |
| `bar` | default (none of above) | `vertical-bar` |
| `area` | `stackable.stack_type: "stacked"` | `stacked-area` |
| `area` | default | `area-chart` |
| `line` | ≥2 series | `multi-line-chart` |
| `line` | 1 series | `line-chart` |
| `scalar` | has `scalar.comparisons` | `single-value-with-trend` |
| `scalar` | no comparisons | `single-value` |
| `table` | has `table.column_formatting` | `data-table-formatted` |
| `table` | default | `data-table` |
| `pivot` | has `table.column_formatting` (conditional formatting as intensity encoding) | `heatmap` |
| `pivot` | default (no conditional formatting, or formatting for alerts only) | `pivot-table` |
| `pie` | — | `donut` |
| text dashcard | — | `text-annotation` |
| dashboard tab | — | `view-group` |

**Guardrail**: Reverse-generated design specs PHẢI có frontmatter `status: draft-from-capture` để phân biệt với analyst-authored specs (`status: final`). Agent không được dùng `draft-from-capture` spec làm source-of-truth cho redesign mà không qua analyst review trước.

Điều này cho phép:
- Tạo design specs cho ~12 blueprints hiện tại (migration) — cần analyst review sau
- Capture bất kỳ dashboard nào đã tạo bằng UI → đưa vào pipeline

### Migration path cho blueprints hiện tại

12 blueprints đã tồn tại **không có design specs**. Chiến lược migration:

| Approach | Effort | Khi nào |
|----------|--------|---------|
| **Lazy migration** | Thấp | Chỉ tạo design spec khi blueprint cần UPDATE lần tới. Blueprints cũ tiếp tục hoạt động không cần design spec. |
| **Batch migration** | Cao | Chạy reverse flow cho tất cả 12 blueprints. Tạo đầy đủ design specs. Dùng khi muốn standardize toàn bộ. |
| **Hybrid** | Trung bình | Ưu tiên blueprints quan trọng nhất (CEO, Daily Sales) → tạo design spec + redesign. Còn lại lazy. |

**Khuyến nghị**: **Hybrid** — redesign 2-3 blueprints quan trọng nhất làm pilot, chứng minh value, rồi mở rộng.

---

## XV. End-to-end example: Design Spec → Blueprint (3 cards)

Dưới đây là 3 cards từ canonical Design Spec (Section IV) được dịch sang Blueprint format, minh họa toàn bộ translation flow.

### Design Spec (input — tool-agnostic)

| # | Row | Card | Role | Viz Type | Color | Size | Comparison |
|---|-----|------|------|----------|-------|------|------------|
| 2 | B | Revenue vs Target | hero | gauge | positive/warning/negative (zones) | one-third × medium | vs monthly target, 3 zones |
| 3 | B | Net Revenue | supporting | single-value-with-trend | primary, trend: positive/negative | one-quarter × short | vs previous week |
| 9 | F | Revenue by Channel | breakdown | horizontal-bar | series-1..3 | half × medium | WoW% per category |

### Blueprint (output — Metabase-specific)

**Card 2: Revenue vs Target** (hero → gauge)

````markdown
### Revenue vs Target

```sql
SELECT
  ROUND(
    SUM(net_revenue) * 100.0
    / NULLIF((SELECT monthly_target FROM targets WHERE month = DATE_TRUNC('month', CURRENT_DATE)), 0)
  , 1) AS achievement_pct
FROM fact_orders
WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE)
  AND channel_category != 'US'
```

```json metabase-viz
{
  "display": "gauge",
  "visualization_settings": {
    "gauge.segments": [
      { "min": 0, "max": 40, "color": "#EF8C8C", "label": "Behind" },
      { "min": 40, "max": 70, "color": "#F9D45C", "label": "On Track" },
      { "min": 70, "max": 100, "color": "#84BB4C", "label": "Ahead" }
    ]
  }
}
```

```json metabase-pos
{ "size_x": 6, "size_y": 6 }
```
````

Translation notes:
- `gauge` → Metabase `gauge` (native)
- **Gauge cần trả về 1 giá trị duy nhất** — SQL tính `achievement_pct` (0-100) thay vì trả 2 columns (revenue + target). Segments dùng percentage scale tương ứng.
- `positive/warning/negative` zones → `gauge.segments` với 3 hex colors
- `one-third` → `size_x: 6`, `medium` → `size_y: 6`

**Card 3: Net Revenue** (supporting → scalar + trend)

````markdown
### Net Revenue

```sql
WITH this_week AS (
  SELECT SUM(net_revenue) AS revenue
  FROM fact_orders
  WHERE order_date >= DATE_TRUNC('week', CURRENT_DATE)
    AND channel_category != 'US'
),
last_week AS (
  SELECT SUM(net_revenue) AS revenue
  FROM fact_orders
  WHERE order_date >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '7 days'
    AND order_date < DATE_TRUNC('week', CURRENT_DATE)
    AND channel_category != 'US'
)
SELECT
  t.revenue AS net_revenue,
  l.revenue AS prev_week_revenue
FROM this_week t, last_week l
```

```json metabase-viz
{
  "display": "scalar",
  "visualization_settings": {
    "scalar.comparisons": [
      {
        "id": "prev_week",
        "type": "anotherColumn",
        "column": "prev_week_revenue",
        "label": "vs last week"
      }
    ],
    "column_settings": {
      "net_revenue": {
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
{ "size_x": 4, "size_y": 3 }
```
````

Translation notes:
- `single-value-with-trend` → Metabase `scalar` + `scalar.comparisons` (native)
- **⚠️ Native SQL queries không hỗ trợ `periodsAgo`** — phải tự tính previous period trong SQL và dùng `"type": "anotherColumn"` để reference column chứa giá trị so sánh
- `primary` color → không cần explicit hex cho scalar (Metabase auto-styles)
- `trend: positive/negative` → Metabase comparison auto-colors green/red
- `one-quarter` → `size_x: 4`, `short` → `size_y: 3`

**Card 9: Revenue by Channel** (breakdown → horizontal bar)

````markdown
### Revenue by Channel

```sql
WITH this_week AS (
  SELECT channel_category, SUM(net_revenue) AS revenue
  FROM fact_orders
  WHERE order_date >= DATE_TRUNC('week', CURRENT_DATE)
    AND channel_category != 'US'
  GROUP BY channel_category
),
last_week AS (
  SELECT channel_category, SUM(net_revenue) AS revenue
  FROM fact_orders
  WHERE order_date >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '7 days'
    AND order_date < DATE_TRUNC('week', CURRENT_DATE)
    AND channel_category != 'US'
  GROUP BY channel_category
)
SELECT
  t.channel_category,
  t.revenue,
  ROUND((t.revenue - l.revenue) / NULLIF(l.revenue, 0) * 100, 1) AS wow_pct
FROM this_week t
LEFT JOIN last_week l USING (channel_category)
ORDER BY t.revenue DESC
```

```json metabase-viz
{
  "display": "row",
  "visualization_settings": {
    "graph.dimensions": ["channel_category"],
    "graph.metrics": ["revenue"],
    "graph.colors": ["#509EE3", "#88BDE6", "#A989C5"],
    "graph.x_axis.title_text": "Revenue (₫)",
    "column_settings": {
      "revenue": {
        "number_style": "currency",
        "currency": "VND",
        "compact": true
      }
    }
  }
}
```

```json metabase-pos
{ "size_x": 9, "size_y": 6 }
```
````

Translation notes:
- `horizontal-bar` → Metabase `row` (native)
- `series-1..3` → `graph.colors: ["#509EE3", "#88BDE6", "#A989C5"]`
- `half` → `size_x: 9`, `medium` → `size_y: 6`

### Filter example: Dashboard có interactive filters

Ví dụ trên (CEO Weekly Pulse) không có interactive filters. Dưới đây minh họa filter flow cho Daily Operations dashboard:

**Design Spec (Constraints & Filters)**:

```markdown
### Constraints & Filters

**Business Constraints** — hardcode trong SQL:

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| Exclude US channel | `channel_category != 'US'` | All cards | Đơn nội bộ, 100% discount |

**Interactive Filters** — user tương tác trên dashboard:

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| Date Range | date/range | Last 7 days | All cards | Cho phép xem theo khoảng thời gian khác nhau |
| Channel | category/single-select | All | Cards 3, 5, 7 | Drill-down theo kênh bán hàng |
```

**Blueprint (filter wiring)**:

````markdown
### Parameters

```json metabase-parameters
[
  {
    "name": "Date Range",
    "slug": "date_range",
    "id": "date_range_param",
    "type": "date/range",
    "default": "past7days"
  },
  {
    "name": "Channel",
    "slug": "channel",
    "id": "channel_param",
    "type": "string/=",
    "default": null
  }
]
```

### Net Revenue (card có cả 2 filters)

```sql
SELECT SUM(net_revenue) AS net_revenue
FROM fact_orders
WHERE order_date >= DATE_TRUNC('week', CURRENT_DATE)
  AND channel_category != 'US'
  [[AND {{date_range}}]]
  [[AND channel_category = {{channel}}]]
```
````

Translation notes:
- `date/range` → Metabase `date/range` parameter type, SQL dùng `{{date_range}}` field filter
- `category/single-select` → Metabase `string/=`, SQL dùng `{{channel}}` template tag
- `[[...]]` = Metabase optional clause syntax — khi filter trống, clause bị bỏ qua
- `parameter_mappings` trong mỗi dashcard wires parameter → card's template tag

---

## XVI. Lợi ích dài hạn

| Concern | Hiện tại (1 skill gộp) | Đề xuất (2 skills tách) |
|---------|----------------------|------------------------|
| **Đổi BI tool** | Viết lại toàn bộ skill, mất domain/playbook knowledge | Chỉ viết lại metabase-automation; analytics-design + toàn bộ handbook (trừ blueprints) giữ nguyên |
| **Knowledge compounding** | Design knowledge bị ẩn trong Metabase context | Domains, playbooks, guides tích lũy độc lập — càng tạo nhiều dashboard càng giàu knowledge |
| **Agent reasoning** | Trộn lẫn "nghĩ gì" với "làm thế nào" | Mindset rõ ràng: Phase 0-6 = analyst suy nghĩ, Phase 7-10 = engineer triển khai |
| **Review workflow** | Chỉ review được sau khi implement | Domain → Playbook → Design Spec → mỗi bước đều có thể review trước khi tiếp tục |
| **Reuse** | Analytics knowledge bị khóa trong "metabase skill" | Domains, playbooks, guides dùng cho mọi output: dashboard, report, slide, email |
| **Artifact ownership** | Không rõ ai tạo/sửa file nào | Ranh giới rõ ràng: analytics-design owns 4 thư mục, metabase-automation owns 1 thư mục |
| **Onboarding** | Phải hiểu cả analytics + Metabase | Analyst đọc analytics-design, engineer đọc metabase-automation |

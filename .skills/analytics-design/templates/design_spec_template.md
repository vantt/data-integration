---
title: [Dashboard Title]
archetype: [Executive Pulse / Operational Cockpit / Exploratory Tool]
status: [final / draft / draft-from-capture]
last_modified: YYYY-MM-DD
domain_refs: [domains/sales.md, domains/customer.md]
---

## Design Spec: [Dashboard Title]

### Brief

- **Audience:** [Ai đọc, role gì, context đọc]
- **Time budget:** [Bao lâu để đọc — e.g., "5 phút, Monday morning"]
- **Primary question:** [Câu hỏi chính dashboard trả lời]
- **Decision enabled:** [Quyết định gì được kích hoạt]
- **Comparison frame:** [So sánh với gì — WoW, MoM, vs Target]
- **Archetype:** [Executive Pulse / Operational Cockpit / Exploratory Tool]
- **Domain references:** [domains/sales.md](../domains/sales.md), [domains/customer.md](../domains/customer.md)

### Constraints & Filters

**Business Constraints** — luôn áp dụng, hardcode trong SQL, user không tương tác:

| Constraint | Rule | Applies to | Rationale |
|------------|------|------------|-----------|
| [e.g., Exclude US channel] | [e.g., `channel_category != 'US'`] | [All cards / specific cards] | [Lý do] |

**Interactive Filters** — user có thể thay đổi trên dashboard:

| Filter | Type | Default | Applies to | Rationale |
|--------|------|---------|------------|-----------|
| [e.g., Date Range] | [date/range] | [Last 7 days] | [All cards] | [Lý do] |
| *(Nếu không có filter: ghi "Không có — [Archetype] cần zero-interaction")* | | | | |

### Views

[Single view (≤10 cards) / Multi-view: View 1 Name, View 2 Name, ...]

### Composition

| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "[Section Heading Text]" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 2 | B | [Card Name] | hero | [standard-viz-term] | [color tokens] | [width × height, text-size] | [Truyền tải thông điệp gì] | [vs what] |
| 3 | B | [Card Name] | supporting | [standard-viz-term] | [color tokens] | [width × height, text-size] | [Thông điệp] | [vs what] |
| 4 | C | "[Section Heading Text]" | annotation | text-annotation | structural | full-width × minimal | Section heading | — |
| 5 | D | [Card Name] | trend | [standard-viz-term] | [color tokens] | [width × height] | [Thông điệp] | [implicit/explicit] |

### Action Map

> Mỗi card có signal quan trọng PHẢI có recommended action. Tham chiếu Action Triggers trong playbook.

| Card | Signal | Condition | Recommended Action |
|------|--------|-----------|-------------------|
| [Card Name] | [e.g., Drop] | [e.g., WoW < -10%] | [e.g., Check breakdown by channel/product] |
| [Card Name] | [e.g., Spike] | [e.g., WoW > +30%] | [e.g., Verify no duplicates, check promo impact] |

<!--
Composition Table Rules:
- Row column: same letter = same horizontal row. Total width per row = full-width.
- Viz Type: use ONLY standard vocabulary terms (see VISUALIZATION_VOCABULARY.md)
- Color: use ONLY semantic tokens (see VISUAL_LANGUAGE.md) — NO hex codes
- Size: use ONLY size tokens (see VISUAL_LANGUAGE.md) — NO pixel values
- Valid width combos on 18-col grid:
    one-third + 3×one-quarter (6+4+4+4=18)
    half + half (9+9=18)
    one-third + two-thirds (6+12=18)
    6×one-sixth (3×6=18)
    Do NOT use 4×one-quarter (4×4=16 ≠ 18)
- Status values: final (analyst-authored), draft (work-in-progress), draft-from-capture (reverse-generated)
-->

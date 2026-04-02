---
name: Analytics Design (Tool-Agnostic)
description: Analyst brain — NGHĨ, ĐỊNH NGHĨA, và THIẾT KẾ analytics artifacts. Không phụ thuộc vào bất kỳ BI tool nào.
---

# Analytics Design Skill

> **Location**: `.skills/analytics-design/` — tool-agnostic analyst knowledge.
> Đây là "analyst brain" — sở hữu và tạo ra toàn bộ analytics artifacts trừ blueprints.
> Blueprints thuộc về `.skills/metabase-automation/` (engineer brain).

## Overview

Skill này cung cấp knowledge framework cho các quyết định analytics & design:
- **WHAT** to measure (domain modeling, metric definitions)
- **WHY** this dashboard exists (audience, purpose, playbooks)
- **HOW to communicate** data (visualization selection, composition, visual language)

Skill này **KHÔNG BIẾT** gì về Metabase, Superset, Looker, hay bất kỳ BI tool cụ thể nào. Mọi output đều dùng **standard vocabulary** (xem `VISUALIZATION_VOCABULARY.md`).

## Knowledge Documents

Đọc theo thứ tự phase đang thực hiện:

| Phase | Document | Mục đích |
|-------|----------|----------|
| Phase 0 | `DOMAIN_MODELING.md` | Cách định nghĩa metrics, domains, formulas |
| Phase 3-4 | `COMPOSITION_PATTERNS.md` | Archetypes, card roles, narrative flow, filter design |
| Phase 5 | `VISUALIZATION_VOCABULARY.md` | 25 viz types + decision tree |
| Phase 5-6 | `VISUAL_LANGUAGE.md` | Design principles, color & size semantic tokens, visual polish checklist |
| Phase 6 | `COMPARATIVE_FRAMING.md` | Quy tắc so sánh, ngữ cảnh hóa KPI |

**Quy tắc**: Chỉ đọc document cần thiết cho phase hiện tại. KHÔNG đọc `.skills/metabase-automation/*` trong Phase 0-6 (trừ khi cần kiểm tra tool feasibility — xem Exception bên dưới).

## Templates

| Template | Dùng cho |
|----------|----------|
| `templates/domain_template.md` | Tạo mới domain file |
| `templates/playbook_template.md` | Tạo mới playbook file |
| `templates/guide_template.md` | Tạo mới guide file |
| `templates/design_spec_template.md` | Tạo mới Design Spec (contract giữa 2 skills) |

## Artifact Ownership

| Artifact | Location | Created by | When |
|----------|----------|-----------|------|
| Domain | `docs/analytics-handbook/domains/` | Analytics Design (Phase 0) | Tạo mới khi metric chưa tồn tại; cập nhật khi thêm metric |
| Playbook | `docs/analytics-handbook/playbooks/` | Analytics Design (Phase 1) | Tạo mới cho mỗi dashboard; cập nhật khi đổi audience/purpose |
| Guide | `docs/analytics-handbook/guides/` | Analytics Design (Phase 2) | Chỉ khi có concept phức tạp cần giải thích riêng |
| Design Spec | `docs/analytics-handbook/designs/` | Analytics Design (Phase 3-6) | Tạo mới cho mỗi dashboard design |
| Blueprint | `docs/analytics-handbook/blueprints/` | **Metabase Automation** (Phase 7-10) | Không thuộc skill này |

**Thứ tự tạo artifact (bắt buộc)**:
```
domain → playbook → [guide] → design spec → blueprint → deploy
```

Mỗi artifact downstream **tham chiếu** artifact upstream:
- Playbook tham chiếu domain ("`xem domains/sales.md cho định nghĩa Net Revenue`")
- Design spec tham chiếu playbook + domain
- Blueprint tham chiếu design spec + domain

## Phase 0-6 Process

### Phase 0 — Domain Modeling

**Input**: User request — xác định domain nào cần.

1. Kiểm tra domain đã tồn tại? → Quét `docs/analytics-handbook/domains/`
2. Nếu đã có → Đọc file, kiểm tra metrics cần thiết. Thiếu → cập nhật thêm.
3. Nếu chưa có → Tạo mới theo `templates/domain_template.md`
4. Đọc `DOMAIN_MODELING.md` cho conventions và quy tắc.

**Output**: `docs/analytics-handbook/domains/<domain>.md`

### Phase 1 — Playbook Creation

**Input**: Domain knowledge + user request (audience, mục đích).

1. Kiểm tra playbook đã tồn tại? → Quét `docs/analytics-handbook/playbooks/`
2. Nếu đã có → Đọc, cập nhật nếu audience/purpose thay đổi
3. Nếu chưa có → Tạo mới theo `templates/playbook_template.md`
4. **Action Triggers table là BẮT BUỘC.** Mỗi metric chính phải có ít nhất 1 threshold + owner + action.
5. **Reading Flow là BẮT BUỘC.** Mô tả đường đi từ hero card → investigation → escalation.

**Output**: `docs/analytics-handbook/playbooks/<name>.md`

### Phase 2 — Guide Creation (conditional)

**Input**: Domain + playbook — có concept phức tạp cần giải thích riêng không?

- Ví dụ cần guide: Health Score composite, revenue terminology, cohort analysis
- Nếu không có concept mới → **Bỏ qua**, chuyển sang Phase 3

**Output**: `docs/analytics-handbook/guides/<topic>.md` — hoặc bỏ qua.

### Phase 3 — Design Brief

**Input**: User request + domain + playbook.

Xác định: Audience, Purpose, Hero Metric, Comparison Frame, Time Budget, Archetype. Xem `COMPOSITION_PATTERNS.md` cho Design Brief fields.

### Phase 4 — Composition Design

**Input**: Metrics (Phase 0) + Brief (Phase 3). Đọc `COMPOSITION_PATTERNS.md`.

- 4a: Card Role Assignment (hero/supporting/trend/breakdown/detail/annotation)
- 4b: Narrative Flow (arc kể chuyện)
- 4c: Spatial Grouping (relative sizing)
- 4d: View Grouping (single vs multi-view)
- 4e: Constraints & Filter Design (business constraints + interactive filters)
- 4f: Companion Card Identification (text cards, comparisons)

### Phase 5 — Visualization Selection

**Input**: Each card from Phase 4. Đọc `VISUALIZATION_VOCABULARY.md`.

Chọn viz type bằng **standard vocabulary** dựa trên: `Card Role × Data Shape × Communication Goal`.

Dùng decision tree trong `VISUALIZATION_VOCABULARY.md`. Anti-pattern check bắt buộc.

### Phase 6 — Enrichment Check

**Input**: Card + viz type. Đọc `COMPARATIVE_FRAMING.md` + `VISUAL_LANGUAGE.md`.

- 6a: Comparative Framing — mọi KPI cần ≥1 so sánh
- 6b: Data Completeness cho viz type đã chọn
- 6c: Narrative Support — viết annotation content theo templates trong `COMPOSITION_PATTERNS.md` Section 8
- 6d: **Action Map** — điền bảng Action Map cho mỗi card có signal quan trọng (xem `templates/design_spec_template.md`)
- 6e: **Dashboard Finish Checklist** — chạy full checklist trong `VISUAL_LANGUAGE.md` Section 10 trước khi finalize

**Output**: Design Spec → lưu tại `docs/analytics-handbook/designs/<name>.md`

## Fast-Track Rules

Không phải mọi dashboard đều cần 7 phases đầy đủ:

| Điều kiện | Phase bỏ qua |
|-----------|-------------|
| Domain đã tồn tại, đầy đủ metrics | Phase 0 (skip — chỉ verify) |
| Playbook đã tồn tại | Phase 1 (skip — chỉ verify) |
| Không có concept phức tạp mới | Phase 2 (mặc định skip) |
| Dashboard ≤5 cards, single view, 1 archetype rõ | Phase 3-6 collapse thành 1 bước |

**Full path** (7 phases): Dashboard mới, domain mới, >5 cards, hoặc multi-view.
**Fast-track** (3-5 phases): Domain + playbook sẵn có, ≤5 cards → skip Phase 0-2, collapse Phase 3-6.
**Khi nghi ngờ → dùng full path.**

## Iteration Workflows

**Flow A — Thêm metric vào dashboard có sẵn**:
Phase 0 (update domain nếu cần) → Phase 4-6 (update design spec: thêm card, gán role/viz/color/size) → chuyển cho engineer Phase 7-10.

**Flow B — Redesign dashboard cũ**:
Phase 3-6 (tạo MỚI hoặc update design spec, giữ metrics, redesign composition + viz) → chuyển cho engineer Phase 7-10.

**Flow C — Hotfix blueprint trực tiếp** (bypass design):
Sửa trực tiếp blueprint (Phase 9 only) → Deploy → Đánh dấu design spec là STALE.

## Failure Modes

| Phase | Failure | Xử lý |
|-------|---------|-------|
| Phase 0 | Metric cần nhưng dbt model chưa tồn tại | Ghi metric vào domain với `status: planned`. Tiếp tục design. |
| Phase 0 | Không xác định được domain (request mơ hồ) | Dừng, hỏi user clarify. |
| Phase 5 | Không tìm được viz type phù hợp | Dùng `data-table` làm safe fallback. Ghi note "needs better viz". |
| Phase 6 | KPI không có comparison khả thi | Chấp nhận `single-value` không trend. Ghi note. |

## Tool Feasibility Exception

Trong Phase 5, nếu cần kiểm tra "BI tool có hỗ trợ viz type này không?", agent có thể scan cột **Metabase Support** trong bảng vocabulary (`VISUALIZATION_VOCABULARY.md`) mà **KHÔNG cần** đọc full `METABASE_VIZ_CATALOG.md`.

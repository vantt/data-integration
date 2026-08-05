# ui-spec wireframe upgrade — content model implementation report

**Date:** 2026-07-13 · **Plan:** `plans/260713-1912-ui-spec-wireframe-content-model/` · **Status:** DONE

## Problem

Layout tab của wireframe-v2 là annotated region map, không phải wireframe: 1 dòng text/region, không phân biệt loại element, không repetition, không tỷ lệ dọc, không viewport frame. Root cause: schema `ui-layout` chỉ có geometry + `samples` 1 dòng.

## What shipped

**Phase 0 — single-writer schema (chống drift, theo yêu cầu user):**
- NEW `tools/wireframe/layout-schema.mjs` — dependency-free; owns `LAYOUT_KEYS`, `CONTENT_TYPES` (15 primitives), `contentElementType/walkContent/contentActionRefs/flattenContentLine`. Node tools import; `html-shell.mjs` inline export-stripped vào browser bundle (regex `^export (const|function)`), có test guard contract (import-free, top-level-export-only, eval được trong bare scope).
- `extract-layout.mjs` KNOWN_KEYS ← LAYOUT_KEYS.

**Phase 1 — proportion + viewport:**
- `row_heights:` (1 CSS track/base row) → `grid-template-rows`; variant rows = auto; warn `VR-LAYOUT-ROWS`.
- `.viewport-frame` theo type/platforms: desktop 1280 / mobile 390 / modal 560 / overlay 420 px + label; relax card cap 900→1560px cho surface có grid (`:has(.grid-with-inspector)`).

**Phase 2 — `content:` model + S14 pilot:**
- Schema: `content: {region: element[]}`; element = `{type: value, ...opts}`; opts `action:`, `primary:`, `active:`. Primitives: h, text, btn, input, select, checklist, chips, badge, tabs, table, list, kpi, divider, slot, row.
- NEW `client/render-content.js` + `styles-content.mjs`; `gridCellHtml` ưu tiên content, fallback samples (53 surface còn lại không đổi).
- Actionable element mang `data-action-id` trực tiếp → Contract Inspector hover/click hoạt động không cần `elements:` map; `buildInspectorChip` nhận actionIdOverride (fix verify-runtime FAIL duy nhất gặp phải).
- ASCII blueprint: region có content flatten 1 dòng qua `flattenContentLine` (deterministic).
- Validator: content keys vào VR-LAYOUT-UNKNOWN; warn mới VR-CONTENT-TYPE / VR-CONTENT-ACTION.
- chip-audit: content region audit theo TYPE (btn/tabs thiếu action = unmapped; badge/chips exempt); samples path skip region đã có content.
- S14 migrate toàn bộ 14 region sang content + row_heights; xóa samples/elements (single source).
- Docs: `ui-layout-authoring.md` (§2 row_heights+content, §2b primitive table, §5 rules, §10 quick-ref, §12 audit, single-writer note) + `SKILL.md`.

## Verification

- Unit: layout-schema 8/8, extract-layout 11/11, generate-ascii 33/33, chip-audit 9/9.
- `npm test` (validator fixture regression): 28/28 PASS.
- `verify-runtime` (jsdom, 54 surfaces, 6 flows): PASS, 0 errors.
- `validate` crm spec: 0 errors 0 warnings; `build` idempotent.
- Visual QA (screenshot 1920×2100 + vision): S14 đạt — button/badge/tabs/input/checklist/kpi/list-skeleton phân biệt rõ, talk_track chiếm ưu thế dọc, frame desktop·1280px, diacritics sạch; S03 (samples+children fallback) và M01 (modal 560px) không regression.
- chip-audit S14 sau migrate: 3 unmapped hợp lệ (⋯ Ghi thủ công, ☑ Zalo, 💬 Zalo — chưa có interaction trong contract).

## Files touched

Skill: `layout-schema.mjs`* `layout-schema.test.mjs`* `render-content.js`* `styles-content.mjs`* (new); `extract-layout.mjs` `html-shell.mjs` `render-grid.js` `generate-ascii.mjs` `chip-audit.mjs` `styles.mjs` `styles-phase6.mjs` `validate.mjs` `SKILL.md` `ui-layout-authoring.md` (modified). Spec: `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` (+ ASCII regenerated).

## Unresolved questions

1. S14 có 3 chip unmapped hợp lệ vì nút chưa có interaction trong contract (`⋯ Ghi thủ công`, `☑ Zalo` strip, `💬 Zalo` identity) — cần bổ sung interaction hay chấp nhận display-only?
2. Migrate content: cho các surface còn lại (S01/S03/S02, modals) — làm đợt sau theo giá trị review, chưa lên lịch.
3. Chưa commit — spec S14 + P01 có sửa đổi uncommitted từ trước của user trên cùng file.

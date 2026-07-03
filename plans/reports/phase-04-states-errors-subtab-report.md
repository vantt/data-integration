# Phase 04 — States / Errors Subtab — Implementation Report

**Date:** 2026-07-02  
**Branch:** feature/task-detail-cockpit-backend  
**Result:** PASS — all verify-runtime sections A–H clean, zero errors

---

## What was done

### New files

| File | Purpose |
|---|---|
| `.agents/skills/ui-spec/tools/wireframe/extract-states.mjs` | `extractStates(prose)` parses `## States` section from surface prose; `readErrCatalog(specRoot)` reads `30-states-and-errors.md` → ERR-* id→description map |
| `.agents/skills/ui-spec/tools/wireframe/styles-phase4.mjs` | CSS: `.state-card`, `.state-id` (soft blue pill), `.state-label`, `.state-desc`, `.err-chip.known` (blue), `.err-chip.unknown` (orange), `.states-empty` |
| `.agents/skills/ui-spec/tools/wireframe/client/render-states.js` | `renderStates(surface)` → HTML string for `#view-states`; inlines ERR chips with tooltip from global `ERR_CATALOG` |

### Modified files

| File | Change |
|---|---|
| `tools/wireframe/styles.mjs` | Import + concat `CSS4` |
| `tools/interpret-wireframe.mjs` | Import `extractStates`, `readErrCatalog`; `buildSurfaceData()` now returns `{ surfaces, errCatalog }`; each surface gains `states: [{id, label, description, errRefs}]`; passes `{ errCatalog }` to `buildHtml` |
| `tools/wireframe/html-shell.mjs` | `buildHtml(surfaces, { errCatalog })` sig; injects `const ERR_CATALOG = {...}` before `SURFACES`; adds States subtab `<button class="subtab" data-view="states">`; adds `<div id="view-states" style="display:none">`; adds `render-states.js` to inline file list |
| `tools/wireframe/client/app-chrome.js` | `switchView` view loop now includes `"states"`; `isSurfaceView` extended to `["layout","blueprint","states"].includes(view)` → Surface top-tab stays highlighted + subtab bar remains visible |
| `tools/wireframe/client/app.js` | `renderMain()` calls `document.getElementById("view-states").innerHTML = renderStates(s)` |
| `tools/wireframe/verify-runtime.mjs` | Section H added (H1: S14 shows ≥1 state card; H2: ERR chip found in ≥1 surface; H3: no crash across all 54 surfaces) |

---

## Verification output (abridged)

```
Section H: States subtab …
  H1 S14 States subtab: 6 state card(s) -- OK
  H2 ERR chip badge found in at least one surface's States view -- OK
  H3 States subtab: no crash across 54 surfaces -- OK

RESULT: PASS -- all assertions clean, zero runtime errors
========================================
Surfaces exercised : 54
Flows exercised    : 6
Errors             : 0
```

---

## Key data points

- **ERR_CATALOG**: 8 entries (`ERR-MERGE-CONSTRAINT`, `ERR-SEGMENT-RULE-INVALID`, `ERR-TASK-DUE-PAST`, `ERR-PHONE-FORMAT`, `ERR-DUPLICATE-IDENTITY`, `ERR-CACHE-READ-FAIL`, `ERR-CAMPAIGN-NO-SEGMENT`, `ERR-CONSENT-BLOCK`)
- **S14 state cards**: 6 (`ST-CALL-NO-SCRIPT`, `ST-CALL-STOP`, `ST-CALL-LOW-CONFIDENCE`, `ST-CALL-NO-ACTIONS`, `ST-CALL-COLLECT-DONE`, `ST-CALL-CONSENT-WARN`)
- **ERR chip trigger**: `S04 / ST-DEDUP-CONFLICT` references `ERR-MERGE-CONSTRAINT` → blue chip with tooltip "Merge failed because moving an identity would violate UNIQUE..."
- Surfaces without `## States` section → "Chưa khai báo states cho màn hình này." empty-state paragraph

---

## Regex coverage notes

Two bullet formats coexist in the spec:
- `- ST-WORKLIST-EMPTY: text` (most surfaces)
- `- **ST-CALL-NO-SCRIPT**: text` (S14/S15 with bold markers)

The `ST_BULLET_RE = /^\s*[-*]\s+\*{0,2}(ST-...)\*{0,2}[:\s—–-]+(.+)/` handles both via `\*{0,2}`. Non-standard bullets like `- error: ERR-*` (some modals) are intentionally skipped (they lack `ST-` prefix) — their ERR refs are not surfaced in the States subtab.

---

## Unresolved questions

None.

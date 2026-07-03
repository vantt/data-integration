# Phase 06 — CSS Grid Renderer — Implementation Report

**Date:** 2026-07-02  
**Branch:** feature/task-detail-cockpit-backend  
**Spec root:** `crm/docs/ui-spec/` (54 surfaces, 311 actions)

## Result

`verify-runtime.mjs` → **PASS A–I** (0 errors, 54 surfaces, 6 flows)  
`extract-layout.test.mjs` → **9/9 passed** (no regression)

## Files changed

| File | Change |
|---|---|
| `tools/wireframe/client/render-regionbox.js` | Extracted `regionBoxHtml(surface, region, opts)` from `buildRegionBoxes`; `buildRegionBoxes` now delegates to it |
| `tools/wireframe/client/render-grid.js` | **NEW** — `cssIdent`, `rewireActionButtons`, `renderGrid`, `toggleFloating`, `switchGridVariant` |
| `tools/wireframe/client/app.js` | `renderMain` uses `rewireActionButtons` (DRY), populates `#view-grid`, shows/hides Layout subtab, calls `switchView("grid"/"layout")` |
| `tools/wireframe/client/app-chrome.js` | `switchView` list extended to include `"grid"`; `isSurfaceView` includes `"grid"` |
| `tools/wireframe/html-shell.mjs` | Added `render-grid.js` to inline file list; added `#subtab-grid` button + `#view-grid` div to HTML template |
| `tools/wireframe/styles-phase6.mjs` | **NEW** — grid container, cell, sample-content, floating-banner, variant-switcher CSS |
| `tools/wireframe/styles.mjs` | Imports and concatenates `CSS6` |
| `tools/wireframe/verify-runtime.mjs` | Added Section I (5 assertions: a–e) |

## Key design decisions

**`regionBoxHtml` extraction**: calls `groupByRegion(surface, [region])` per-region (slightly more calls than before, acceptable at this scale). `buildRegionBoxes` now loops over `regionOrder(surface)` and calls it — same output, same click-handler behavior.

**`rewireActionButtons(root)`**: defined in `render-grid.js` (loaded before `app.js`). Replaces the two inline `for` loops in `renderMain`. Also called after `switchGridVariant` re-renders the grid. References `handleInteraction` and `showToast` (function declarations in `app.js`) — hoisted within the single `<script>` block so available at call time.

**Variant onclick quoting**: `JSON.stringify(k)` would produce `"key"` (double quotes) inside an HTML double-quote attribute, breaking parsing. Fixed with `data-variant="${escAttr(k)}"` + `onclick="switchGridVariant(this.dataset.variant)"`. `switchGridVariant` coerces `""` → `null` for the default button.

**CSS ident sanitization**: `cssIdent(r)` replaces `[^a-zA-Z0-9_-]` with `_`. Applied consistently to both `grid-template-areas` rows and each cell's `style="grid-area:..."` + `data-region-ident` attribute. S14 region names (`reason_to_call`, `identity_bar`, etc.) are already safe — no collisions in practice.

**Floating region toggle**: `toggleFloating(btn)` uses `data-replaces` (comma-separated CSS idents) to find cells via `.grid-cell[data-region-ident="..."]` and sets `display:none`. Toggling again restores cells. Works in jsdom (onclick attribute handlers fire via `dispatchEvent`).

**View default switching**: `renderMain` now explicitly calls `switchView("grid")` for surfaces with `layout` and `switchView("layout")` otherwise. This resets the active tab on every navigation — consistent with spec intent (stakeholders always see the spatial view first).

**`children` sub-layouts**: S14 has none; no special handling needed. The normal `regionBoxHtml` call in the grid cell loop handles any region, with or without children.

## Section I assertions verified

| | Check | Result |
|---|---|---|
| (a) | S14 default = Layout tab; `grid-template-areas` contains `reason_to_call` | OK |
| (b) | Floating toggle shows `stop_banner` banner; replaced cell becomes `display:none` | OK |
| (c) | Variant switch to `full_screen` prepends topbar cell | OK |
| (d) | S01 (no layout): Layout tab hidden, Interactions is default | OK |
| (e) | No crash across all 54 surfaces | OK |

## Unresolved questions

None.

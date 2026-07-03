# Phase 06b — Grid Cell Visual Redesign Report

**Date:** 2026-07-02  
**Branch:** feature/task-detail-cockpit-backend

## Problem

Grid cells reused the full `regionBoxHtml` (Interactions-style: count badge, 2-line action buttons with trigger→action meta, listener chips, "(display only)" notes) crammed into small CSS grid cells. User rejected: "messy, everything crammed, looks like Interactions but worse."

## Changes

### `render-grid.js`

- Added `gridCellHtml(surface, region, sampleText)` — new dedicated cell renderer:
  - `gc-label`: 9px uppercase muted region name (no count badge)
  - `gc-sample`: 13px `#111827` dominant sample text, full wrap
  - `gc-pills`: wrapping row of small inline pills — element name only, full contract in title tooltip
  - Pills keep `class="action-btn"` + `data-action/data-target/data-id` so `rewireActionButtons` + `handleInteraction` wire correctly
  - Guard info in title only; listener chips omitted entirely
  - Empty region = just label + (optional) sample, no "(display only)" note
- `regionBoxHtml` (Interactions tab) left completely unchanged
- Grid cells in `renderGrid` now call `gridCellHtml` instead of `regionBoxHtml`
- Floating banners now call `gridCellHtml` wrapped in `.grid-cell.gc-floating` (red-tinted card)
- Grid container inline style: `gap:10px` → `gap:12px;grid-auto-rows:minmax(56px,auto)`

### `styles-phase6.mjs`

- `.grid-container`: added `padding:16px`, `max-width:1100px`, `margin:0 auto`, `background:#f1f5f9`, `border-radius:8px`
- `.grid-cell`: removed `overflow:hidden`, added `padding:10px 12px`, `min-height:56px`, `display:flex`, `flex-direction:column`, `gap:4px`
- Removed `.grid-cell > .region-box` CSS (no longer used)
- Added `.gc-label` (9px, uppercase, `#94a3b8`, `letter-spacing:.09em`)
- Added `.gc-sample` (13px, `#111827`, `line-height:1.45`, `flex:1`)
- Added `.gc-pills` (flex, wrap, `gap:4px`)
- Added `button.action-btn.gc-pill` override (compact pill: `padding:2px 8px`, `border-radius:9999px`, 10px monospace, `min-width:unset`, `transform:none`)
- Added `.gc-floating` (red tint: `background:#fff1f2`, `border-color:#fecaca`, `.gc-label` in `#ef4444`)

## Visual Self-Check Results

Screenshots saved to scratchpad:

| Surface | Screenshot |
|---------|-----------|
| S14 Call Mode / Strategy Cockpit | `scratchpad/s14-v1.png` |
| S03 Customer 360 Detail | `scratchpad/s03-v1.png` |
| M01 Merge Confirm Modal | `scratchpad/m01-v1.png` |

**Assessment after visual check (1 iteration, no further CSS fixes needed):**
- Spacing: airy — cells have breathing room, light gray container background separates cells visually
- Sample text: dominant — 13px dark text is the first thing the eye lands on
- Pills: small — inline rounded badges at 10px, not oversized action cards
- 2-column proportion: clearly visible on S14 (wide left / narrow right) and S03 (main_col / sidebar)
- Floating banner: red-tinted card matches warning intent; toggle still works

## Verification

```
node .agents/skills/ui-spec/tools/wireframe/verify-runtime.mjs --root crm/docs/ui-spec
```

```
Surfaces exercised : 54
Flows exercised    : 6
Errors             : 0

RESULT: PASS -- all assertions clean, zero runtime errors
```

All sections A-J passed with 0 errors. Section I selectors unchanged (`.grid-container`, `data-region-ident`, `.floating-toggle`, `.variant-btn` all kept).

## Addendum — Children Sub-Layout Rendering (2026-07-02, follow-up)

Human review approved S14/M01 but flagged S03: sidebar cell rendered only the
"(sidebar blocks stacked)" placeholder; `layout.children` was not rendered.

**Changes:**

- `render-grid.js`: added `gridChildSectionsHtml(surface, layout, region)` — renders
  `layout.children[region].areas` as stacked mini-sections inside the parent grid cell,
  reusing the `gridCellHtml` grammar (gc-label with dotted child name, gc-sample from
  `layout.samples[childName]`, gc-pills for the child's actions). Child area matrices are
  flattened to a vertical stack in first-appearance order; 1 level only, no recursion.
  Child regions also present in `layout.floating` (S03 `sidebar.warning`) are skipped —
  they stay floating-toggle-banner-only (no double render). Cell mapping in `renderGrid`
  appends child sections; JSDoc for `layout.children` updated.
- `styles-phase6.mjs`: added `.gc-children` (column stack, 8px gap) and `.gc-child`
  (thin `#eef2f6` top divider, 8px padding-top).
- `crm/docs/ui-spec/screens/S03-customer-360-detail.md`: removed the
  `sidebar: "(sidebar blocks stacked)"` placeholder sample — the children render now
  carries the cell. Build regenerated S03's ASCII accordingly.
- `verify-runtime.mjs`: new assertion I(f) — S03 sidebar grid cell must contain >0
  `.gc-child` mini-sections (found 5: core_info, head_line, contact, dates, tags).
  Updated stale Section J comment ("children unimplemented" → skip-floating rule).

**Visual check (1 iteration):** `scratchpad/s03-v2.png` — sidebar right rail now reads
as 5 stacked blocks with samples dominant and action pills per block; sidebar.warning
appears only via the floating toggle. Approved visually.

**Verification:** verify-runtime PASS A-J, 0 errors (incl. new I(f): 5 child sections).
`validate.mjs` passes with 0 warnings after final rebuild.

## Unresolved Questions

None.

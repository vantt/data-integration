# Phase 1 — row_heights + viewport frame

## Requirement
Vertical proportions and horizontal viewport of the Layout tab reflect the real screen.

## Changes

**`row_heights` key** (optional, array of CSS track strings, one per base `areas` row):
- `render-grid.js` → `grid-template-rows`; variant prepend/append rows get `auto`
- `validate.mjs` → new warn `VR-LAYOUT-ROWS` when `row_heights.length !== areas.length`
- ASCII generator: ignore (keep current uniform rows — YAGNI)

**Viewport frame:**
- `render-grid.js`: wrap `.grid-main` grid in `.viewport-frame` sized by surface `platforms` frontmatter — desktop → max-width 1280px, mobile-only → 390px; label chip showing platform + width
- styles: new rules (frame border, centered, label)

## Files
- `.skills/ui-spec/tools/wireframe/client/render-grid.js`
- `.skills/ui-spec/tools/wireframe/layout-schema.mjs` (LAYOUT_KEYS already has row_heights from phase 0)
- `.skills/ui-spec/tools/validate.mjs`
- styles module (append to grid styles chunk)

## Validation
- S14 gets `row_heights` pilot values; screenshot shows talk_track/talking_points visibly taller than alert_row
- Surfaces without `row_heights` render exactly as before

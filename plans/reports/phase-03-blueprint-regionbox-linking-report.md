# Phase 03 — Blueprint ↔ Region-Box Linking — Report

**Date:** 2026-07-02  
**Branch:** feature/task-detail-cockpit-backend

## Decision: both directions implemented

The implementation stayed under 88 lines (client code), well within the 150-line gate. Both directions are live:

- **Blueprint → Interactions:** region names in `<pre>` get dotted-underline spans; click switches to Interactions subtab and flashes the matching region-box.
- **Interactions → Blueprint:** clicking any region-label header switches to Blueprint and highlights the matching span.

Region-label → Blueprint was chosen over "xem blueprint" affordance (option 3 in spec) because it requires zero new DOM elements, uses the existing clickable label surface, and rounds out the 2-way contract symmetrically.

## Files changed

| File | Change |
|---|---|
| `.agents/skills/ui-spec/tools/wireframe/client/blueprint-link.js` | **New** — 88 lines; `initBlueprintLinks`, `flashRegionBox`, `flashBlueprintSpan` |
| `.agents/skills/ui-spec/tools/wireframe/client/render-regionbox.js` | `data-region` attr added to `.region-box` and `.region-label` divs (both empty and non-empty branches) |
| `.agents/skills/ui-spec/tools/wireframe/client/app.js` | `removeAttribute("data-linked")` at top of `renderMain`; `initBlueprintLinks()` call at end |
| `.agents/skills/ui-spec/tools/wireframe/html-shell.mjs` | `"blueprint-link.js"` added to inlined file list (after `render-regionbox.js`) |
| `.agents/skills/ui-spec/tools/wireframe/styles-phase2.mjs` | `.bp-region-span`, `.bp-span-active`, `.region-label-link`, `.region-box-flash` + `@keyframes region-flash` |
| `.agents/skills/ui-spec/tools/wireframe/verify-runtime.mjs` | Section G added (G1–G3 assertions) |

## Spec deviations

1. **`.region-title` → `.region-label`**: phase spec referenced `.region-title` but the actual class in `render-regionbox.js` is `.region-label`. Fixed to match real HTML.
2. **`CSS.escape` → `attrSelectorEscape`**: replaced `CSS.escape()` with a minimal inline helper since jsdom (used by verify-runtime.mjs) does not expose the `CSS` global. Region names are `\w`+`_` so behavior is identical in practice.
3. **`data-region` on region-boxes**: spec assumed this attribute existed; it did not. Added to both `.region-box` and `.region-label` in `render-regionbox.js`.

## Verification output

```
Section G: Blueprint ↔ region-box linking …
  G1 surface 'S14': 3 bp-region-span(s) injected -- OK
  G2 bp-region-span click switches to Interactions -- OK
  G3 region-label click switches to Blueprint -- OK

RESULT: PASS -- all assertions clean, zero runtime errors
Surfaces exercised : 54 | Flows exercised : 6 | Errors : 0
```

Build command: `node build.mjs --root crm/docs/ui-spec` — succeeds, 54 surfaces, 311 actions.

## Notes

- S14 has 14 declared regions; only 3 appear as standalone tokens in the ASCII (most are embedded in prose/box labels where word-boundary regex blocks false positives). Silently skipped per spec.
- Parenthesized forms like `(alert_row)` match naturally — `(` and `)` are non-word chars satisfying the lookbehind/lookahead.
- The `data-linked` guard prevents re-running `initBlueprintLinks` on the same surface, cleared by `removeAttribute` at the top of `renderMain` when the surface changes.

## Unresolved questions

None. Phase 6 (CSS grid renderer) will supersede most visual value here as planned.

---

Status: DONE  
Summary: 2-way Blueprint ↔ Interactions linking implemented in 88 lines of new client code (under 150-line gate); verify-runtime sections A-G all pass with 0 errors across 54 surfaces and 6 flows.

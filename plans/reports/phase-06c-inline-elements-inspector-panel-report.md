# Phase 6c — Inline Elements & Inspector Panel

**Date:** 2026-07-02  
**Branch:** feature/task-detail-cockpit-backend  
**Status:** DONE

---

## What was done

### PART A — Grid cells (all 40 layout surfaces)

**1. Removed gc-pills row**  
`gridCellHtml` in `render-grid.js` now returns only `gc-label + gc-sample`. All gc-pills CSS removed from `styles-phase6.mjs`. The Interactions tab (render-regionbox.js) is untouched.

**2. Inline chip tokenization**  
Added `tokenizeSample(raw)` (splits on `[...]`) and `renderSampleWithChips(raw, elements)` (escapes each part, wraps bracket tokens as `<span class="gc-inline-chip">` with 1px border, radius 4, cursor pointer). Chips matching a `layout.elements` key get class `gc-inline-chip-mapped` (blue border + data-action-id). Chips in `gc-child` sections share the same path.

**3. Fixed inspector panel (#grid-inspector)**  
A `300px` sticky column added to the right of `.grid-with-inspector` (flex row). Always visible when Layout tab is active. Content states:
- **Default:** hint text "Hover một element hoặc vùng để xem contract" + surface-level counts (N interactions · M reactions)
- **Cell hover:** region name + compact interaction rows (element, trigger → action, guard)
- **Mapped chip hover:** full contract (id, element, trigger, action, target clickable → navigateTo, guard, effects)
- **Unmapped chip hover:** "[text] — chưa gắn contract" + region interaction fallback
- **Click:** pins panel (footer shows "📌 ghim · click ngoài để bỏ"); click outside `.grid-with-inspector` unpins
- **Mapped chip click** on navigate/open_overlay: also fires `handleInteraction` (existing behavior preserved)

Event wiring: `rewireInspectorHover(viewGridDiv, surface)` is called after every `renderGrid` + innerHTML assignment (in `renderMain` and `switchGridVariant`). Uses a document-level unpin handler that removes itself on re-render.

**4. Flex layout**  
`.grid-with-inspector { display:flex; gap:16px; align-items:flex-start }` wraps `.grid-main` (flex:1) and `.grid-inspector` (width:300px, sticky top:72px). `.grid-container` no longer has `max-width` / `margin:0 auto` — the flex parent handles sizing.

---

### PART B — Schema + S14 pilot

**5. `extract-layout.mjs`**  
Added `"elements"` to `KNOWN_KEYS`. YAML `elements:` map is parsed as-is and exposed on `model.elements` (plain object). Absent key → `undefined`. No change to `layoutAreaNames` or `nonRectRegions`.

**6. `validate.mjs` — VR-ELEMENT-REF**  
New warn-level rule added before VR-WIREFRAME-STALE. For each surface whose layout has an `elements` object, every value must be a known action id (in the post-pass-1 `actionIndex`). Unknown ref → `warn(file, "layout.elements[...] references unknown action id ...")`.

**7. S14 pilot — verified mappings**

| Chip text | Action id | Verification |
|---|---|---|
| `📞Gọi` | A-S14-006 | `btn_call` · identity_bar · click · open_overlay → M08 ✓ |
| `360` | A-S14-007 | `btn_view_360` · identity_bar · click · navigate → S03 ✓ |
| `📋Copy` | A-S14-001 | `btn_copy_talk_track` · talk_track · click · mutate ✓ |
| `⏱Đặt lịch` | A-S14-024 | `btn_reason_schedule` · reason_to_call · click · open_overlay → M05 ✓ |

Outcome-bar buttons (✓Gọi được etc.) skipped — all map to A-S14-009 with different implicit params; too ambiguous per spec ("wrong guesses worse than fewer mappings").

**8. Chip matching**  
Exact string inside `[...]` (trimmed by the bracket regex) matched against `layout.elements` keys at render time. No normalization.

---

## Tests

| Test | Result |
|---|---|
| `extract-layout.test.mjs` (11 tests including 2 new) | 11 passed, 0 failed |
| `validate.mjs` on spec root | VR-ELEMENT-REF silent (all pilot refs valid) · 0 errors · 0 new warnings |
| `verify-runtime.mjs` (A–J including new I(g) + I(h)) | 54 surfaces, 6 flows, 0 errors — PASS |

Hover state verified via jsdom (I(h) dispatches mouseover on `.gc-inline-chip[data-action-id]`, asserts inspector HTML contains `A-S14-006`). Static screenshots confirm no hover-state content.

---

## Screenshots

- `s14-v3.png` — S14 default variant: no pills; mapped chips blue-bordered; inspector panel right side with counts
- `s03-v3.png` — S03: child sub-layout intact; inspector shows counts; floating toggle present
- Path: `C:\Users\Vantt\AppData\Local\Temp\claude\D--Vantt-app-data-integration\1136e5d4-c63a-4bb1-91a8-38e4c74132f3\scratchpad\`

---

## Files changed

| File | Change |
|---|---|
| `.agents/skills/ui-spec/tools/wireframe/client/render-grid.js` | Rewrite: remove gc-pills, add chip tokenizer, inspector panel, rewireInspectorHover |
| `.agents/skills/ui-spec/tools/wireframe/styles-phase6.mjs` | Remove gc-pills CSS; add gc-inline-chip, grid-with-inspector, inspector panel styles |
| `.agents/skills/ui-spec/tools/wireframe/client/app.js` | +1 line: `rewireInspectorHover(gridDiv, s)` after renderGrid in renderMain |
| `.agents/skills/ui-spec/tools/wireframe/extract-layout.mjs` | Add `"elements"` to KNOWN_KEYS |
| `.agents/skills/ui-spec/tools/validate.mjs` | Add VR-ELEMENT-REF warn rule |
| `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` | Add `elements:` map to ui-layout fence; ASCII regenerated by build |
| `.agents/skills/ui-spec/tools/wireframe/extract-layout.test.mjs` | +2 tests (Test 10, Test 11) |
| `.agents/skills/ui-spec/tools/wireframe/verify-runtime.mjs` | +Section I(g) + I(h) |
| `crm/docs/ui-spec/generated/wireframe-v2.html` | Regenerated |

---

## Unresolved questions

- **Chip text normalization**: currently exact string inside brackets is matched (e.g. "📞Gọi" not "Gọi"). If a surface's sample uses inconsistent spacing or Unicode composition, chips won't map. No case arose in S14 pilot but worth noting for future bulk migration.
- **Inspector sticky offset**: `top: 72px` hard-coded to clear the topbar. If the topbar height changes (e.g. multi-line on narrow viewport) the panel may overlap. Not a blocker for desktop-only stakeholder review.
- **gc-pills CSS removed** but no other surfaces used gc-pill class (it was grid-only). If any external tool scraped the HTML for `.gc-pill` selectors, those would stop matching. No evidence of such a consumer.

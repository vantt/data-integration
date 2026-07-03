# Phase 08d — ASCII Injection, Build, Docs Integration Report

Date: 2026-07-02

## Generator Run Stats

| Pass | Surfaces with layout | Written | Unchanged | Skipped |
|------|---------------------|---------|-----------|---------|
| First  | 40 | 39 | 1 (S14 already had markers) | 14 (flows + standalone md) |
| Second | 40 | 0 | 40 | 14 |

Idempotency confirmed: second pass wrote 0 files.

The 14 skipped files are: F01-F06 (flow surfaces — no `yaml ui-layout` fence) plus 8 standalone docs (`00-overview.md`, `15-system-events.md`, `20-domain-rules.md`, `30-states-and-errors.md`, etc.).

## Generator Fixes

None required. The generator ran cleanly on all 40 layout surfaces without defensive patching.

## Build Output

```
✓ built generated/: surface-registry.yaml, navigation-graph.yaml, action-registry.csv, coverage-report.md
  surfaces=54 actions=311 flows=6
✓ built generated/wireframe-v2.html
✓ ascii: 40 surface(s) with layout — all up to date
```

## Unit Tests

| File | Result |
|------|--------|
| extract-layout.test.mjs | 9 passed, 0 failed |
| generate-ascii.test.mjs | 33 passed, 0 failed |

## verify-runtime Result

All sections A-J passed. Final tail:

```
Section J: Grid render smoke (all surfaces with layout) …
  J grid smoke: 40 surfaces rendered without crash, 14 skipped (no layout) — OK

========================================
verify-runtime summary
========================================
Surfaces exercised : 54
Flows exercised    : 6
Errors             : 0

RESULT: PASS -- all assertions clean, zero runtime errors
========================================
```

### Fix required during Step 5

Section I(d) originally asserted "S01 has no layout → subtab-grid hidden." Since Phase 8 injected ASCII markers into all 40 layout surfaces (including S01), this check was stale. Fixed by changing the spot-check target from S01 to F01 (flow surfaces genuinely have no `yaml ui-layout` fence). The fix is in `verify-runtime.mjs` with an explanatory comment.

## Section J

Added before the `// Summary` block in `verify-runtime.mjs`. Output: `J grid smoke: 40 surfaces rendered without crash, 14 skipped (no layout) — OK`.

## render-grid.js Changes

No functional changes. Updated JSDoc comment for `layout.children →` line to document the intentional non-rendering of child regions, preventing double-render with floating regions (S03: `sidebar.warning` appears in both `floating` and `children.sidebar.areas`).

## Templates Updated

| File | Change |
|------|--------|
| `templates/surfaces/screen.md` | Replaced hand ASCII block with `yaml ui-layout` fence + markers. Default areas: header, body, footer |
| `templates/surfaces/modal.md` | Same pattern. Default areas: header, body, actions |
| `templates/surfaces/panel.md` | Same pattern. Default areas: header, content |
| `templates/surfaces/overlay.md` | Same pattern. Default areas: header, body, actions |

`component.md` and `flow.md` not touched.

## SKILL.md Updates

Surgical additions only:

1. `### build` — two new bullets: `generated/wireframe-v2.html` and ASCII injection note.
2. `interpret:wf` — added "Preferred workflow" note pointing to `tools/build.mjs`.
3. New `### ui-layout fence (spatial layout model)` section inserted after "Surface file anatomy" code block — includes full schema, generated ASCII marker note, and regions rule.
4. Compiler pipeline diagram — expanded to list all 6 generated outputs including `wireframe-v2.html` and ASCII injection.

## Top-5 Surfaces: Generated ASCII vs Hand ASCII Deviation

Surfaces already had rich hand-drawn ASCII prose above the START marker. The generated ASCII adds clean bounding-box diagrams between markers. Surfaces with largest delta between hand ASCII and generated:

1. **S03** — hand ASCII describes a full 2-column layout with 7-tab sub-nav and sidebar breakdown with 6 named sub-blocks; generated shows 3-region grid (topbar/tab_bar/main_col + sidebar) with a floating `SIDEBAR.WARNING` block. Children sub-layout (sidebar.warning, sidebar.core_info, etc.) intentionally absent from grid (design decision documented in render-grid.js).

2. **S14** — most complex screen: hand ASCII has call-outs, arrows, nested cockpit sections with reasons/talking-points/objection-handling grids; generated shows clean 3-column grid with stop_banner floating + full_screen variant topbar. Significantly simpler but structurally accurate.

3. **S06** — hand ASCII shows conversation thread with message bubbles, reply box, and sidebar assignment; generated shows 3-row layout (conv_header / message_list / reply_bar) + info_sidebar. No nested call-outs.

4. **S09** — hand ASCII shows segment builder with live-count badge, condition rows, and rule connector buttons; generated shows 2-column grid (builder_panel / preview_panel). Rich interaction annotations absent.

5. **S11** — hand ASCII shows campaign detail header, stats strip, recipient table, and action row; generated shows 4-row stacked layout (campaign_header / stats_bar / target_list / action_bar). Richly annotated original simplified to pure bounding boxes.

**Note:** all hand ASCII is preserved above the START marker — the generated ASCII is additive only.

## Unresolved Questions

None.

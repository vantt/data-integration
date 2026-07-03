# Phase 05 — ui-layout Schema + Parser + VR-LAYOUT-* Validation

**Date:** 2026-07-02  
**Branch:** feature/task-detail-cockpit-backend  
**Status:** DONE

---

## What Was Done

### 1. `tools/wireframe/extract-layout.mjs` (new)

- `extractLayout(rawMarkdown)` — regex `FENCE_RE` matches ` ```yaml ui-layout` (handles CRLF + up to 3 leading spaces per CommonMark); returns model or `null` when fence absent or YAML invalid. Unknown top-level keys collected into `model._warnings[]` rather than crashing.
- `layoutAreaNames(model)` — returns `Set<string>` of all region names from: base `areas`, `variants[*].prepend_rows/append_rows`, `floating[*].region`, `children` (1-level). Covers the full "all layout names" contract from the task.
- `nonRectRegions(model)` — builds a cell map from the base `areas` matrix only (floating/variant-row names have no cells → skipped silently). Returns offending names.

### 2. `tools/interpret-wireframe.mjs` enriched

Added `import { extractLayout }` and attached `layout = extractLayout(raw)` inside `buildSurfaceData()`. Each surface object now carries a `.layout` key (null when no fence).

### 3. `tools/wireframe/extract-prose.mjs` — ui-layout fence stripped

Added one `text.replace(/```yaml\s+ui-layout[\s\S]*?```/g, "")` pass so the YAML block is removed from prose before Blueprint view and `findAsciiBlock`. This prevents the structured YAML from showing raw in the Blueprint tab or confusing the box-drawing detector.

### 4. `tools/validate.mjs` — three new VR-LAYOUT-* rules

Inserted after VR-REGION-PARENT, imports `extractLayout / layoutAreaNames / nonRectRegions`:

| Rule | Level | Trigger |
|---|---|---|
| VR-LAYOUT-UNKNOWN | error | region name in areas/floating/samples not in frontmatter `regions[]` |
| VR-LAYOUT-RECT | error | region cells in areas matrix don't form a solid rectangle |
| VR-LAYOUT-ORPHAN | warn | declared region missing from all layout areas + floating + variants |

### 5. Pilot: `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md`

Inserted `yaml ui-layout` block directly under `## Layout` heading (before first `###`). Kept all hand-drawn ASCII diagrams intact below.

Layout covers all 14 declared regions:
- 12 in areas (including `reason_to_call` spanning rows 3-4, `collect` spanning rows 6-7)
- 1 in floating (`stop_banner`)
- 1 in variant prepend_rows (`topbar`)

**strategy_summary placement check:** Row 4, left column `[strategy_summary, reason_to_call]`. Verified against spec:
- ASCII shows "⏱ Gọi 1-2 ngày, giờ hành chính" immediately below talk_track in the LEFT column.
- Data sourcing section confirms timing comes from `approach.timing` field of the script (LEFT + guardrails).
- No interactions reference `strategy_summary` as region (it's a read-only display band).
- Placement in row 4 is correct. No adjustment needed.

### 6. `tools/wireframe/extract-layout.test.mjs` (new)

9 self-contained node assertions, no framework:

| # | Test | Pass |
|---|---|---|
| 1 | Valid 2-col grid parses | ✓ |
| 2 | `layoutAreaNames` returns all 6 names (areas+floating+variant) | ✓ |
| 3 | L-shaped region flagged by `nonRectRegions` | ✓ |
| 4 | Full-row header (1×2 rectangle) not flagged | ✓ |
| 5 | Missing `areas` key → null | ✓ |
| 6 | YAML parse error → null | ✓ |
| 7 | No fence → null | ✓ |
| 8 | Region spanning 2 rows in same column is valid | ✓ |
| 9 | Unknown key collected as `_warnings`, model returned | ✓ |

---

## Verification Output

### Test suite
```
extract-layout.test: 9 passed, 0 failed
```

### Validate
```
Scanned 54 spec files, 311 actions, 52 surfaces.
⚠ [wireframe] wireframe-v2.html is older than 1 spec file(s) — run build to regenerate

✓ validation passed (1 warning(s)).
```
No VR-LAYOUT-* errors. No VR-LAYOUT-ORPHAN warns. The single warning is the pre-existing stale-wireframe notice, which resolves after build.

### Build
```
✓ built generated/: surface-registry.yaml, navigation-graph.yaml, action-registry.csv, coverage-report.md
  surfaces=54 actions=311 flows=6
✓ built generated/wireframe-v2.html
```

### verify-runtime (A-H)
```
RESULT: PASS -- all assertions clean, zero runtime errors
Surfaces exercised: 54 | Flows exercised: 6 | Errors: 0
```
All sections A-H clean. No regression.

### S14 layout in SURFACES JSON
```
S14 keys: file, id, meta, contract, prose, asciiLayout, layout, states, errors
S14.layout.areas rows: 9
S14.layout.floating: [{region: "stop_banner", when: "recommended == false", replaces: [...]}]
S14.layout.variants: ["full_screen"]
S14.layout.samples keys: topbar, identity_bar, alert_row, talk_track, strategy_summary,
  talking_points, objection_handling, guardrails, reason_to_call, snapshot, collect,
  trust_footer, outcome_bar
```

---

## Files Changed

| File | Change |
|---|---|
| `.agents/skills/ui-spec/tools/wireframe/extract-layout.mjs` | New — parser + helpers |
| `.agents/skills/ui-spec/tools/wireframe/extract-layout.test.mjs` | New — 9 node tests |
| `.agents/skills/ui-spec/tools/wireframe/extract-prose.mjs` | Strip ui-layout fence from prose |
| `.agents/skills/ui-spec/tools/interpret-wireframe.mjs` | Import + attach `.layout` to surfaces |
| `.agents/skills/ui-spec/tools/validate.mjs` | Add VR-LAYOUT-* rules (import + block) |
| `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` | Insert yaml ui-layout pilot block |

---

## Unresolved Questions

None. Phase 5 complete and clean. Phase 6 (CSS grid renderer with samples + floating toggle) can proceed.

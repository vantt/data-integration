# Phase 05 — ui-layout Schema + Parser + VR-LAYOUT-* Validation

## Context links
- `tools/extract.mjs` (120 lines) — `extractAll()` + `SPEC_ROOT`; reads raw file per surface
- `tools/interpret-wireframe.mjs` — `buildSurfaceData()` enrichment loop; best place to attach `.layout`
- `tools/validate.mjs` — pass-1 / pass-2 structure; `err()` / `warn()` helpers; `surfaceRegions` map already built
- `tools/wireframe/ascii-normalize.mjs` — width logic reference; `normalizeAsciiBlock()`
- `crm/docs/ui-spec/surfaces/S14-*.md` — pilot surface; has hand-drawn `## Layout` ASCII block
- `templates/surfaces/*.md` — will need `ui-layout` placeholder added in phase 08

## Schema definition

New fenced code block inside `## Layout` section of a surface .md:

~~~
```yaml ui-layout
columns: ["1fr", "2fr"]
areas:
  - [header,   header  ]
  - [sidebar,  main    ]
  - [footer,   footer  ]
floating:
  - region: action_bar
    when: scroll_threshold
    replaces: []
variants:
  full_screen:
    prepend_rows:
      - [main, main]
samples:
  header: "Nguyễn Văn A · 0912 345 678"
  main:   "Lý do gọi: Tái đặt hàng SP001"
```
~~~

All keys optional except `areas` (minimum viable layout). `columns` defaults to equal-width if omitted.
`children` key (for dotted regions like `sidebar.core_info`) is a nested layout object — same schema, `areas` required if present.

## Files to modify / create

| File | Change |
|---|---|
| `tools/wireframe/extract-layout.mjs` | New — parse `yaml ui-layout` fence from raw markdown |
| `tools/interpret-wireframe.mjs` | Import + call `extractLayout`; attach `.layout` to surface objects |
| `tools/validate.mjs` | Add VR-LAYOUT-UNKNOWN, VR-LAYOUT-RECT, VR-LAYOUT-ORPHAN rules |

## Implementation steps

### 1. New `tools/wireframe/extract-layout.mjs`

```js
// extract-layout.mjs — parse ```yaml ui-layout fence from surface markdown.
// Returns layout model object or null if fence absent / unparseable.

import yaml from "js-yaml";

const FENCE_RE = /^```yaml\s+ui-layout\s*\n([\s\S]*?)^```/m;

export function extractLayout(rawMarkdown) {
  const m = rawMarkdown.match(FENCE_RE);
  if (!m) return null;
  try {
    const model = yaml.load(m[1]);
    if (!model || typeof model !== "object" || !Array.isArray(model.areas)) return null;
    return model;
  } catch {
    return null;  // parse error — caller decides whether to warn
  }
}

/** Collect all unique region names from areas matrix (including variant prepend_rows). */
export function layoutAreaNames(model) {
  const names = new Set();
  const rows = [...(model.areas || [])];
  for (const v of Object.values(model.variants || {})) {
    for (const row of v.prepend_rows || []) rows.push(row);
  }
  for (const row of rows) for (const cell of row) names.add(cell);
  return names;
}

/** Validate each region forms a solid rectangle in areas matrix. Returns array of offending region names. */
export function nonRectRegions(model) {
  const areas = model.areas || [];
  const offending = [];
  const nameSet = layoutAreaNames(model);
  for (const name of nameSet) {
    const cells = [];
    for (let r = 0; r < areas.length; r++)
      for (let c = 0; c < areas[r].length; c++)
        if (areas[r][c] === name) cells.push([r, c]);
    if (!cells.length) continue;
    const minR = Math.min(...cells.map(([r]) => r));
    const maxR = Math.max(...cells.map(([r]) => r));
    const minC = Math.min(...cells.map(([, c]) => c));
    const maxC = Math.max(...cells.map(([, c]) => c));
    const expected = (maxR - minR + 1) * (maxC - minC + 1);
    if (cells.length !== expected) offending.push(name);
  }
  return offending;
}
```

### 2. Enrich `interpret-wireframe.mjs` — `buildSurfaceData()`

```js
import { extractLayout } from "./wireframe/extract-layout.mjs";
// Inside loop, after extractProse:
let layout = null;
try { layout = extractLayout(raw); } catch { /* ignore */ }
surfaces.push({ ..., layout, /* existing fields */ });
```

### 3. `validate.mjs` — VR-LAYOUT-* rules

Add after VR-REGION-PARENT block, reusing `surfaceRegions` and raw file reads already present:

```js
// VR-LAYOUT-*: validate ui-layout fence when present
import { extractLayout, layoutAreaNames, nonRectRegions } from "./wireframe/extract-layout.mjs";

for (const f of files) {
  if (!f.meta?.id) continue;
  let raw;
  try { raw = readFileSync(join(SPEC_ROOT, f.file), "utf8"); } catch { continue; }

  let layout;
  try { layout = extractLayout(raw); } catch {
    warn(f.file, "ui-layout fence present but failed to parse (VR-LAYOUT-PARSE)");
    continue;
  }
  if (!layout) continue;

  const sid = f.meta.id;
  const declaredRegions = surfaceRegions.get(sid) || [];
  const areaNames = layoutAreaNames(layout);

  // VR-LAYOUT-UNKNOWN: area cell name not in frontmatter regions[]
  for (const name of areaNames) {
    if (!declaredRegions.includes(name))
      err(f.file, `ui-layout area \`${name}\` not in frontmatter regions[] (VR-LAYOUT-UNKNOWN)`);
  }

  // VR-LAYOUT-RECT: each region must form a solid rectangle
  for (const bad of nonRectRegions(layout))
    err(f.file, `ui-layout region \`${bad}\` does not form a solid rectangle (VR-LAYOUT-RECT)`);

  // VR-LAYOUT-ORPHAN: declared region absent from areas + floating (warn only)
  const floatingNames = new Set((layout.floating || []).map(f => f.region));
  for (const r of declaredRegions) {
    if (!areaNames.has(r) && !floatingNames.has(r))
      warn(f.file, `region \`${r}\` declared in frontmatter but absent from ui-layout areas+floating (VR-LAYOUT-ORPHAN)`);
  }
}
```

`readFileSync` and `join` already imported in `validate.mjs`.

## Fixture-based tests

Create `tools/wireframe/__tests__/extract-layout.test.mjs` (manual node --test or vitest):

1. Valid `areas` with 2-column grid → returns model, `layoutAreaNames` returns correct set.
2. Non-rectangular region → `nonRectRegions` returns that region name.
3. Rectangular spanning region (e.g. `header` spanning 2 cols) → returns empty array.
4. Missing `areas` key → returns null.
5. YAML parse error → returns null.

## Pilot: S14

1. Add `yaml ui-layout` fence to `S14-*.md` `## Layout` section (hand-author matching existing ASCII).
2. Add `columns`, `areas` (2-column LEFT/RIGHT with `reason_to_call` spanning), `samples`.
3. Run `validate.mjs` → VR-LAYOUT-* rules pass for S14.
4. Confirm `extractAll` still works (layout fence does not confuse contract block extraction).

## Validation
1. `node tools/validate.mjs --root crm/docs/ui-spec` → no new errors for surfaces without layout fence.
2. S14 with valid fence → no VR-LAYOUT-* errors.
3. Deliberately introduce a non-rectangular region → VR-LAYOUT-RECT error fires.
4. Deliberately add area name not in regions[] → VR-LAYOUT-UNKNOWN error fires.
5. Declared region missing from areas → VR-LAYOUT-ORPHAN warn (not error).

## Risks & rollback
- **Risk:** `yaml ui-layout` fence regex mismatches if fence uses 4 backticks or Windows CRLF — use `\r?\n` in FENCE_RE and match ` {0,3}``` ` to be safe.
- **Risk:** `js-yaml` not yet in `tools/node_modules` — check `tools/package.json`; it's already used by `build.mjs` so it will be present.
- **Risk:** `validate.mjs` reads raw files per surface in the new loop — adds file I/O on every validate run; acceptable for <100 surfaces.
- **Rollback:** `extractLayout` returns null for surfaces without fence → zero behavior change; remove VR-LAYOUT-* block from validate.mjs to disable entirely.

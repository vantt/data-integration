# Phase 07 — ASCII Generator from Layout Model

## Context links
- `tools/wireframe/ascii-normalize.mjs` (143 lines) — `normalizeAsciiBlock(raw)`: wide-char substitutions (`▶→>`, `⚠→!`, etc.), uniform box-drawing; width constants; reference for column-budget logic
- `tools/wireframe/extract-layout.mjs` (phase 05) — `extractLayout(raw)`, `layoutAreaNames(model)`
- `tools/build.mjs` — calls registries then `generateWireframe`; ASCII generation hooked here
- `crm/docs/ui-spec/surfaces/S14-*.md` — pilot; existing hand-drawn ASCII in `## Layout` is the diff target
- Spec root: `crm/docs/ui-spec/`

## Requirements
1. Given a `ui-layout` model, generate box-drawing ASCII that fits in 78 columns.
2. Include `samples[region]` as a content line inside each cell.
3. Each named `variant` gets a separate ASCII block below the default.
4. `floating` regions rendered as a standalone STOP-variant block.
5. Output written between markers `<!-- ui-layout:ascii:start -->` / `<!-- ui-layout:ascii:end -->` in the surface .md.
6. Regeneration is idempotent: same model input → byte-identical output (no timestamps, no random padding).
7. Wide-char substitutions applied (same table as `ascii-normalize.mjs`) so output is safe in monospaced viewers.

## Files to create / modify

| File | Change |
|---|---|
| `tools/wireframe/generate-ascii.mjs` | New — core generator: `generateAscii(model)` + CLI |
| `tools/build.mjs` | Call `generateAscii` per surface with layout model; rewrite markers if changed |

No surface .md files are modified by this phase file — marker insertion is a build-time write.

## Implementation steps

### 1. New `tools/wireframe/generate-ascii.mjs`

#### Column budget
- Total width: 78 chars.
- N columns from `model.columns`. Compute pixel-proportional widths from fr values:
  ```js
  function colWidths(columns, total = 78) {
    const frs = (columns || []).map(c => parseFloat(c) || 1);
    const sum = frs.reduce((a, b) => a + b, 0);
    // Distribute, reserving 1 char per separator (N-1 separators + 2 outer borders)
    const inner = total - 2 - (frs.length - 1);
    return frs.map(fr => Math.floor((fr / sum) * inner));
    // Adjust last col to absorb rounding remainder
  }
  ```

#### Cell rendering
Each cell gets: top border row, region-name row, optional sample row, bottom border row.
Cells share borders with neighbours (grid-area spanning handled by merging cells horizontally).

#### Core algorithm
Use a character matrix (array of string arrays, width=78) approach:
1. For each unique region, compute bounding box (minRow, maxRow, minCol, maxCol) from `areas` matrix × `colWidths`.
2. Draw outer rectangle with box-drawing chars (`┌─┐└─┘│`).
3. Write region name left-aligned inside, padded to cell width.
4. Write sample line (if present) on next line, prefixed with `· `.
5. Spanning cells: top/bottom borders drawn at span extremes; internal row borders replaced with space (cell interior).
6. Assemble character matrix into lines; join with `\n`.

#### Wide-char normalization
Apply same substitution table as `ascii-normalize.mjs` to `samples` text before writing into cells.

#### Variant blocks
For each `variants` key, prepend `prepend_rows` to areas and re-render with header `[variant: full_screen]`.

#### Floating block
Render each floating region as standalone single-column block with label `[STOP variant — {when}]`.

#### Marker replacement
```js
export function injectAscii(markdown, asciiBlock) {
  const START = "<!-- ui-layout:ascii:start -->";
  const END   = "<!-- ui-layout:ascii:end -->";
  const block = `${START}\n\`\`\`\n${asciiBlock}\n\`\`\`\n${END}`;
  const re = new RegExp(`${START}[\\s\\S]*?${END}`);
  return re.test(markdown) ? markdown.replace(re, block) : markdown + "\n\n" + block;
}
```

#### CLI
```js
// CLI: node tools/generate-ascii.mjs --root <spec-root> [--surface S14]
import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { extractLayout } from "./wireframe/extract-layout.mjs";
import { generateAscii, injectAscii } from "./wireframe/generate-ascii.mjs";
import { SPEC_ROOT, surfaceDirs } from "./config.mjs";

const args = process.argv.slice(2);
const rootArg = args[args.indexOf("--root") + 1] || SPEC_ROOT;
const surfaceFilter = args[args.indexOf("--surface") + 1] || null;

// ... iterate surface dirs, read .md, extractLayout, generateAscii, injectAscii, writeFileSync ...
```

### 2. `build.mjs` integration

After writing registries and calling `generateWireframe`:
```js
import { generateAscii, injectAscii } from "./wireframe/generate-ascii.mjs";
import { extractLayout } from "./wireframe/extract-layout.mjs";

for (const f of files) {
  const rawPath = join(SPEC_ROOT, f.file);
  let raw;
  try { raw = readFileSync(rawPath, "utf8"); } catch { continue; }
  const layout = extractLayout(raw);
  if (!layout) continue;
  const ascii = generateAscii(layout);
  const updated = injectAscii(raw, ascii);
  if (updated !== raw) {
    writeFileSync(rawPath, updated, "utf8");
    console.log(`  ascii regenerated: ${f.file}`);
  }
}
```

Only writes if content changed → idempotent at file level.

## Idempotency guarantee
- Column widths computed deterministically from fr values via `Math.floor` + fixed remainder assignment to last column.
- No timestamps or counters in output.
- Marker regex is greedy-within-markers only (not cross-marker).
- Test: run generator twice on same model → `diff` shows no changes.

## S14 diff validation
1. Generate ASCII for S14 layout model.
2. `diff` generated output vs existing hand-drawn ASCII in `## Layout`.
3. Acceptable deltas: box-drawing style, exact column widths, whitespace padding.
4. Unacceptable: missing regions, wrong spanning, sample text absent.
5. Adjust `colWidths` budget if hand ASCII uses different proportions — document the chosen ratio.

## Validation
1. `node tools/wireframe/generate-ascii.mjs --root crm/docs/ui-spec --surface S14` → produces ASCII block; no crash.
2. Run twice → files byte-identical (second run writes nothing).
3. S14 generated ASCII visually matches 2-column LEFT/RIGHT layout with `reason_to_call` spanning.
4. `node tools/build.mjs --root crm/docs/ui-spec` → ASCII markers injected in S14.md; `verify-runtime.mjs` green.
5. Surface without `ui-layout` fence: untouched (no marker injected).

## Risks & rollback
- **Risk:** spanning region border calculation — cells that span multiple grid rows/cols need interior border suppression; off-by-one in row/col index is common. Mitigate: unit-test with 2×2 and 3×3 fixture grids before S14.
- **Risk:** wide-char in `samples` text breaks column alignment — normalize samples through the same substitution table as `ascii-normalize.mjs` before writing into cells.
- **Risk:** `injectAscii` regex too greedy if multiple marker pairs exist in one file — use non-greedy `[\s\S]*?`; only one pair should ever exist per surface.
- **Rollback:** remove `build.mjs` ASCII injection loop; existing hand-drawn ASCII remains. Generator file is standalone with no impact on other tools.

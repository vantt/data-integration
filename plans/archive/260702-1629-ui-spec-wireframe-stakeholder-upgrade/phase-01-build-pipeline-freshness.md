# Phase 01 — Build Pipeline Freshness

## Context links
- `tools/interpret-wireframe.mjs` (87 lines) — current CLI entrypoint; `buildSurfaceData()` + `openBrowser()` inline
- `tools/build.mjs` — generates registries; calls `extractAll()` then writes yaml/csv/md
- `tools/wireframe/html-shell.mjs` — `buildHtml(surfaces)` → HTML string; bottombar is `<div id="bottombar"></div>` (populated at runtime by `updateBottomBar()`)
- `tools/validate.mjs` — `statSync` + `readdirSync` already imported; uses `surfaceDirs` from config
- `tools/config.mjs` — exports `specRoot`, `surfaceDirs`, `config`

## Requirements
1. Single `node tools/build.mjs` regenerates registries AND wireframe (no separate run needed).
2. Wireframe output always opens via `--open` flag; default (CI / build) = no open.
3. Bottom-bar of wireframe shows: `Generated {ISO datetime} · {N} surfaces`.
4. `validate.mjs` warns when `generated/wireframe-v2.html` mtime < newest surface .md mtime.

## Files to modify / create

| File | Change |
|---|---|
| `tools/interpret-wireframe.mjs` | Extract `generateWireframe(root, opts)` export; keep CLI wrapper; add `--no-open` / `--open` flag |
| `tools/build.mjs` | Import + call `generateWireframe` after registries; pass `{ open: false }` |
| `tools/wireframe/html-shell.mjs` | Accept optional `generatedAt` / `surfaceCount` params in `buildHtml`; embed stamp in HTML |
| `tools/validate.mjs` | New staleness check block after existing pass-2 rules |

## Implementation steps

### 1. Refactor `interpret-wireframe.mjs`
- Wrap the body (after imports) into `export async function generateWireframe(root, { open = false } = {})`.
- The function: calls `buildSurfaceData()`, calls `buildHtml(surfaces, { generatedAt: new Date().toISOString(), surfaceCount: surfaces.length })`, writes file, conditionally calls `openBrowser` if `open`.
- CLI block at bottom: parse `process.argv` for `--no-open` / `--open`; call `generateWireframe(specRoot, { open: !noOpen })`.
- Default behavior unchanged when run directly (opens browser unless `--no-open`).

### 2. Extend `html-shell.mjs` — `buildHtml`
- Change signature: `export function buildHtml(surfaces, { generatedAt = "", surfaceCount } = {})`.
- In the returned HTML, replace static `<div id="bottombar"></div>` with a sibling `<div id="build-stamp">` element below bottombar (outside `#main` surface logic so it always shows).
- Content: `Generated ${esc(generatedAt)} · ${surfaceCount ?? surfaces.length} surfaces`.
- CSS: `.build-stamp { font-size:11px; color:#94a3b8; padding:4px 16px; border-top:1px solid #1e293b; }` — add to `styles.mjs` CSS block.
- Note: `updateBottomBar()` in `app-chrome.js` targets `#bottombar` (surface rules/platforms) — unaffected.

### 3. Update `build.mjs`
```js
import { generateWireframe } from "./interpret-wireframe.mjs";
// after existing writeFileSync calls:
await generateWireframe(SPEC_ROOT, { open: false });
console.log("✓ wireframe-v2.html generated");
```
- Make `build.mjs` top-level `async` (wrap in IIFE or add `await` at top level with `--experimental-vm-modules` — just wrap existing body in `(async () => { ... })()` to keep Node compatibility).

### 4. Add staleness check to `validate.mjs`
Add after VR-OVERVIEW block, before final report:
```js
// VR-WIREFRAME-STALE: wireframe older than any surface .md → warn
import { statSync as _stat } from "node:fs"; // already imported
const wfPath = join(SPEC_ROOT, "generated", "wireframe-v2.html");
let wfMtime = 0;
try { wfMtime = statSync(wfPath).mtimeMs; } catch { /* not yet generated */ }
if (wfMtime) {
  for (const dir of surfaceDirs) {
    const abs = join(SPEC_ROOT, dir);
    let entries = [];
    try { entries = readdirSync(abs); } catch { continue; }
    for (const e of entries) {
      if (!e.endsWith(".md")) continue;
      const mt = statSync(join(abs, e)).mtimeMs;
      if (mt > wfMtime) { warn("wireframe", "wireframe stale — run build (VR-WIREFRAME-STALE)"); break; }
    }
  }
}
```
- `warn()` helper already defined in validate.mjs; staleness is warn-level (not error, since wireframe is optional output).

## Validation
1. `node tools/validate.mjs --root crm/docs/ui-spec` passes (no new errors).
2. `node tools/build.mjs --root crm/docs/ui-spec` completes; produces `generated/wireframe-v2.html`.
3. Open wireframe in browser; confirm bottom stamp shows ISO datetime and surface count.
4. Confirm S15 visible in sidebar; S14 renders with 14 region chips.
5. Run `node tools/wireframe/verify-runtime.mjs` (Playwright) → green.
6. Touch any surface .md; re-run `validate.mjs` → VR-WIREFRAME-STALE warning appears.
7. Re-run `build.mjs` → warning gone.

## Risks & rollback
- **Risk:** `generate-wireframe.mjs` exported as `async` but callers use `await` — ensure build.mjs is wrapped in async IIFE.
- **Risk:** `--root` flag forwarding from build.mjs to `generateWireframe` — pass `SPEC_ROOT` (already resolved from config) not raw argv string.
- **Rollback:** both `interpret-wireframe.mjs` and `build.mjs` are independent; reverting either leaves the other functional.

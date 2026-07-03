# Phase 1 Report — Build Pipeline + Freshness Stamp + Staleness Warning

**Date:** 2026-07-02
**Branch:** feature/task-detail-cockpit-backend

## Changes Made

### 1. `interpret-wireframe.mjs` — refactored to export `generateWireframe`
- Extracted all generation logic into `export function generateWireframe(rootDir, { open = true } = {})`.
- Added `isMain` detection via `fileURLToPath(import.meta.url) === resolve(process.argv[1])` — CLI block runs only when file is the entry point, not when imported.
- Added `--no-open` CLI flag: `const open = !process.argv.includes("--no-open")`.
- Original CLI behavior (`node interpret-wireframe.mjs --root <dir>`) preserved unchanged.

### 2. `build.mjs` — calls wireframe generation as part of build
- Added `import { generateWireframe } from "./interpret-wireframe.mjs"` (static, top-level).
- After writing 4 registries, calls `generateWireframe(SPEC_ROOT, { open: false })` — browser never opened in build context.
- Added log line `✓ built generated/wireframe-v2.html` matching existing style.

### 3. `wireframe/html-shell.mjs` — freshness stamp in bottom bar
- Added `ictTimestamp()` helper: uses `Intl.DateTimeFormat.formatToParts` with `timeZone: "Asia/Ho_Chi_Minh"` for locale-independent YYYY-MM-DD HH:mm extraction.
- `buildHtml(surfaces)` computes `freshnessStamp = "Generated ${ictTimestamp()} ICT · ${surfaces.length} surfaces"`.
- Embeds as `<div id="gen-stamp">` sibling of `<div id="bottombar">` with inline style (11px, `#94a3b8`, right-aligned, top border). Placed outside `#bottombar` so `updateBottomBar()` in JS doesn't overwrite it.

### 4. `validate.mjs` — staleness warning (VR-WIREFRAME-STALE)
- After all cross-file rules, checks if `generated/wireframe-v2.html` exists and compares its mtime against all `.md` files in `surfaceDirs`.
- Emits `warn("wireframe", "wireframe-v2.html is older than N spec file(s) — run build to regenerate")` — warning, not error, does not block validation gate.
- Uses already-imported `existsSync`, `statSync`, `readdirSync`, `SPEC_ROOT`, `surfaceDirs`.

### 5. `wireframe/verify-runtime.mjs` — added `--root` support
- Added `parseRootArg()` + `--root` flag handling.
- `HTML_PATH` now resolves via `join(rootArg, "generated", "wireframe-v2.html")` when `--root` is given; falls back to legacy hardcoded path otherwise (backward-compat).
- Required to make acceptance criterion 3 pass (legacy hardcoded `frontend/docs/ui-spec` path doesn't exist in this repo).

## Verification Output

**1. `node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec`**
```
✓ built generated/: surface-registry.yaml, navigation-graph.yaml, action-registry.csv, coverage-report.md
  surfaces=54 actions=311 flows=6
ui-spec wireframe v2 — reading spec from: D:\...\crm\docs\ui-spec
  Found 54 surface(s)
  Wireframe v2 written: D:\...\crm\docs\ui-spec\generated\wireframe-v2.html
✓ built generated/wireframe-v2.html
```

**2. Content checks on wireframe-v2.html**
```
Has S15: true
Has alert_row: true | Has snapshot: true | Has reason_to_call: true | Has collect: true
Has gen-stamp: true
Stamp text: 2026-07-02 16:36 ICT · 54 surfaces
```

**3. `node .agents/skills/ui-spec/tools/wireframe/verify-runtime.mjs --root crm/docs/ui-spec`**
```
Surfaces exercised : 54
Flows exercised    : 6
Errors             : 0
RESULT: PASS — all assertions clean, zero runtime errors
```

**4. `node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec`**

After fresh build (no warning):
```
Scanned 54 spec files, 311 actions, 52 surfaces.
✓ validation passed (0 warning(s)).
```

After touching `S01-worklist-dashboard.md` (warning fires):
```
Scanned 54 spec files, 311 actions, 52 surfaces.
⚠ [wireframe] wireframe-v2.html is older than 1 spec file(s) — run build to regenerate
✓ validation passed (1 warning(s)).
```

## Unresolved Questions

None.

---

Status: DONE
Summary: Build pipeline integration, freshness stamp (ICT timestamp + surface count in bottom bar), staleness warning in validate, and `--root` support in verify-runtime all implemented and verified end-to-end. One `build` command now regenerates registries + wireframe together.

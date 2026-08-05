# Phase 0 — Single-writer schema module

## Requirement
All `ui-layout` schema knowledge (key sets, content primitive registry, walkers, flatten) lives in ONE dependency-free module consumed by both node tools and the browser bundle. No behavior change in this phase.

## Files

**Create:** `.skills/ui-spec/tools/wireframe/layout-schema.mjs`
- `LAYOUT_KEYS` — known top-level fence keys (existing 7 + `row_heights` + `content`)
- `CONTENT_TYPES` — primitive registry: `h, text, btn, input, select, checklist, chips, badge, tabs, table, list, kpi, divider, slot, row`
- `contentElementType(el)` — resolve which key of an element object is its type
- `walkContent(content, cb)` — iterate every element (recursing into `row`), cb({region, el, type})
- `contentActionRefs(content)` — [{region, type, label, actionId}] for validator/audit
- `flattenContentLine(elements)` — deterministic 1-line text summary (ASCII blueprint)
- MUST have zero imports (node- and browser-safe)

**Modify:**
- `extract-layout.mjs` — import `LAYOUT_KEYS` (replaces local `KNOWN_KEYS`)
- `html-shell.mjs` — inline `layout-schema.mjs` first in client script order, stripping `export ` prefixes (regex `^export (?=(const|function))` → "")
- `validate.mjs` — no rule changes yet; only if it needs the key set

## Validation
- `node --test .skills/ui-spec/tools/wireframe/` green
- `validate.mjs + build.mjs --root crm/docs/ui-spec` output unchanged (byte-identical wireframe except gen timestamp)

## Risks
- Export-strip regex must not touch function bodies → keep module top-level-export only, verified by test.

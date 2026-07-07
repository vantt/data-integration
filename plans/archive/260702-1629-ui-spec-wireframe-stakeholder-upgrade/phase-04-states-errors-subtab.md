# Phase 04 — States / Errors Subtab

## Context links
- `tools/extract.mjs` (120 lines) — `extractAll()` returns `{ file, id, meta, contract, prose, errors }`; `prose` field is already populated by `extractProse()` call in `interpret-wireframe.mjs`
- `tools/wireframe/extract-prose.mjs` — `extractProse(raw, contractTag)` strips contract block; returns prose markdown
- `crm/docs/ui-spec/30-states-and-errors.md` — catalog of `### ST-*` and `### ERR-*` headings with description text
- `tools/wireframe/html-shell.mjs` — `#surface-subtabs` bar; `buildClientScript` inlines files
- `tools/wireframe/client/app.js` — `renderMain()` calls `renderLayout(s)`; `switchView` controls sub-tab display
- `tools/wireframe/client/app-chrome.js` — `switchView("states")` must be handled
- `tools/wireframe/styles.mjs` — CSS

## Requirements
1. Each surface JSON embedded in wireframe gains a `states` array: `[{ id, label, description, errRefs: [ERR-*] }]`.
2. A "States" subtab button appears in `#surface-subtabs`.
3. Clicking States shows cards: state id badge, label, description prose, linked ERR-* chips (tooltip = catalog description).
4. ERR-* refs not in catalog shown in orange with `(unknown)` tooltip.
5. Surfaces with no ST-* entries show empty-state message.

## Files to modify / create

| File | Change |
|---|---|
| `tools/wireframe/extract-states.mjs` | New — extract ST-*/ERR-* from prose `## States` section |
| `tools/interpret-wireframe.mjs` | Import `extractStates`; attach `.states` and `.errCatalog` to surface objects |
| `tools/wireframe/html-shell.mjs` | Add States subtab button; add `"render-states.js"` to inline list; inject `ERR_CATALOG` JSON |
| `tools/wireframe/client/render-states.js` | New — render states cards HTML |
| `tools/wireframe/client/app.js` | Add `#view-states` show/hide in `switchView` (via `app-chrome.js`); wire subtab click |
| `tools/wireframe/client/app-chrome.js` | Extend `switchView` to handle `"states"` view; add `<div id="view-states">` display toggle |
| `tools/wireframe/styles.mjs` | State card styles |

## Implementation steps

### 1. New `tools/wireframe/extract-states.mjs`

```js
// extract-states.mjs — parse ## States section from surface prose.
// Returns { states: [{id, label, description, errRefs}], errIds: Set<string> }

const ST_SECTION_RE = /^##\s+States?\s*$/im;
const NEXT_H2_RE    = /^##\s+/m;
const ST_BULLET_RE  = /^\s*[-*]\s+\*{0,2}(ST-[A-Za-z0-9-]+)\*{0,2}[:\s—–-]+(.+)/;
const ERR_REF_RE    = /ERR-[A-Za-z0-9-]+/g;

export function extractStates(prose) {
  const sectionStart = prose.search(ST_SECTION_RE);
  if (sectionStart === -1) return { states: [], errIds: new Set() };

  const afterHeader = prose.slice(sectionStart).replace(ST_SECTION_RE, "");
  const nextH2 = afterHeader.search(NEXT_H2_RE);
  const section = nextH2 === -1 ? afterHeader : afterHeader.slice(0, nextH2);

  const states = [];
  const errIds = new Set();
  for (const line of section.split("\n")) {
    const m = line.match(ST_BULLET_RE);
    if (!m) continue;
    const id = m[1];
    const rest = m[2].trim();
    // Split label from description at ' — ' or ': '
    const sepIdx = rest.search(/ [—–-] | :\s/);
    const label       = sepIdx === -1 ? rest : rest.slice(0, sepIdx).trim();
    const description = sepIdx === -1 ? ""   : rest.slice(sepIdx).replace(/^[—–:\s-]+/, "").trim();
    const errRefs = [...(description + " " + label).matchAll(ERR_REF_RE)].map(x => x[0]);
    errRefs.forEach(e => errIds.add(e));
    states.push({ id, label, description, errRefs });
  }
  return { states, errIds };
}

export function readErrCatalog(specRoot) {
  // Read 30-states-and-errors.md, extract ERR-* heading + following text as description.
  import { readFileSync, readdirSync } from "node:fs";
  import { join } from "node:path";
  const catalog = {};
  try {
    const name = readdirSync(specRoot).find(n => /states/i.test(n) && n.endsWith(".md"));
    if (!name) return catalog;
    const raw = readFileSync(join(specRoot, name), "utf8");
    const matches = [...raw.matchAll(/^#{2,4}\s+(ERR-[A-Za-z0-9-]+)\s*\n([\s\S]*?)(?=^#{2,4}\s|$)/gm)];
    for (const m of matches) {
      catalog[m[1]] = m[2].trim().split("\n")[0].replace(/^[-*]\s+/, "");
    }
  } catch { /* unreadable */ }
  return catalog;
}
```

Note: `import` statements inside function body are invalid — restructure `readErrCatalog` as a top-level function with top-level imports when implementing.

### 2. Enrich surface data in `interpret-wireframe.mjs`

In `buildSurfaceData()`, after existing `extractProse` call:
```js
import { extractStates, readErrCatalog } from "./wireframe/extract-states.mjs";
// Once before loop:
const errCatalog = readErrCatalog(specRoot);
// Inside loop:
const { states } = extractStates(prose);
surfaces.push({ ..., states, /* existing fields */ });
```

Pass `errCatalog` into `buildHtml`:
```js
const html = buildHtml(surfaces, { generatedAt: ..., surfaceCount: ..., errCatalog });
```

### 3. `html-shell.mjs` changes

a. Accept `errCatalog` in options; emit as inline JS const before SURFACES:
```js
`const ERR_CATALOG = ${JSON.stringify(errCatalog ?? {})};\n` +
`const SURFACES = ${surfacesJson};\n\n${clientJs}`
```

b. Add States subtab button in HTML markup (after existing Blueprint subtab):
```html
<button class="subtab" data-view="states" title="Surface states and error references">States</button>
```

c. Add `<div id="view-states" style="display:none"></div>` inside `.surface-body` after `#view-blueprint`.

d. Add `"render-states.js"` to `buildClientScript` file list (after `render-regionbox.js`).

### 4. New `client/render-states.js`

```js
// render-states.js — render States subtab content for current surface.
// Globals: currentSurface, ERR_CATALOG, esc, escAttr

function renderStates(surface) {
  const states = surface.states || [];
  if (!states.length)
    return '<p class="states-empty">No ST-* states defined for this surface.</p>';

  return states.map(st => {
    const errChips = st.errRefs.map(e => {
      const desc = ERR_CATALOG[e];
      return desc
        ? `<span class="err-chip known" title="${escAttr(desc)}">${esc(e)}</span>`
        : `<span class="err-chip unknown" title="(not in catalog)">${esc(e)}</span>`;
    }).join("");
    return `
      <div class="state-card">
        <div class="state-header">
          <span class="state-id">${esc(st.id)}</span>
          <span class="state-label">${esc(st.label)}</span>
        </div>
        ${st.description ? `<p class="state-desc">${esc(st.description)}</p>` : ""}
        ${errChips ? `<div class="state-err-refs">${errChips}</div>` : ""}
      </div>`;
  }).join("\n");
}
```

### 5. Wire States view in `app-chrome.js` — `switchView`

Add `"states"` to the views array:
```js
for (const v of ["layout", "blueprint", "storyboard", "states", "graph"])
  document.getElementById("view-" + v)?.style && (document.getElementById("view-" + v).style.display = v === view ? "block" : "none");
```

Also extend `isSurfaceView` check: `const isSurfaceView = ["layout","blueprint","states"].includes(view);`

### 6. Wire render call in `app.js` — `renderMain`

```js
document.getElementById("view-states").innerHTML = renderStates(s);
```
Add after `renderLayout` call.

### 7. CSS — `styles.mjs`

```css
.state-card { border:1px solid #1e293b; border-radius:8px; padding:12px 16px; margin-bottom:10px; }
.state-header { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
.state-id { font-family:monospace; font-size:11px; background:#1e293b; padding:2px 6px; border-radius:4px; color:#94a3b8; }
.state-label { font-weight:600; font-size:13px; color:#e2e8f0; }
.state-desc { font-size:12px; color:#94a3b8; margin:4px 0 8px; }
.state-err-refs { display:flex; flex-wrap:wrap; gap:6px; }
.err-chip { font-size:11px; padding:2px 7px; border-radius:10px; cursor:default; }
.err-chip.known   { background:#1e3a5f; color:#60a5fa; }
.err-chip.unknown { background:#431407; color:#fb923c; }
.states-empty { color:#64748b; font-size:13px; padding:24px; text-align:center; }
```

## Validation
1. S14 States subtab: shows ST-* entries matching `## States` prose section.
2. ERR-* chips: known refs show blue with tooltip text from catalog; unknown refs show orange.
3. Surface with no states (e.g. a simple modal): shows empty-state message without crash.
4. Switching between Interactions / Blueprint / States tabs: no content bleed-through.
5. `verify-runtime.mjs`: click States subtab → no JS error in console.

## Risks & rollback
- **Risk:** `## States` heading absent or spelled differently (e.g. `## State`) — regex uses `States?` to handle both; prose-section boundary detection relies on next `##` heading.
- **Risk:** `switchView` currently hardcodes view id list in `app-chrome.js` — must extend to include `"states"` or `getElementById("view-states")` returns null and `.style` throws.
- **Risk:** `errCatalog` injected into HTML may be large if catalog is long — spot-check file size; truncate description to first sentence (already done via `.split("\n")[0]`).
- **Rollback:** remove `render-states.js` from inline list + remove States subtab button + remove `states` field from surface objects. Zero impact on existing tabs.

# Phase 06 — CSS Grid Renderer

## Context links
- `tools/wireframe/client/render-regionbox.js` (123 lines) — `renderLayout(surface)` → HTML; `buildRegionBoxes(surface)` + `regionBoxHtml` logic (not yet a named export — must extract); `actionBtnHtml`, `listenerChipHtml`
- `tools/wireframe/client/app.js` — `renderMain()` calls `renderLayout(s)` → `#view-layout`
- `tools/wireframe/extract-layout.mjs` (phase 05) — `layoutAreaNames(model)`, `nonRectRegions(model)`
- `tools/wireframe/html-shell.mjs` — inline file list in `buildClientScript`
- `tools/wireframe/styles.mjs` — CSS
- Phase 05 prerequisite: `surface.layout` object populated in surface JSON

## Requirements
1. Surfaces with `surface.layout` → render as CSS grid (spatial); surfaces without → existing stacked region-boxes (no regression).
2. Grid cells = region box + sample content line when `samples[region]` present.
3. Floating regions rendered as toggle-able banner strips below grid; button cycles show/hide.
4. Named variants (e.g. `full_screen`) rendered via a variant switcher button row; switching prepends rows to grid.
5. Clicking a grid cell region box still wires action buttons the same as stacked view.

## Files to modify / create

| File | Change |
|---|---|
| `tools/wireframe/client/render-regionbox.js` | Extract `regionBoxHtml(surface, region, opts)` as reusable function (DRY) |
| `tools/wireframe/client/render-grid.js` | New — CSS grid container from layout model |
| `tools/wireframe/client/app.js` | `renderMain`: prefer `renderGrid` when `surface.layout` present |
| `tools/wireframe/html-shell.mjs` | Add `"render-grid.js"` to inline list (after `render-regionbox.js`) |
| `tools/wireframe/styles.mjs` | Grid container + cell + sample + floating banner + variant switcher styles |

## Implementation steps

### 1. Extract `regionBoxHtml` in `render-regionbox.js`

Current `renderLayout` iterates regions and builds box HTML inline. Refactor:

```js
/**
 * Render one region box (header + action list).
 * @param {object} surface  - full surface object
 * @param {string} region   - region name
 * @param {object} [opts]   - { sampleText: string|null }
 * @returns {string} HTML
 */
function regionBoxHtml(surface, region, opts = {}) {
  // Extract existing per-region rendering logic from renderLayout into here.
  // opts.sampleText: if truthy, append <div class="sample-content">{sampleText}</div>
  const interactions = interactionsOf(surface, region); // from region-model.js
  const sample = opts.sampleText
    ? `<div class="sample-content">${esc(opts.sampleText)}</div>` : "";
  // ... existing header + action list HTML ...
  return `<div class="region-box" data-region="${escAttr(region)}">
    <h3 class="region-title" data-region="${escAttr(region)}">${esc(region)}</h3>
    ${sample}
    <div class="action-list">${interactions.map(it => actionBtnHtml(it)).join("")}</div>
  </div>`;
}
```

Update `renderLayout` to call `regionBoxHtml` per region (behavior unchanged for stacked view).

### 2. New `client/render-grid.js`

```js
// render-grid.js — CSS grid renderer for surfaces with ui-layout model.
// Globals: esc, escAttr, regionBoxHtml (render-regionbox.js), currentSurface

/** Build CSS grid-template-areas string from areas matrix. */
function areasCSS(areas) {
  return areas.map(row => `"${row.join(" ")}"`).join(" ");
}

/** Build grid-template-columns CSS value from columns array. */
function columnsCSS(columns) {
  return (columns || []).map(() => "1fr").join(" "); // default equal-width
  // If columns is string[]: return columns.join(" ");
}

/**
 * Render the full grid view for a surface.
 * @param {object} surface
 * @param {string} [activeVariant]  - variant key to apply (default: none)
 */
function renderGrid(surface, activeVariant) {
  const layout = surface.layout;
  if (!layout) return renderLayout(surface); // fallback

  const model = activeVariant && layout.variants?.[activeVariant]
    ? { ...layout, areas: [...(layout.variants[activeVariant].prepend_rows || []), ...layout.areas] }
    : layout;

  const columns = columnsCSS(layout.columns);
  const areas   = areasCSS(model.areas);
  const samples = layout.samples || {};

  // Unique region names (preserving order of first appearance)
  const seen = new Set();
  const regions = [];
  for (const row of model.areas) for (const cell of row) {
    if (!seen.has(cell)) { seen.add(cell); regions.push(cell); }
  }

  const cells = regions.map(r =>
    `<div class="grid-cell" style="grid-area:${CSS.escape(r)}">
      ${regionBoxHtml(surface, r, { sampleText: samples[r] || null })}
    </div>`
  ).join("\n");

  // Floating regions
  const floatingBanners = (layout.floating || []).map(f =>
    `<div class="floating-banner" id="floating-${escAttr(f.region)}" style="display:none">
      ${regionBoxHtml(surface, f.region, { sampleText: samples[f.region] || null })}
    </div>
    <button class="floating-toggle" onclick="toggleFloating('${escAttr(f.region)}')">
      Show ${esc(f.region)} (STOP variant)
    </button>`
  ).join("\n");

  // Variant switcher
  const variantKeys = Object.keys(layout.variants || {});
  const variantSwitcher = variantKeys.length
    ? `<div class="variant-switcher">
        <span>Variant:</span>
        <button class="variant-btn ${!activeVariant ? "active" : ""}"
          onclick="switchGridVariant(null)">default</button>
        ${variantKeys.map(k =>
          `<button class="variant-btn ${activeVariant === k ? "active" : ""}"
            onclick="switchGridVariant('${escAttr(k)}')">${esc(k)}</button>`
        ).join("")}
      </div>` : "";

  return `
    ${variantSwitcher}
    <div class="grid-container"
         style="display:grid;grid-template-columns:${columns};grid-template-areas:${areas};gap:10px">
      ${cells}
    </div>
    ${floatingBanners}`;
}

/** Toggle a floating region banner. */
function toggleFloating(regionName) {
  const el = document.getElementById("floating-" + regionName);
  if (el) el.style.display = el.style.display === "none" ? "block" : "none";
}

/** Re-render grid with a new variant. */
function switchGridVariant(variantKey) {
  document.getElementById("view-layout").innerHTML = renderGrid(currentSurface, variantKey);
  rewireActionButtons(document.getElementById("view-layout"));
}
```

**`rewireActionButtons(root)`** — extract from `renderMain` the querySelector + addEventListener loop into a helper so both `renderMain` and `switchGridVariant` can call it.

### 3. `app.js` — `renderMain` grid preference

```js
// In renderMain(), replace:
document.getElementById("view-layout").innerHTML = renderLayout(s);
// With:
document.getElementById("view-layout").innerHTML =
  s.layout ? renderGrid(s) : renderLayout(s);
```

Then call `rewireActionButtons(document.getElementById("view-layout"))`.

### 4. `html-shell.mjs` — inline order

```js
const files = [
  "region-model.js",
  "render-regionbox.js",
  "render-grid.js",        // ← new; after render-regionbox so regionBoxHtml is defined
  "blueprint-link.js",     // phase 03
  "render-states.js",      // phase 04
  "render-storyboard.js",
  "render-graph.js",
  "app-chrome.js",
  "graph-controls.js",
  "flow-play.js",
  "app.js",
];
```

### 5. CSS — `styles.mjs`

```css
/* Grid renderer */
.grid-container { padding:12px; }
.grid-cell { min-width:0; }         /* prevent overflow in narrow columns */
.sample-content {
  font-size:11px; color:#64748b; font-style:italic;
  padding:2px 8px 6px; border-left:2px solid #1e293b; margin:4px 0 6px;
}
.floating-banner { border:1px dashed #f59e0b; border-radius:6px; padding:8px; margin:8px 0; }
.floating-toggle {
  font-size:11px; padding:3px 10px; background:#1e293b; border:1px solid #f59e0b;
  color:#f59e0b; border-radius:4px; cursor:pointer; margin:4px 0;
}
.variant-switcher { display:flex; align-items:center; gap:6px; margin-bottom:8px; font-size:12px; color:#94a3b8; }
.variant-btn { font-size:11px; padding:3px 10px; background:#1e293b; border:1px solid #334155; border-radius:4px; cursor:pointer; color:#94a3b8; }
.variant-btn.active { border-color:#60a5fa; color:#60a5fa; }
```

## Validation
1. S14 (has `ui-layout` after phase 05 pilot): renders LEFT + RIGHT two-column grid; `reason_to_call` spans both rows as per areas matrix.
2. `samples` line appears in cell as italic grey text.
3. Floating region toggle button shows/hides banner.
4. Variant switcher (if S14 has `full_screen`): switching adds prepend rows; switching back restores default.
5. Surface without `layout` (e.g. any unmodified S01): still renders stacked region-boxes unchanged.
6. Action buttons in grid cells fire navigation / overlay same as stacked view.
7. `verify-runtime.mjs` green.

## Risks & rollback
- **Risk:** `CSS.escape` used in `grid-area` style — region names with dots (e.g. `sidebar.core_info`) are invalid CSS ident; replace dots with underscores when emitting `grid-area` values and `grid-template-areas` cells. Map: `r.replace(/\./g, "_")`.
- **Risk:** `regionBoxHtml` refactor may break stacked `renderLayout` if interaction filtering by region differs — run stacked-view regression on S14 before merging.
- **Risk:** `rewireActionButtons` must also wire `.listener-chip` clicks (currently done in `renderMain`) — include both selectors.
- **Rollback:** restore `renderLayout(s)` call in `renderMain`; remove `render-grid.js` from inline list. Zero impact on stacked view.

// wireframe/html-shell.mjs
// NODE: buildHtml(surfaces) → full self-contained HTML string.
// Embeds SURFACES JSON + inlines all client/*.js in correct dependency order.
// CSS imported from styles.mjs (split to keep this file < 200 lines).
// Resolves client file paths via import.meta.url (Windows-safe, no __dirname).
// Cytoscape UMD bundle inlined BEFORE client modules so global `cytoscape` exists.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { CSS } from "./styles.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));

/** Read a client JS file relative to this module's directory. */
function readClient(filename) {
  const url = new URL("./client/" + filename, import.meta.url);
  return readFileSync(fileURLToPath(url), "utf8");
}

/**
 * Read layout-schema.mjs (single-writer schema module, one dir up from client/)
 * and strip `export ` prefixes so it runs as a plain browser script. The module
 * is import-free and top-level-export-only by contract (see its header comment).
 */
function readLayoutSchemaForBrowser() {
  const url = new URL("./layout-schema.mjs", import.meta.url);
  return readFileSync(fileURLToPath(url), "utf8").replace(/^export (?=(const|function|let|class)\b)/gm, "");
}

/** Read a node_modules bundle (path relative to tools/node_modules). */
function readNodeBundle(relPath) {
  return readFileSync(join(__dir, "..", "node_modules", relPath), "utf8");
}

/** Inline all client modules + cytoscape bundle into one <script> block. */
function buildClientScript(surfacesJson, errCatalogJson) {
  // graph-layout.js excluded — Cytoscape does layout now; no module references layeredLayout.
  const files = [
    "region-model.js",      // esc, escAttr, isReaction, interactionsOf, edgeById, narrate
    "render-regionbox.js",  // renderLayout, renderMini, regionBoxHtml, actionBtnHtml, listenerChipHtml
    "render-content.js",    // contentElementHtml, renderContentElements (content: model)
    "render-grid.js",       // renderGrid, rewireActionButtons, toggleFloating, switchGridVariant (Phase 6)
    "blueprint-link.js",    // initBlueprintLinks, flashRegionBox, flashBlueprintSpan (Phase 3 plan)
    "render-storyboard.js", // renderStoryboard (Phase 2)
    "render-graph.js",      // buildGraph, renderGraph → Cytoscape elements (Phase 3)
    "render-states.js",     // renderStates — States subtab (Phase 4)
    "app-chrome.js",        // sidebar, breadcrumb, bottombar, switchView
    "graph-controls.js",    // graphState, renderAndInsertGraph, initGraphControls (Phase 3)
    "flow-play.js",         // flow play 2.0: timer, highlight, narration
    "app.js",               // state, nav, overlay, interaction handler, init
  ];
  // layout-schema.mjs first: single-writer schema globals (CONTENT_TYPES, walkers)
  // must exist before render modules parse.
  const clientJs = [readLayoutSchemaForBrowser(), ...files.map(readClient)].join("\n\n");

  // Cytoscape + cytoscape-dagre (bundles dagre) — UMD globals, then register the ext.
  const cytoscapeBundle = readNodeBundle("cytoscape/dist/cytoscape.min.js");
  const dagreExtBundle  = readNodeBundle("cytoscape-dagre/dist/cytoscape-dagre.min.js");

  return (
    `<script>\n/* cytoscape + cytoscape-dagre — inlined UMD */\n${cytoscapeBundle}\n${dagreExtBundle}\n` +
    `try{ if (window.cytoscape && window.cytoscapeDagre) cytoscape.use(cytoscapeDagre); }catch(e){ console.warn("dagre ext", e); }\n</script>\n` +
    `<script>\nconst ERR_CATALOG = ${errCatalogJson};\nconst SURFACES = ${surfacesJson};\n\n${clientJs}\n</script>`
  );
}

/**
 * Format current time as "YYYY-MM-DD HH:mm" in Asia/Ho_Chi_Minh (ICT, UTC+7).
 * Uses Intl.DateTimeFormat.formatToParts for locale-independent extraction.
 */
function ictTimestamp() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
    hour12: false,
  }).formatToParts(new Date());
  const p = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}`;
}

/**
 * Build the complete self-contained HTML string.
 * @param {object[]} surfaces - enriched surface data array
 * @param {{ errCatalog?: Record<string,string> }} opts
 * @returns {string}
 */
export function buildHtml(surfaces, opts = {}) {
  const { errCatalog = {} } = opts;
  const surfacesJson  = JSON.stringify(surfaces, null, 2);
  const errCatalogJson = JSON.stringify(errCatalog);
  const script = buildClientScript(surfacesJson, errCatalogJson);

  // Freshness stamp shown in the bottom bar area — computed at generation time.
  const freshnessStamp = `Generated ${ictTimestamp()} ICT · ${surfaces.length} surfaces`;

  return `<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ui-spec · wireframe v2</title>
<style>${CSS}</style>
</head>
<body>

<div id="topbar">
  <h1>ui-spec · wireframe</h1>
  <button id="btn-back" disabled>← Back</button>
  <div id="breadcrumb"></div>
  <div class="tabs">
    <button class="tab active" data-view="layout" title="The selected surface">Surface</button>
    <button class="tab" data-view="storyboard" title="A user flow as a storyboard">Storyboard</button>
    <button class="tab" data-view="graph" title="App-wide navigation graph">Graph</button>
  </div>
  <div id="topbar-right">
    <!-- Flow bar: select + play/stop controls -->
    <div id="flow-bar">
      <select id="flow-select" title="Select a flow"></select>
      <button id="btn-flow-play" class="icon-btn" title="Play flow step-by-step">▶</button>
      <button id="btn-flow-stop" class="icon-btn" disabled title="Stop flow playback">■</button>
    </div>
    <button class="icon-btn" id="btn-toggle-sidebar" title="Toggle sidebar">☰</button>
  </div>
</div>

<!-- Graph toolbar: shown only when Graph tab is active (display toggled by switchView) -->
<div id="graph-toolbar" style="display:none">
  <label title="Reaction = điều hướng do listener / system event kích hoạt, không phải user click trực tiếp">
    <input type="checkbox" id="graph-reaction-toggle"> Show reaction edges
  </label>
  <select id="graph-flow-select" title="Highlight a flow path through the graph"></select>
  <label title="Graph layout algorithm">Layout
    <select id="graph-layout-select">
      <option value="dagre" selected>dagre (layered)</option>
      <option value="breadthfirst">breadthfirst</option>
    </select>
  </label>
  <div class="graph-legend">
    <span class="graph-legend-item"><span class="graph-leg-line graph-leg-solid"></span> navigate</span>
    <span class="graph-legend-item"><span class="graph-leg-line graph-leg-dash"></span> open_overlay</span>
    <span class="graph-legend-item"><span class="graph-leg-line graph-leg-dot"></span> reaction</span>
    <span class="graph-legend-item"><span class="graph-leg-line graph-leg-hl"></span> flow path</span>
  </div>
  <span class="graph-hint" title="Pan/zoom/drag nodes freely — click a node to open its Layout view">
    Pan · Zoom · Drag · Click node to inspect
  </span>
</div>

<!-- Narration banner: shown during flow play, hidden otherwise -->
<div id="narration-banner" class="hidden">
  <span class="nb-step"></span>
  <span class="nb-text"></span>
  <button class="nb-close" onclick="flowStop()" title="Stop playback">✕</button>
</div>

<div id="layout">
  <div id="sidebar">
    <div id="sidebar-header">
      <span>Surfaces</span>
      <button id="btn-collapse" title="Collapse">‹</button>
    </div>
    <div id="sidebar-content"></div>
  </div>

  <div id="main">
    <!-- Graph view: Cytoscape canvas, hidden unless Graph tab active -->
    <div id="view-graph"></div>
    <div id="surface-wrap">
      <div class="surface-card">
        <div class="surface-header">
          <span class="surface-id" id="surface-id">—</span>
          <span class="surface-name" id="surface-name">—</span>
          <span class="type-badge" id="surface-type-badge">—</span>
          <span class="region-chips" id="surface-region-chips"></span>
        </div>
        <!-- Surface sub-tabs: views of the SAME surface -->
        <div id="surface-subtabs">
          <!-- Layout subtab (Phase 6): spatial CSS grid — shown only for surfaces with ui-layout model -->
          <button class="subtab" id="subtab-grid" data-view="grid" style="display:none" title="Spatial CSS grid layout — stakeholder view">Layout</button>
          <button class="subtab active" data-view="layout" title="Interactions grouped by region">Interactions</button>
          <button class="subtab" data-view="blueprint" title="Original hand-authored ASCII layout">Blueprint</button>
          <button class="subtab" data-view="states" title="Surface states and error references">States</button>
        </div>
        <div class="surface-body">
          <div class="surface-errors" id="surface-errors" style="display:none"></div>
          <!-- Grid view (Phase 6): CSS grid for surfaces with ui-layout model -->
          <div id="view-grid" style="display:none"></div>
          <div id="view-layout"></div>
          <div id="view-blueprint" style="display:none">
            <div class="blueprint-note">Bản ASCII gốc (hand-authored) — tham chiếu bố cục 2D.</div>
            <pre id="blueprint-pre"></pre>
          </div>
          <!-- Storyboard filmstrip view (Phase 2) -->
          <div id="view-storyboard" style="display:none"></div>
          <!-- States subtab (Phase 4) -->
          <div id="view-states" style="display:none"></div>
        </div>
      </div>

      <!-- Filled at init by app.js from legendHtml() (single source in render-grid.js).
           Hidden on the grid subtab — there the legend lives in the right rail. -->
      <div class="legend" id="page-legend"></div>
    </div>
    <div id="bottombar"></div>
    <div id="gen-stamp" style="font-size:11px;color:#94a3b8;padding:2px 12px 4px;text-align:right;border-top:1px solid #e2e8f0;">${freshnessStamp}</div>
  </div>
</div>

<div id="overlay-backdrop" class="hidden">
  <div id="overlay-card"></div>
</div>

<div id="toast"></div>

${script}
</body>
</html>`;
}

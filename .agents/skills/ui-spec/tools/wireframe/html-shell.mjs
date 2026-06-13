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

/** Read a node_modules bundle (path relative to tools/node_modules). */
function readNodeBundle(relPath) {
  return readFileSync(join(__dir, "..", "node_modules", relPath), "utf8");
}

/** Inline all client modules + cytoscape bundle into one <script> block. */
function buildClientScript(surfacesJson) {
  // graph-layout.js excluded — Cytoscape does layout now; no module references layeredLayout.
  const files = [
    "region-model.js",      // esc, escAttr, isReaction, interactionsOf, edgeById, narrate
    "render-regionbox.js",  // renderLayout, renderMini, actionBtnHtml, listenerChipHtml
    "render-storyboard.js", // renderStoryboard (Phase 2)
    "render-graph.js",      // buildGraph, renderGraph → Cytoscape elements (Phase 3)
    "app-chrome.js",        // sidebar, breadcrumb, bottombar, switchView
    "graph-controls.js",    // graphState, renderAndInsertGraph, initGraphControls (Phase 3)
    "flow-play.js",         // flow play 2.0: timer, highlight, narration
    "app.js",               // state, nav, overlay, interaction handler, init
  ];
  const clientJs = files.map(readClient).join("\n\n");

  // Cytoscape + cytoscape-dagre (bundles dagre) — UMD globals, then register the ext.
  const cytoscapeBundle = readNodeBundle("cytoscape/dist/cytoscape.min.js");
  const dagreExtBundle  = readNodeBundle("cytoscape-dagre/dist/cytoscape-dagre.min.js");

  return (
    `<script>\n/* cytoscape + cytoscape-dagre — inlined UMD */\n${cytoscapeBundle}\n${dagreExtBundle}\n` +
    `try{ if (window.cytoscape && window.cytoscapeDagre) cytoscape.use(cytoscapeDagre); }catch(e){ console.warn("dagre ext", e); }\n</script>\n` +
    `<script>\nconst SURFACES = ${surfacesJson};\n\n${clientJs}\n</script>`
  );
}

/**
 * Build the complete self-contained HTML string.
 * @param {object[]} surfaces - enriched surface data array
 * @returns {string}
 */
export function buildHtml(surfaces) {
  const surfacesJson = JSON.stringify(surfaces, null, 2);
  const script = buildClientScript(surfacesJson);

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
        <!-- Surface sub-tabs: two representations of the SAME surface -->
        <div id="surface-subtabs">
          <button class="subtab active" data-view="layout" title="Interactions grouped by region">Interactions</button>
          <button class="subtab" data-view="blueprint" title="Original hand-authored ASCII layout">Blueprint</button>
        </div>
        <div class="surface-body">
          <div class="surface-errors" id="surface-errors" style="display:none"></div>
          <div id="view-layout"></div>
          <div id="view-blueprint" style="display:none">
            <div class="blueprint-note">Bản ASCII gốc (hand-authored) — tham chiếu bố cục 2D.</div>
            <pre id="blueprint-pre"></pre>
          </div>
          <!-- Storyboard filmstrip view (Phase 2) -->
          <div id="view-storyboard" style="display:none"></div>
        </div>
      </div>

      <div class="legend">
        <h4>Chú thích</h4>
        <div class="legend-row">
          <span class="legend-item"><span class="swatch" style="background:#dbeafe"></span> navigate</span>
          <span class="legend-item"><span class="swatch" style="background:#ede9fe"></span> open_overlay</span>
          <span class="legend-item"><span class="swatch" style="background:#ffedd5"></span> mutate</span>
          <span class="legend-item"><span class="swatch" style="background:#dcfce7"></span> emit_event</span>
          <span class="legend-item"><span class="swatch" style="background:#fee2e2"></span> close_overlay</span>
          <span class="legend-item"><span class="swatch" style="border:1px dashed #94a3b8;background:#f3f4f6"></span> ⚡ reaction</span>
        </div>
      </div>
    </div>
    <div id="bottombar"></div>
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

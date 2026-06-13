// wireframe/styles-phase3.mjs
// NODE: Phase 3 CSS additions — Cytoscape graph container, toolbar, legend.
// Old SVG edge/node CSS removed (now handled by Cytoscape stylesheet in render-graph.js).
// Concatenated by styles.mjs into the final CSS export.

export const CSS3 = `
/* ── Phase 3: Graph view container ─────────────────────────────────────────── */
/* #view-graph must have an explicit pixel height for Cytoscape to render.      */
/* It sits in #main (flex-column); give it flex:1 + min-height so it fills      */
/* the available space between topbar+toolbar and bottombar.                    */
#view-graph {
  display: none;
  flex: 1;
  min-height: 400px;
  width: 100%;
  background: #f8fafc;
  /* Cytoscape mounts a <canvas> directly inside — no overflow:auto needed */
}

/* ── Phase 3: Graph toolbar ─────────────────────────────────────────────────── */
#graph-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 7px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 12px;
  color: #475569;
  flex-shrink: 0;
  flex-wrap: wrap;
}
#graph-toolbar label { display: flex; align-items: center; gap: 5px; cursor: pointer; }
#graph-toolbar input[type=checkbox] { cursor: pointer; }

#graph-flow-select, #graph-layout-select {
  background: #334155;
  border: 1px solid #475569;
  color: #cbd5e1;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 11px;
  max-width: 200px;
  cursor: pointer;
}
#graph-flow-select:focus, #graph-layout-select:focus { outline: 2px solid #2563eb; }

.graph-hint {
  font-size: 11px;
  color: #94a3b8;
  font-style: italic;
  margin-left: auto;
}

/* ── Phase 3: Graph legend row ───────────────────────────────────────────────── */
.graph-legend { display: flex; gap: 14px; align-items: center; flex-wrap: wrap;
                font-size: 11px; color: #64748b; }
.graph-legend-item { display: flex; align-items: center; gap: 5px; }
.graph-leg-line { display: inline-block; width: 24px; height: 2px; border-radius: 1px; }
.graph-leg-solid { background: #2563eb; }
.graph-leg-dash  { background: repeating-linear-gradient(90deg,#7c3aed 0 4px,transparent 4px 8px); }
.graph-leg-dot   { background: repeating-linear-gradient(90deg,#94a3b8 0 2px,transparent 2px 5px); }
.graph-leg-hl    { background: #f59e0b; }
`;

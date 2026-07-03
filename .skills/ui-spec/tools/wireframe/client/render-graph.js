// wireframe/client/render-graph.js
// BROWSER: App-wide navigation graph — Cytoscape element + stylesheet builder.
// Replaces old SVG renderer. Returns { elements, style, flowPath, nodeCount }.
// Depends on: region-model.js (SURFACES, surfaceById, interactionsOf, isReaction, edgeById)

// ── Type palette (mirrors badge CSS) ─────────────────────────────────────────
const TYPE_FILL   = { screen:"#dbeafe", modal:"#e5e7eb", panel:"#d1fae5",
                      overlay:"#fef3c7", component:"#ede9fe", flow:"#fce7f3" };
const TYPE_TEXT   = { screen:"#1d4ed8", modal:"#374151", panel:"#065f46",
                      overlay:"#92400e", component:"#5b21b6", flow:"#9d174d" };
const TYPE_BORDER = { screen:"#93c5fd", modal:"#d1d5db", panel:"#6ee7b7",
                      overlay:"#fcd34d", component:"#c4b5fd", flow:"#f9a8d4" };

// ── buildGraph: collect Cytoscape elements ────────────────────────────────────
function buildGraph({ includeReactions = false } = {}) {
  const nodeSet = new Set();
  const edgeMap = {};
  for (const s of SURFACES) if (s.meta?.type === "screen") nodeSet.add(s.id);
  for (const s of SURFACES) {
    for (const ix of interactionsOf(s)) {
      if (ix.action !== "navigate" && ix.action !== "open_overlay") continue;
      if (!ix.target || !surfaceById[ix.target]) continue;
      const isReact = isReaction(ix);
      if (isReact && !includeReactions) continue;
      const key = s.id + "|" + ix.target + "|" + ix.action + "|" + isReact;
      if (!edgeMap[key]) edgeMap[key] = { from:s.id, to:ix.target, action:ix.action,
                                          isReaction:isReact, label:ix.element||ix.trigger||"" };
      nodeSet.add(s.id); nodeSet.add(ix.target);
    }
  }
  const elements = [];
  for (const id of nodeSet) {
    const s = surfaceById[id], type = s?.meta?.type || "unknown";
    const name = s?.meta?.name || s?.file || id;
    elements.push({ group:"nodes", data:{ id, surfaceType:type,
      label: id + "\n" + (name.length > 22 ? name.slice(0,21) + "…" : name),
      fill: TYPE_FILL[type]||"#f3f4f6", text: TYPE_TEXT[type]||"#374151",
      border: TYPE_BORDER[type]||"#cbd5e1" }});
  }
  let ei = 0;
  for (const e of Object.values(edgeMap))
    elements.push({ group:"edges", data:{ id:"e"+(ei++), source:e.from, target:e.to,
                                          action:e.action, isReaction:e.isReaction, label:e.label }});
  return { elements, nodeSet };
}

// ── flowSurfacePath ───────────────────────────────────────────────────────────
function flowSurfacePath(flowId) {
  const surface = surfaceById[flowId];
  if (!surface?.contract?.flow?.steps?.length) return [];
  const raw = surface.contract.flow.steps.map(sid => edgeById(sid)?.from).filter(Boolean);
  return raw.filter((id, i) => i === 0 || id !== raw[i-1]);
}

// ── Cytoscape stylesheet ──────────────────────────────────────────────────────
function buildCyStyle() {
  return [
    { selector:"node", style:{
      "background-color":"data(fill)", "border-color":"data(border)", "border-width":1.5,
      "color":"data(text)", "label":"data(label)", "text-valign":"center", "text-halign":"center",
      "font-family":"ui-monospace,monospace", "font-size":"11px",
      "text-wrap":"wrap", "text-max-width":"140px",
      "width":160, "height":56, "shape":"round-rectangle", "cursor":"pointer",
      "transition-property":"border-color border-width", "transition-duration":"0.15s",
    }},
    { selector:"node:hover",            style:{ "border-color":"#2563eb", "border-width":2.5 }},
    { selector:"node.highlighted",      style:{ "border-color":"#f59e0b", "border-width":3, "background-color":"#fffbeb" }},
    { selector:"node.dimmed",           style:{ "opacity":0.3 }},
    { selector:"node.neighbor-highlighted", style:{ "border-color":"#60a5fa", "border-width":2 }},
    { selector:"edge", style:{
      "width":1.5, "target-arrow-shape":"triangle",
      // bezier so parallel edges bow apart (taxi caused overlapping merged lines)
      "curve-style":"bezier", "control-point-step-size":50,
      "arrow-scale":1.1, "opacity":0.9,
      // edge label = triggering element; white pill background for legibility over lines
      "label":"data(label)", "font-size":"9px", "font-family":"ui-monospace,monospace",
      "color":"#475569", "text-rotation":"autorotate", "text-margin-y":-6,
      "text-background-color":"#ffffff", "text-background-opacity":0.85,
      "text-background-padding":2, "text-background-shape":"roundrectangle",
      "text-opacity":0,  // hidden by default — revealed on node hover / flow highlight
    }},
    { selector:"edge[action='navigate']",    style:{ "line-color":"#2563eb", "target-arrow-color":"#2563eb", "line-style":"solid" }},
    { selector:"edge[action='open_overlay']",style:{ "line-color":"#7c3aed", "target-arrow-color":"#7c3aed", "line-style":"dashed", "line-dash-pattern":[6,4] }},
    { selector:"edge[?isReaction]",          style:{ "line-color":"#94a3b8", "target-arrow-color":"#94a3b8", "line-style":"dotted", "opacity":0.65 }},
    { selector:"edge.highlighted",           style:{ "line-color":"#f59e0b", "target-arrow-color":"#f59e0b", "width":3, "opacity":1, "z-index":10, "text-opacity":1 }},
    { selector:"edge.dimmed",                style:{ "opacity":0.15 }},
    { selector:"edge.neighbor-highlighted",  style:{ "line-color":"#93c5fd", "target-arrow-color":"#93c5fd", "width":2, "text-opacity":1 }},
  ];
}

// ── Layout presets ────────────────────────────────────────────────────────────
function graphLayoutConfig(name) {
  const common = { padding: 40, animate: false, fit: true };
  switch (name) {
    case "dagre":
      return { name:"dagre", ...common, rankDir:"TB", nodeSep:50, rankSep:78,
               edgeSep:14, ranker:"network-simplex", acyclicer:"greedy" };
    default: // breadthfirst
      return { name:"breadthfirst", ...common, directed:true,
               spacingFactor:1.4, avoidOverlap:true };
  }
}

// ── Public API ────────────────────────────────────────────────────────────────
/**
 * Build Cytoscape elements + stylesheet for the navigation graph.
 * Called by graph-controls.js renderAndInsertGraph().
 * @param {{ includeReactions?: boolean, highlightFlowId?: string }} opts
 * @returns {{ elements, style, flowPath, nodeCount }}
 */
function renderGraph({ includeReactions = false, highlightFlowId = "" } = {}) {
  const { elements, nodeSet } = buildGraph({ includeReactions });
  return { elements, style: buildCyStyle(),
           flowPath: highlightFlowId ? flowSurfacePath(highlightFlowId) : [],
           nodeCount: nodeSet.size };
}

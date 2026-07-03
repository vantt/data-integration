// wireframe/client/graph-layout.js
// BROWSER: Layered-BFS layout for the navigation node graph.
// Pure function — no DOM access. Consumed by render-graph.js.
// Accepted limitation (documented): same-layer / self-loop / back edges may overlap visually;
//   no auto-routing is performed by design (YAGNI — no physics lib).

const COL_W = 230; // horizontal distance between layers (px)
const ROW_H = 100; // vertical distance between nodes in same layer (px)
const PAD_X = 40;  // left/right padding inside the SVG canvas
const PAD_Y = 50;  // top/bottom padding inside the SVG canvas
const NODE_W = 160; // node rectangle width
const NODE_H = 56;  // node rectangle height

/**
 * BFS-based layered layout.
 * Entry nodes = type==='screen' AND no incoming navigate/open_overlay edge.
 * Falls back to all screen nodes, then to [nodes[0]].
 *
 * @param {string[]} nodeIds  - ordered list of all node surface IDs to place
 * @param {{ from:string, to:string, action:string }[]} edges
 * @param {{ [id:string]: object }} surfaceById  - for meta.type lookup
 * @returns {{ pos:{ [id:string]:{x:number,y:number} }, svgW:number, svgH:number, NODE_W:number, NODE_H:number }}
 */
function layeredLayout(nodeIds, edges, surfaceById) {
  // Count incoming navigate/open_overlay edges per node
  const incoming = {};
  for (const id of nodeIds) incoming[id] = 0;
  for (const e of edges) {
    if (e.to && incoming[e.to] !== undefined) incoming[e.to]++;
  }

  // Adjacency list (navigate + open_overlay only, not reactions) for BFS
  const adj = {};
  for (const id of nodeIds) adj[id] = [];
  for (const e of edges) {
    if (adj[e.from]) adj[e.from].push(e.to);
  }

  // Choose entries: screens with no incoming nav edge
  let entries = nodeIds.filter(id => {
    const t = surfaceById[id]?.meta?.type;
    return t === "screen" && incoming[id] === 0;
  });
  // Fallback 1: all screen nodes
  if (!entries.length) entries = nodeIds.filter(id => surfaceById[id]?.meta?.type === "screen");
  // Fallback 2: first node
  if (!entries.length && nodeIds.length) entries = [nodeIds[0]];

  // BFS — assign shortest hop layer
  const layer = {};
  const queue = [];
  for (const id of entries) { layer[id] = 0; queue.push(id); }
  let qi = 0;
  while (qi < queue.length) {
    const cur = queue[qi++];
    for (const nb of (adj[cur] || [])) {
      if (layer[nb] === undefined) {
        layer[nb] = layer[cur] + 1;
        queue.push(nb);
      }
    }
  }

  // Unreached nodes go to maxLayer + 1
  const maxReached = Object.values(layer).reduce((m, v) => Math.max(m, v), 0);
  for (const id of nodeIds) {
    if (layer[id] === undefined) layer[id] = maxReached + 1;
  }

  // Group by layer, assign y positions
  const byLayer = {};
  for (const id of nodeIds) {
    const l = layer[id];
    if (!byLayer[l]) byLayer[l] = [];
    byLayer[l].push(id);
  }

  const pos = {};
  const layerKeys = Object.keys(byLayer).map(Number).sort((a, b) => a - b);
  for (const l of layerKeys) {
    const group = byLayer[l];
    for (let i = 0; i < group.length; i++) {
      pos[group[i]] = {
        x: PAD_X + l * COL_W,
        y: PAD_Y + i * ROW_H,
      };
    }
  }

  // Compute SVG bounds
  const maxLayer = layerKeys[layerKeys.length - 1] || 0;
  const maxStack = Math.max(...layerKeys.map(l => byLayer[l].length));
  const svgW = PAD_X * 2 + maxLayer * COL_W + NODE_W;
  const svgH = PAD_Y * 2 + (maxStack - 1) * ROW_H + NODE_H;

  return { pos, svgW, svgH, NODE_W, NODE_H };
}

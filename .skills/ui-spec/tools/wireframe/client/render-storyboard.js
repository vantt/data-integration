// wireframe/client/render-storyboard.js
// BROWSER: renderStoryboard(flowSurface) → filmstrip HTML.
// Phase 2 — replaces Phase 1 stub.
// Depends on: region-model.js (esc, escAttr, narrate, edgeById, actionDesc)
//             render-regionbox.js (renderMini)
//             app.js (surfaceById — available at call time; navigateTo wired by caller)

/**
 * Render a single storyboard card for one flow step.
 * Clicking the card navigates to the step's surface (wired by app.js via data-from).
 * @param {string} stepId - action id like A-S04-001
 * @param {number} idx - 0-based step index
 * @param {number} total - total step count
 * @returns {string} HTML card string
 */
function renderStepCard(stepId, idx, total) {
  const e = edgeById(stepId);
  const fromSurface = e && surfaceById[e.from];
  const caption = esc(narrate(stepId));

  // Mini region-box: highlight the region + element this step acts on
  const miniHtml = fromSurface
    ? renderMini(fromSurface, { highlightEl: e.id, highlightRegion: e.region })
    : `<div class="mini mini-unknown">(surface ${esc(e?.from || stepId)} not found)</div>`;

  const arrowHtml = idx < total - 1
    ? '<div class="sb-arrow" aria-hidden="true">↓</div>'
    : "";

  return `<div class="sb-step-wrap">
  <div class="sb-card" data-from="${escAttr(e?.from || "")}" title="${caption}">
    <div class="sb-step-num">Step ${idx + 1}</div>
    <div class="sb-mini">${miniHtml}</div>
    <div class="sb-cap">${caption}</div>
  </div>
  ${arrowHtml}
</div>`;
}

/**
 * Render branch annotations for a flow's alternate paths.
 * Displayed below the filmstrip as side-notes.
 * @param {Array<{when:string, action:string}>} branches
 * @returns {string} HTML
 */
function renderBranches(branches) {
  if (!branches || branches.length === 0) return "";
  const items = branches.map(b => {
    const e = edgeById(b.action);
    const narration = e ? actionDesc(e) : b.action;
    return `<div class="sb-branch-item">
  <span class="sb-branch-fork">⎇</span>
  <span class="sb-branch-when">${esc(b.when)}</span>
  <span class="sb-branch-arrow">→</span>
  <span class="sb-branch-action">${esc(narration)}</span>
  <span class="sb-branch-id">[${esc(b.action)}]</span>
</div>`;
  }).join("");
  return `<div class="sb-branches">
  <div class="sb-branches-label">Alt paths</div>
  ${items}
</div>`;
}

/**
 * Render the full storyboard filmstrip for a flow surface.
 * - Header: flow goal
 * - One card per step (per-step, NOT collapsed — even if same surface)
 * - Vertical scroll list with ↓ separators
 * - Branches row below the filmstrip
 * Card clicks wired by app.js after injection (data-from attr).
 * @param {object} flowSurface - surface with type==='flow' and contract.flow
 * @returns {string} HTML
 */
function renderStoryboard(flowSurface) {
  const flow = flowSurface?.contract?.flow;
  if (!flow) {
    return '<p class="sb-hint">No flow contract found for this surface.</p>';
  }
  const steps = flow.steps || [];
  const branches = flow.branches || [];
  const goal = flow.goal || "";
  const name = esc(flowSurface.meta?.name || flowSurface.id || "");

  if (steps.length === 0) {
    return `<div class="sb-header"><strong>${name}</strong>: ${esc(goal)}</div>
<p class="sb-hint">This flow has no steps defined.</p>`;
  }

  const cards = steps.map((stepId, i) => renderStepCard(stepId, i, steps.length)).join("");

  return `<div class="sb-header">
  <span class="sb-flow-name">${name}</span>
  <span class="sb-goal">${esc(goal)}</span>
</div>
<div class="sb-filmstrip" role="list">
  ${cards}
</div>
${renderBranches(branches)}`;
}

// wireframe/client/render-regionbox.js
// BROWSER: renderLayout(surface) + renderMini(surface, opts) → region-box HTML.
// Ported from mockup s01-regionbox-mockup.html lines 198-235.
// Depends on region-model.js (esc, escAttr, isReaction, actionDesc, regionOrder, groupByRegion).
// DRY: actionBtnHtml / listenerChipHtml are shared helpers used by both renderers.
// app.js wires click handlers; this module only produces markup.

// ── Shared atom renderers ─────────────────────────────────────────────────────

/**
 * Render an action button HTML string.
 * @param {object} ix - interaction
 * @param {string} surfaceId
 * @param {string} [activeId] - action id to highlight with active-el class
 * @returns {string}
 */
function actionBtnHtml(ix, surfaceId, activeId) {
  const cls = "btn-" + (ix.action || "default");
  const guardHtml = ix.guard
    ? `<span class="guard-pill" title="${escAttr(ix.guard)}">if</span>`
    : "";
  const activeCls = activeId && ix.id === activeId ? " active-el" : "";
  return `<button class="action-btn ${esc(cls)}${activeCls}"
  data-action="${escAttr(ix.action || "")}"
  data-target="${escAttr(ix.target || "")}"
  data-id="${escAttr(ix.id || "")}"
  data-surface="${escAttr(surfaceId || "")}"
  title="${escAttr("[" + (ix.id || "?") + "] " + (ix.trigger || "") + " → " + actionDesc(ix))}">
  <span class="el">${esc(ix.element || ix.id || "?")}</span>
  <span class="meta">${esc(ix.trigger || "")} → ${esc(actionDesc(ix))}</span>
  ${guardHtml}
</button>`;
}

/**
 * Render a reaction/listener chip HTML string.
 * @param {object} ix - interaction
 * @param {string} surfaceId
 * @returns {string}
 */
function listenerChipHtml(ix, surfaceId) {
  const onLabel = ix.listens_to || ix.trigger || "event";
  return `<div class="listener-chip"
  data-id="${escAttr(ix.id || "")}"
  data-surface="${escAttr(surfaceId || "")}"
  title="reaction — not a user click: on ${escAttr(onLabel)}">
  <span class="top">
    <span class="bolt">⚡</span>
    <span class="el">${esc(ix.element || ix.id || "?")}</span>
  </span>
  <span class="on">on ${esc(onLabel)}</span>
  <span class="meta">→ ${esc(actionDesc(ix))}</span>
</div>`;
}

// ── Shared region-box builder ─────────────────────────────────────────────────

/**
 * Build HTML for all region boxes of a surface.
 * @param {object} surface
 * @param {object} [opts] - { activeId, activeRegion } for highlight
 * @returns {string}
 */
function buildRegionBoxes(surface, opts) {
  const { activeId, activeRegion } = opts || {};
  const order = regionOrder(surface);
  if (order.length === 0) {
    return '<p style="color:#9ca3af;font-style:italic;padding:12px 0">No regions or interactions defined.</p>';
  }
  const groups = groupByRegion(surface, order);
  let html = "";
  for (const region of order) {
    const g = groups[region];
    const n = g.actions.length + g.listeners.length;
    // Highlight this region box if it matches the active region
    const regionActiveCls = activeRegion && region === activeRegion ? " active-region" : "";
    if (n === 0) {
      html += `<div class="region-box empty${regionActiveCls}">
  <div class="region-label">${esc(region)} <span class="region-count">0</span></div>
  <div class="region-empty-note">(display only — no interactions)</div>
</div>`;
      continue;
    }
    let body = "";
    for (const ix of g.actions) body += actionBtnHtml(ix, surface.id, activeId);
    for (const ix of g.listeners) body += listenerChipHtml(ix, surface.id);
    html += `<div class="region-box${regionActiveCls}">
  <div class="region-label">${esc(region)} <span class="region-count">${n}</span></div>
  <div class="region-body">${body}</div>
</div>`;
  }
  return html;
}

// ── Public renderers ──────────────────────────────────────────────────────────

/**
 * Full Layout view for a surface — used by main area + overlay.
 * @param {object} surface
 * @param {object} [opts] - { activeId, activeRegion } forwarded to buildRegionBoxes
 * @returns {string} HTML
 */
function renderLayout(surface, opts) {
  return buildRegionBoxes(surface, opts);
}

/**
 * Compact mini region-box for storyboard cards.
 * Adds class "mini" to a wrapper; pointer-events:none on inner controls.
 * Highlights the region box matching opts.highlightRegion and the button matching opts.highlightEl (by action id).
 * @param {object} surface
 * @param {object} [opts] - { highlightEl: actionId, highlightRegion: regionName }
 * @returns {string} HTML
 */
function renderMini(surface, opts) {
  const { highlightEl, highlightRegion } = opts || {};
  // Build region boxes with highlight, then wrap in .mini container
  const inner = buildRegionBoxes(surface, {
    activeId: highlightEl,
    activeRegion: highlightRegion,
  });
  return `<div class="mini">${inner}</div>`;
}

// wireframe/client/render-states.js — render States subtab content for a surface.
// BROWSER: inlined by html-shell.mjs after region-model.js (esc, escAttr available).
// Globals required: ERR_CATALOG (injected by html-shell.mjs), esc, escAttr (region-model.js).

/**
 * Render state cards HTML for the given surface's `states` array.
 * Returns an HTML string to be set as innerHTML of #view-states.
 * @param {{ states?: {id: string, label: string, description: string, errRefs: string[]}[] }} surface
 * @returns {string}
 */
function renderStates(surface) {
  const states = surface.states || [];

  if (!states.length)
    return '<p class="states-empty">Chưa khai báo states cho màn hình này.</p>';

  return states.map(st => {
    const errChips = (st.errRefs || []).map(e => {
      const desc = (typeof ERR_CATALOG !== "undefined" && ERR_CATALOG[e]) ? ERR_CATALOG[e] : null;
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

// wireframe/client/render-content.js
// BROWSER: typed content renderer — turns layout.content[region] element lists
// into lo-fi wireframe idioms (buttons, inputs, table/list skeletons, tabs, kpi).
// Loaded after region-model.js (esc/escAttr) and after the inlined layout-schema
// globals (CONTENT_TYPES, contentElementType) — see html-shell.mjs ordering.
//
// Elements with an `action:` opt get data-action-id + data-chip-text so the
// existing inspector hover/click delegation in render-grid.js works unchanged
// (it targets .gc-inline-chip, which actionable elements also carry).

/**
 * Render one content element to wireframe HTML.
 * Unknown types render as a visible ⚠ pill (validator warns separately).
 * @param {object} el - content element object
 * @returns {string} HTML
 */
function contentElementHtml(el) {
  const type = contentElementType(el);
  if (!type) return `<span class="wf-unknown">⚠ ?</span>`;
  const v = el[type];

  switch (type) {
    case "h":
      return `<div class="wf-h">${esc(String(v))}</div>`;

    case "text":
      return `<div class="wf-text">${esc(String(v))}</div>`;

    case "btn": {
      const cls = "wf-btn" + (el.primary ? " wf-btn-primary" : "") + actionCls(el);
      return `<span class="${cls}"${actionAttrs(el, String(v))}>${esc(String(v))}</span>`;
    }

    case "input":
      return `<span class="wf-input">${esc(String(v))}</span>`;

    case "select":
      return `<span class="wf-select">${esc(String(v))}<span class="wf-select-caret">▾</span></span>`;

    case "checklist": {
      const items = (Array.isArray(v) ? v : []).map((i) => {
        const s = String(i);
        const checked = s.startsWith("[x] ");
        const label = checked ? s.slice(4) : s;
        return `<div class="wf-check"><span class="wf-checkbox${checked ? " wf-checked" : ""}">${checked ? "✓" : ""}</span>${esc(label)}</div>`;
      });
      return `<div class="wf-checklist">${items.join("")}</div>`;
    }

    case "chips":
      return `<span class="wf-chips">${(Array.isArray(v) ? v : []).map((c) => `<span class="wf-chip">${esc(String(c))}</span>`).join("")}</span>`;

    case "badge":
      return `<span class="wf-badge">${esc(String(v))}</span>`;

    case "tabs": {
      // Per-tab contract map (actions: {label: id}) wins over the whole-bar action.
      const perTab = el.actions && typeof el.actions === "object" ? el.actions : null;
      const tabs = (Array.isArray(v) ? v : []).map((t, i) => {
        const label  = String(t);
        const active = el.active != null ? el.active === t : i === 0;
        const aid    = perTab ? perTab[label] : null;
        const cls    = "wf-tab" + (active ? " wf-tab-active" : "")
          + (aid ? " gc-inline-chip gc-inline-chip-mapped wf-actionable" : "");
        const attrs  = aid
          ? ` data-action-id="${escAttr(String(aid))}" data-chip-text="${escAttr(label)}"`
          : "";
        return `<span class="${cls}"${attrs}>${esc(label)}</span>`;
      });
      // Whole-bar action (no per-tab map): container is the hoverable element.
      const cls = "wf-tabs" + (perTab ? "" : actionCls(el));
      const label = (Array.isArray(v) && v.length) ? String(v[0]) : "tabs";
      return `<div class="${cls}"${perTab ? "" : actionAttrs(el, label)}>${tabs.join("")}</div>`;
    }

    case "table": {
      const cols = Array.isArray(v?.cols) ? v.cols : [];
      const rows = Math.max(1, Math.min(8, Number(v?.rows) || 3));
      const head = `<tr>${cols.map((c) => `<th>${esc(String(c))}</th>`).join("")}</tr>`;
      const body = Array.from({ length: rows }, (_, r) =>
        `<tr>${cols.map(() => `<td><span class="wf-skel" style="width:${60 + ((r * 17) % 30)}%"></span></td>`).join("")}</tr>`
      ).join("");
      return `<table class="wf-table"><thead>${head}</thead><tbody>${body}</tbody></table>`;
    }

    case "list": {
      const rows = Math.max(1, Math.min(8, Number(v?.rows) || 3));
      const item = v?.item ? esc(String(v.item)) : "";
      const lis = Array.from({ length: rows }, (_, r) =>
        `<div class="wf-list-item">${item ? `<span class="wf-list-text${r > 0 ? " wf-list-ghost" : ""}">${item}</span>` : `<span class="wf-skel" style="width:${70 + ((r * 13) % 25)}%"></span>`}</div>`
      ).join("");
      return `<div class="wf-list">${lis}</div>`;
    }

    case "kpi":
      return `<span class="wf-kpi">${v?.label ? `<span class="wf-kpi-label">${esc(String(v.label))}</span>` : ""}<span class="wf-kpi-value">${esc(String(v?.value ?? ""))}</span></span>`;

    case "divider":
      return `<hr class="wf-divider">`;

    case "slot":
      return `<div class="wf-slot">${esc(String(v))}</div>`;

    case "row":
      return `<div class="wf-row">${(Array.isArray(v) ? v : []).map(contentElementHtml).join("")}</div>`;

    default:
      return `<span class="wf-unknown">⚠ ${esc(type)}</span>`;
  }
}

/** Class suffix for actionable elements: reuse chip classes so inspector hover works. */
function actionCls(el) {
  return el && el.action ? " gc-inline-chip gc-inline-chip-mapped wf-actionable" : "";
}

/** data- attributes for actionable elements (inspector + click-through). */
function actionAttrs(el, label) {
  if (!el || !el.action) return "";
  return ` data-action-id="${escAttr(String(el.action))}" data-chip-text="${escAttr(label)}"`;
}

/**
 * Render a region's full content element list (the content: path of a grid cell).
 * @param {object[]} elements - layout.content[region]
 * @returns {string} HTML for .gc-content
 */
function renderContentElements(elements) {
  if (!Array.isArray(elements) || !elements.length) return "";
  return `<div class="gc-content">${elements.map(contentElementHtml).join("")}</div>`;
}

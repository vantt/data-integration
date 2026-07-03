// wireframe/client/render-grid.js
// BROWSER: CSS grid renderer for surfaces with ui-layout model.
// Loaded after render-regionbox.js so regionBoxHtml / renderLayout are already defined.
// Globals available at call time (not at parse time):
//   esc, escAttr          (region-model.js)
//   isReaction            (region-model.js)
//   interactionsOf        (region-model.js)
//   actionDesc            (region-model.js)
//   groupByRegion         (region-model.js)
//   regionBoxHtml         (render-regionbox.js)
//   renderLayout          (render-regionbox.js — stacked fallback)
//   handleInteraction     (app.js)
//   navigateTo            (app.js)
//   showToast             (app.js)
//   currentSurface        (app.js — let, available at call time)

// ── CSS ident sanitization ────────────────────────────────────────────────────

/**
 * Sanitize a region name to a valid CSS ident for grid-area / grid-template-areas.
 * Replaces dots and any non-word characters (except hyphens) with underscores.
 * Must be applied consistently to both grid-template-areas rows AND each cell's grid-area.
 * @param {string} r - raw region name
 * @returns {string}
 */
function cssIdent(r) {
  return String(r).replace(/[^a-zA-Z0-9_-]/g, "_");
}

// ── Shared wiring helper ──────────────────────────────────────────────────────

/**
 * Wire action-button clicks and listener-chip toasts within a DOM subtree.
 * Extracted as reusable helper so both renderMain (app.js) and switchGridVariant
 * can call it without duplicating the selector loop.
 * @param {Element} root - DOM element to scope querySelectorAll
 */
function rewireActionButtons(root) {
  if (!root) return;
  for (const btn of root.querySelectorAll(".action-btn"))
    btn.addEventListener("click", () => handleInteraction(btn));
  for (const chip of root.querySelectorAll(".listener-chip"))
    chip.addEventListener("click", () =>
      showToast("Reaction [" + (chip.dataset.id || "") + "]: " + (chip.getAttribute("title") || ""), 3500));
}

// ── Chip sample renderer ──────────────────────────────────────────────────────

/**
 * Tokenize a sample text string into text segments and [bracket] chip segments.
 * Returns [{type:"text"|"chip", value:string}].
 * @param {string} raw - raw sample text (not yet escaped)
 * @returns {Array<{type:string,value:string}>}
 */
function tokenizeSample(raw) {
  const tokens = [];
  const re = /\[([^\]]+)\]/g;
  let last = 0;
  let m;
  while ((m = re.exec(raw)) !== null) {
    if (m.index > last) tokens.push({ type: "text", value: raw.slice(last, m.index) });
    tokens.push({ type: "chip", value: m[1] });
    last = re.lastIndex;
  }
  if (last < raw.length) tokens.push({ type: "text", value: raw.slice(last) });
  return tokens;
}

/**
 * Render sample text as HTML, converting [bracket] tokens into inline chip spans.
 * Chips matching a key in elements get data-action-id and a mapped class.
 * Escape-safe: each token part is escaped individually after tokenization.
 *
 * @param {string|null} raw - raw sample text
 * @param {object} elements - layout.elements map {chipText → actionId}; may be empty
 * @returns {string} HTML for .gc-sample div, or "" when raw is null/empty
 */
function renderSampleWithChips(raw, elements) {
  if (!raw) return "";
  const tokens = tokenizeSample(raw);
  const parts = tokens.map((t) => {
    if (t.type === "text") return esc(t.value);
    const actionId = elements && elements[t.value];
    const cls = actionId ? "gc-inline-chip gc-inline-chip-mapped" : "gc-inline-chip";
    const actionAttr = actionId ? ` data-action-id="${escAttr(String(actionId))}"` : "";
    return `<span class="${cls}" data-chip-text="${escAttr(t.value)}"${actionAttr}>${esc(t.value)}</span>`;
  });
  return `<div class="gc-sample">${parts.join("")}</div>`;
}

// ── Grid cell inner renderer (wireframe-style, stakeholder-readable) ─────────

/**
 * Render inner content for a single grid cell — lightweight wireframe style.
 * Intentionally simpler than regionBoxHtml: no count badges, no listener chips,
 * no guard pills. Contract detail lives in the hover-driven inspector panel.
 *
 * Elements:
 *   gc-label  — 9px muted uppercase region name
 *   gc-sample — dominant 13px sample text with inline [chip] elements
 *
 * [bracket] tokens in sample text are rendered as inline chips (.gc-inline-chip).
 * Chips matching a key in surface.layout.elements get class gc-inline-chip-mapped
 * and a data-action-id attribute for inspector and click-trigger.
 *
 * @param {object} surface
 * @param {string} region
 * @param {string|null} sampleText
 * @returns {string} HTML (inner content only — caller wraps in .grid-cell)
 */
function gridCellHtml(surface, region, sampleText) {
  const elements = surface.layout?.elements || {};
  const labelHtml  = `<div class="gc-label">${esc(region)}</div>`;
  const sampleHtml = renderSampleWithChips(sampleText, elements);
  return labelHtml + sampleHtml;
}

// ── Child sub-layout renderer (1 level, vertical stack) ──────────────────────

/**
 * Render a region's child sub-layout (layout.children[region]) as stacked
 * mini-sections inside the parent grid cell — same visual grammar as gridCellHtml
 * (gc-label + gc-sample per child region, inline chips included).
 *
 * Each .gc-child receives data-region-raw so the inspector hover handler can
 * identify the child region independently of the parent cell.
 *
 * Rules:
 *   - Child areas may be a matrix; rendered as a vertical stack of row entries
 *     in first-appearance order (single column, 1 level only — no recursion).
 *   - Child regions that ALSO appear in layout.floating are SKIPPED here:
 *     they render as floating toggle banners only (e.g. S03 sidebar.warning),
 *     never twice.
 *
 * @param {object} surface
 * @param {object} layout - surface.layout (source of children / floating / samples)
 * @param {string} region - parent region name
 * @returns {string} HTML ("" when region has no child layout)
 */
function gridChildSectionsHtml(surface, layout, region) {
  const child = layout.children?.[region];
  if (!child || !Array.isArray(child.areas)) return "";
  const floatingSet = new Set((layout.floating || []).map((f) => f.region));
  const samples = layout.samples || {};
  const seen = new Set();
  const sections = [];
  for (const row of child.areas) {
    for (const name of row) {
      if (seen.has(name) || floatingSet.has(name)) continue;
      seen.add(name);
      // data-region-raw on .gc-child enables the inspector to identify the child region
      sections.push(
        `<div class="gc-child" data-region-raw="${escAttr(name)}">${gridCellHtml(surface, name, samples[name] || null)}</div>`
      );
    }
  }
  return sections.length ? `<div class="gc-children">${sections.join("")}</div>` : "";
}

// ── Inspector panel ───────────────────────────────────────────────────────────

/**
 * Build default inspector panel content HTML (hint + surface-level interaction counts).
 * @param {object} surface
 * @returns {string} HTML for .gi-content
 */
function buildInspectorDefault(surface) {
  const all = interactionsOf(surface);
  const actCount  = all.filter((ix) => !isReaction(ix)).length;
  const reactCount = all.filter((ix) => isReaction(ix)).length;
  return `<div class="gi-hint">Hover một element hoặc vùng để xem contract</div>`
    + `<div class="gi-surface-meta">${actCount} interaction${actCount !== 1 ? "s" : ""} · ${reactCount} reaction${reactCount !== 1 ? "s" : ""}</div>`;
}

/**
 * Build inspector content for a region hover: region name + compact interaction rows.
 * @param {object} surface
 * @param {string} regionRaw - raw region name (not CSS ident)
 * @returns {string} HTML for .gi-content
 */
function buildInspectorRegion(surface, regionRaw) {
  if (!regionRaw) return buildInspectorDefault(surface);
  const groups = groupByRegion(surface, [regionRaw]);
  const g = groups[regionRaw] || { actions: [], listeners: [] };
  let html = `<div class="gi-region-name">${esc(regionRaw)}</div>`;
  if (g.actions.length === 0 && g.listeners.length === 0) {
    html += `<div class="gi-empty">No interactions in this region</div>`;
    return html;
  }
  for (const ix of g.actions) {
    html += `<div class="gi-row">`
      + `<span class="gi-el">${esc(ix.element || ix.id || "?")}</span>`
      + `<span class="gi-sep">${esc(ix.trigger || "?")} →</span>`
      + `<span class="gi-act">${esc(actionDesc(ix))}</span>`
      + (ix.guard ? `<span class="gi-guard">if: ${esc(ix.guard)}</span>` : "")
      + `</div>`;
  }
  for (const ix of g.listeners) {
    html += `<div class="gi-row gi-row-reaction">`
      + `<span class="gi-el">⚡ ${esc(ix.element || ix.id || "?")}</span>`
      + `<span class="gi-sep">on ${esc(ix.listens_to || "event")} →</span>`
      + `<span class="gi-act">${esc(actionDesc(ix))}</span>`
      + `</div>`;
  }
  return html;
}

/**
 * Build inspector content for an inline chip hover.
 * If mapped (in layout.elements): show full action contract with clickable target.
 * If unmapped: show "chưa gắn contract" + region interaction list as fallback.
 * @param {object} surface
 * @param {string} chipText - text inside [brackets]
 * @param {string} regionRaw - nearest region name (parent cell or gc-child)
 * @returns {string} HTML for .gi-content
 */
function buildInspectorChip(surface, chipText, regionRaw) {
  const elements  = surface.layout?.elements || {};
  const actionId  = elements[chipText];
  if (actionId) {
    const all = interactionsOf(surface);
    const ix  = all.find((a) => a.id === actionId);
    if (!ix) {
      // Mapped but action not found in this surface (VR-ELEMENT-REF catches this)
      return `<div class="gi-chip-title">[${esc(chipText)}]</div>`
        + `<div class="gi-unmapped">mapped → ${esc(String(actionId))} (not found in surface)</div>`
        + buildInspectorRegion(surface, regionRaw);
    }
    const isNavAction = ix.action === "navigate" || ix.action === "open_overlay";
    const targetStr  = ix.target != null ? String(ix.target) : "";
    // Target is clickable when action is navigate/open_overlay
    const targetHtml = targetStr
      ? isNavAction
        ? `<button class="gi-target-btn" onclick="event.stopPropagation();navigateTo('${escAttr(targetStr)}')">${esc(targetStr)}</button>`
        : esc(targetStr)
      : "—";

    let html = `<div class="gi-chip-title">[${esc(chipText)}]</div>`;
    html += `<div class="gi-contract">`;
    html += `<div class="gi-kv"><span class="gi-k">id</span><span class="gi-v">${esc(ix.id || "?")}</span></div>`;
    html += `<div class="gi-kv"><span class="gi-k">element</span><span class="gi-v">${esc(ix.element || "?")}</span></div>`;
    html += `<div class="gi-kv"><span class="gi-k">trigger</span><span class="gi-v">${esc(ix.trigger || "?")}</span></div>`;
    html += `<div class="gi-kv"><span class="gi-k">action</span><span class="gi-v">${esc(ix.action || "?")}</span></div>`;
    html += `<div class="gi-kv"><span class="gi-k">target</span><span class="gi-v">${targetHtml}</span></div>`;
    if (ix.guard)
      html += `<div class="gi-kv"><span class="gi-k">guard</span><span class="gi-v gi-guard">${esc(ix.guard)}</span></div>`;
    if (ix.effects?.length)
      html += `<div class="gi-kv"><span class="gi-k">effects</span><span class="gi-v">${esc(ix.effects.join(", "))}</span></div>`;
    if (ix.listens_to)
      html += `<div class="gi-kv"><span class="gi-k">listens_to</span><span class="gi-v">${esc(ix.listens_to)}</span></div>`;
    html += `</div>`;
    return html;
  } else {
    // Unmapped chip — show hint + region fallback
    return `<div class="gi-chip-title">[${esc(chipText)}]</div>`
      + `<div class="gi-unmapped">chưa gắn contract</div>`
      + buildInspectorRegion(surface, regionRaw);
  }
}

/**
 * Build the fixed inspector panel HTML (always present in grid view).
 * Content area is empty by default; hover handlers fill it dynamically.
 * @param {object} surface
 * @returns {string} HTML for .grid-inspector
 */
function buildInspectorPanel(surface) {
  return `<div id="grid-inspector" class="grid-inspector">`
    + `<div class="gi-header">Contract Inspector</div>`
    + `<div class="gi-content">${buildInspectorDefault(surface)}</div>`
    + `<div class="gi-footer">click để ghim</div>`
    + `</div>`;
}

// ── Inspector hover state ─────────────────────────────────────────────────────

/** Whether the inspector is pinned (user clicked a cell/chip). */
let _inspectorPinned = false;

/** Surface currently displayed in the inspector (for reset after mouseleave). */
let _inspectorCurrentSurface = null;

/**
 * Update the inspector content area if not pinned.
 * @param {string} html - new HTML for .gi-content
 */
function setInspectorContent(html) {
  if (_inspectorPinned) return;
  const panel = document.getElementById("grid-inspector");
  if (!panel) return;
  const content = panel.querySelector(".gi-content");
  if (content) content.innerHTML = html;
  const footer = panel.querySelector(".gi-footer");
  if (footer) footer.textContent = "click để ghim";
}

/**
 * Reset inspector to the default (hint + counts) state when not pinned.
 */
function resetInspectorContent() {
  if (_inspectorPinned || !_inspectorCurrentSurface) return;
  setInspectorContent(buildInspectorDefault(_inspectorCurrentSurface));
}

// ── Inspector hover wiring ────────────────────────────────────────────────────

/**
 * Wire hover + click event delegation for the inspector panel on the grid.
 * Called after every renderGrid/innerHTML assignment.
 * Resets pin state and removes the previous document-level unpin listener.
 *
 * Hover delegation on .grid-main:
 *   - .gc-inline-chip hover → chip contract (if mapped) or unmapped note
 *   - .grid-cell hover → region interactions
 *   - mouseleave → reset to default
 *
 * Click on cell/chip pins the panel. Clicking outside .grid-with-inspector unpins.
 * Clicking a mapped chip whose action is navigate/open_overlay also fires handleInteraction.
 *
 * @param {Element} viewGridDiv - the #view-grid DOM element
 * @param {object} surface - current surface data
 */
function rewireInspectorHover(viewGridDiv, surface) {
  _inspectorPinned = false;
  _inspectorCurrentSurface = surface;

  const gridMain = viewGridDiv.querySelector(".grid-main");
  if (!gridMain) return;

  // Hover delegation — chip takes priority over cell
  gridMain.addEventListener("mouseover", (e) => {
    if (_inspectorPinned) return;
    const chip = e.target.closest(".gc-inline-chip");
    if (chip) {
      const chipText  = chip.dataset.chipText || "";
      // Nearest ancestor with data-region-raw (gc-child or grid-cell)
      const regionEl  = chip.closest("[data-region-raw]");
      const regionRaw = regionEl ? regionEl.dataset.regionRaw : "";
      setInspectorContent(buildInspectorChip(surface, chipText, regionRaw));
      return;
    }
    const cell = e.target.closest(".grid-cell[data-region-raw]");
    if (cell) {
      setInspectorContent(buildInspectorRegion(surface, cell.dataset.regionRaw));
    }
  });

  gridMain.addEventListener("mouseleave", () => {
    if (!_inspectorPinned) resetInspectorContent();
  });

  // Click delegation: pin panel + optionally trigger action for mapped chips
  gridMain.addEventListener("click", (e) => {
    const chip = e.target.closest(".gc-inline-chip");
    const cell = e.target.closest(".grid-cell[data-region-raw]");
    if (!chip && !cell) return;

    _inspectorPinned = true;
    const panel  = document.getElementById("grid-inspector");
    const footer = panel?.querySelector(".gi-footer");
    if (footer) footer.textContent = "📌 ghim · click ngoài để bỏ";

    // Mapped chip: fire navigate/open_overlay through handleInteraction
    if (chip && chip.dataset.actionId) {
      const all = interactionsOf(surface);
      const ix  = all.find((a) => a.id === chip.dataset.actionId);
      if (ix && (ix.action === "navigate" || ix.action === "open_overlay")) {
        // Synthetic btn-like object — handleInteraction reads .dataset only
        handleInteraction({ dataset: { action: ix.action, target: ix.target || "", id: ix.id || "" } });
      }
    }
  });

  // Document-level unpin when clicking outside the grid-with-inspector wrapper
  if (rewireInspectorHover._docHandler) {
    document.removeEventListener("click", rewireInspectorHover._docHandler);
  }
  rewireInspectorHover._docHandler = (e) => {
    if (!_inspectorPinned) return;
    if (!e.target.closest(".grid-with-inspector")) {
      _inspectorPinned = false;
      resetInspectorContent();
    }
  };
  document.addEventListener("click", rewireInspectorHover._docHandler);
}

// ── Grid renderer ─────────────────────────────────────────────────────────────

/**
 * Render the full CSS grid view for a surface with a ui-layout model.
 * Returns an HTML string (no side-effects; caller sets innerHTML).
 *
 * Layout:
 *   .grid-with-inspector — flex row: grid grows (flex:1), inspector fixed 300px
 *   .grid-main — holds variant-switcher + grid-container + floating banners
 *   .grid-inspector (#grid-inspector) — hover-driven contract inspector panel
 *
 * Grid semantics:
 *   - layout.columns → grid-template-columns (e.g. "3fr 2fr")
 *   - layout.areas   → grid-template-areas  (sanitized via cssIdent)
 *   - layout.samples → sample content lines per region (with inline chip tokenization)
 *   - layout.elements → chip text → action id map (for inspector and chip styling)
 *   - layout.floating → toggle buttons + collapsible banners with replaces list
 *   - layout.variants → switcher bar; active variant prepends / appends rows
 *   - layout.children → 1-level nested sub-layouts rendered as stacked mini-sections
 *       INSIDE the parent region's grid cell (gridChildSectionsHtml). Child regions
 *       that also appear in layout.floating (e.g. S03: sidebar.warning) are skipped
 *       there and render as floating toggle banners only — never twice.
 *
 * @param {object} surface
 * @param {string|null} [activeVariant] - variant key to apply (null = base layout)
 * @returns {string} HTML
 */
function renderGrid(surface, activeVariant) {
  const layout = surface.layout;
  if (!layout) return renderLayout(surface); // stacked fallback for surfaces without layout

  // Build effective areas: apply variant prepend_rows / append_rows if requested.
  const variantDef = activeVariant && layout.variants?.[activeVariant];
  const effectiveAreas = variantDef
    ? [
        ...(variantDef.prepend_rows || []),
        ...layout.areas,
        ...(variantDef.append_rows  || []),
      ]
    : layout.areas;

  const samples = layout.samples || {};

  // CSS grid property values
  const columnsVal = Array.isArray(layout.columns) && layout.columns.length
    ? layout.columns.join(" ")
    : "1fr";
  // Single-quote each row: the whole value is interpolated into a double-quoted
  // style="" attribute, where inner double quotes would truncate the attribute
  // and silently drop grid-template-areas (cells then auto-place as a stack).
  const areasVal = effectiveAreas
    .map((row) => "'" + row.map(cssIdent).join(" ") + "'")
    .join(" ");

  // Unique region names in order of first appearance (preserves visual order).
  const seen    = new Set();
  const regions = [];
  for (const row of effectiveAreas) {
    for (const cell of row) {
      const ident = cssIdent(cell);
      if (!seen.has(ident)) { seen.add(ident); regions.push({ raw: cell, ident }); }
    }
  }

  // Grid cells — one <div> per distinct region.
  // Uses gridCellHtml (not regionBoxHtml) so cells render as clean wireframe cards
  // without count badges, listener chips, guard pills, or "(display only)" notes.
  // Regions with a child sub-layout additionally stack child mini-sections below.
  // data-region-raw stores the original (un-sanitized) region name for the inspector.
  const cells = regions.map(({ raw, ident }) => {
    const sampleText = samples[raw] || null;
    const inner = gridCellHtml(surface, raw, sampleText)
      + gridChildSectionsHtml(surface, layout, raw);
    return `<div class="grid-cell" style="grid-area:${ident}" data-region-ident="${escAttr(ident)}" data-region-raw="${escAttr(raw)}">${inner}</div>`;
  }).join("\n");

  // Floating region banners + toggle buttons.
  const floating     = layout.floating || [];
  const floatingHtml = floating.map((f) => {
    const rn      = f.region || "";
    const ident   = cssIdent(rn);
    const whenLabel = f.when ? ` — khi: ${esc(f.when)}` : "";
    const sampleText = samples[rn] || null;
    const replacesIdents = (f.replaces || []).map(cssIdent);
    return `<button class="floating-toggle" data-floating="${escAttr(ident)}" data-replaces="${escAttr(replacesIdents.join(","))}" onclick="toggleFloating(this)">⛔ ${esc(rn)}${whenLabel}</button>
<div class="floating-banner" id="floating-${escAttr(ident)}" style="display:none">
  <div class="grid-cell gc-floating">${gridCellHtml(surface, rn, sampleText)}</div>
</div>`;
  }).join("\n");

  // Variant switcher bar (only when surface declares variants).
  const variantKeys     = Object.keys(layout.variants || {});
  const variantSwitcher = variantKeys.length
    ? `<div class="variant-switcher">
        <span>Variant:</span>
        <button class="variant-btn${!activeVariant ? " active" : ""}" data-variant="" onclick="switchGridVariant(this.dataset.variant)">default</button>
        ${variantKeys.map((k) =>
          `<button class="variant-btn${activeVariant === k ? " active" : ""}" data-variant="${escAttr(k)}" onclick="switchGridVariant(this.dataset.variant)">${esc(k)}</button>`
        ).join("")}
      </div>`
    : "";

  return `<div class="grid-with-inspector">
<div class="grid-main">
${variantSwitcher}
<div class="grid-container" style="display:grid;grid-template-columns:${columnsVal};grid-template-areas:${areasVal};gap:12px;grid-auto-rows:minmax(56px,auto)">
${cells}
</div>
${floatingHtml}
</div>
${buildInspectorPanel(surface)}
</div>`;
}

// ── Interactive handlers (called by inline onclick on generated elements) ─────

/**
 * Toggle a floating region banner on/off.
 * When the banner becomes visible, replaced cells are hidden via display:none.
 * When hidden again, replaced cells are restored.
 * @param {HTMLButtonElement} btn - the toggle button (passes `this` via onclick)
 */
function toggleFloating(btn) {
  const ident  = btn.dataset.floating;
  const banner = document.getElementById("floating-" + ident);
  if (!banner) return;
  const isCurrentlyVisible = banner.style.display !== "none";

  // Toggle banner
  banner.style.display = isCurrentlyVisible ? "none" : "block";
  btn.classList.toggle("floating-toggle-active", !isCurrentlyVisible);

  // Show/hide replaced grid cells
  const replaces = (btn.dataset.replaces || "").split(",").filter(Boolean);
  const viewGrid = document.getElementById("view-grid");
  for (const r of replaces) {
    const cell = viewGrid && viewGrid.querySelector(`.grid-cell[data-region-ident="${r}"]`);
    if (cell) cell.style.display = isCurrentlyVisible ? "" : "none";
  }
}

/**
 * Re-render the grid with a new variant applied.
 * Called via onclick; receives this.dataset.variant which is "" for default (no variant).
 * Coerces empty string → null so renderGrid sees null = base layout.
 * Reads currentSurface (declared in app.js — available at call time).
 * @param {string} variantKey - variant name, or "" for base layout
 */
function switchGridVariant(variantKey) {
  const container = document.getElementById("view-grid");
  if (!container || !currentSurface) return;
  container.innerHTML = renderGrid(currentSurface, variantKey || null);
  rewireActionButtons(container);
  rewireInspectorHover(container, currentSurface);
}

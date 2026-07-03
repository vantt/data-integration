// wireframe/client/graph-controls.js — BROWSER: Graph view state + Cytoscape lifecycle.
// renderAndInsertGraph() called by switchView('graph'). Deps inlined before this file:
// render-graph.js, app.js, app-chrome.js, region-model.js, cytoscape (UMD global).

// ── Graph view state ──────────────────────────────────────────────────────────
const graphState = {
  includeReactions: false,
  highlightFlowId:  "",
  layoutName:       "dagre",
};

/** Single shared Cytoscape instance — created once, refreshed on state change. */
let _cy = null;

// ── Cytoscape mount / refresh ─────────────────────────────────────────────────

/**
 * Build or rebuild the Cytoscape graph in #view-graph.
 * Safe to call multiple times — destroys + recreates if already mounted.
 */
function renderAndInsertGraph() {
  const container = document.getElementById("view-graph");
  if (!container) return;

  // Guard: cytoscape global may be absent under jsdom (no canvas) — fail gracefully.
  if (typeof cytoscape === "undefined") {
    container.innerHTML =
      "<p style='color:#9ca3af;padding:32px'>Graph unavailable (cytoscape not loaded).</p>";
    return;
  }

  const { elements, style, flowPath, nodeCount } = renderGraph(graphState);

  if (!nodeCount) {
    container.innerHTML =
      "<p style='color:#9ca3af;padding:32px'>No navigation edges found in surfaces.</p>";
    return;
  }

  // Destroy previous instance cleanly
  if (_cy) { try { _cy.destroy(); } catch (_) {} _cy = null; }

  // Cytoscape needs explicit px height — compute from #main (switchView sets display:block).
  const main = document.getElementById("main");
  const toolbar = document.getElementById("graph-toolbar");
  const topbarH  = document.getElementById("topbar")?.offsetHeight  || 46;
  const toolbarH = (toolbar && toolbar.style.display !== "none") ? (toolbar.offsetHeight || 38) : 0;
  // Use main's client height if available (flex layout), else fallback to viewport minus topbars
  const mainH = (main && main.clientHeight > 0) ? main.clientHeight : (window.innerHeight - topbarH - toolbarH);
  container.style.height = Math.max(mainH, 400) + "px";

  try {
    _cy = cytoscape({
      container,
      elements,
      style,
      layout: graphLayoutConfig(graphState.layoutName),
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.3,
    });
  } catch (err) {
    // Cytoscape throws under jsdom (no canvas/HTMLCanvasElement) — graceful fallback
    console.warn("Cytoscape init failed (expected under jsdom):", err.message);
    container.innerHTML =
      "<p style='color:#9ca3af;padding:32px'>Graph unavailable in headless environment.</p>";
    return;
  }

  _applyFlowHighlight(flowPath);
  _wireHover();
  _wireNodeTap();
}

// ── Flow-path highlight ───────────────────────────────────────────────────────

function _applyFlowHighlight(flowPath) {
  if (!_cy) return;
  _cy.elements().removeClass("highlighted dimmed");
  if (!flowPath.length) return;

  const hlNodeSet = new Set(flowPath);
  const hlEdgePairs = new Set();
  for (let i = 0; i < flowPath.length - 1; i++) {
    hlEdgePairs.add(flowPath[i] + "|" + flowPath[i + 1]);
  }

  _cy.nodes().forEach(n => {
    n.addClass(hlNodeSet.has(n.id()) ? "highlighted" : "dimmed");
  });
  _cy.edges().forEach(e => {
    const key = e.data("source") + "|" + e.data("target");
    e.addClass(hlEdgePairs.has(key) ? "highlighted" : "dimmed");
  });
}

// ── Hover: highlight node + connected neighbors ───────────────────────────────

function _wireHover() {
  if (!_cy) return;

  _cy.on("mouseover", "node", function(evt) {
    const node = evt.target;
    _cy.elements().addClass("dimmed").removeClass("neighbor-highlighted");
    node.removeClass("dimmed").addClass("neighbor-highlighted");
    node.connectedEdges().removeClass("dimmed").addClass("neighbor-highlighted");
    node.neighborhood("node").removeClass("dimmed").addClass("neighbor-highlighted");
  });

  _cy.on("mouseout", "node", function() {
    _cy.elements().removeClass("dimmed neighbor-highlighted");
    // Restore flow highlight if active
    if (graphState.highlightFlowId) {
      const { flowPath } = renderGraph(graphState);
      _applyFlowHighlight(flowPath);
    }
  });
}

// ── Node tap → navigate ───────────────────────────────────────────────────────

function _wireNodeTap() {
  if (!_cy) return;
  _cy.on("tap", "node", function(evt) {
    const sid = evt.target.id();
    if (sid) {
      navigateTo(sid);    // defined in app.js
      switchView("layout"); // defined in app-chrome.js
    }
  });
}

// ── Fit button (injected into graph-toolbar) ──────────────────────────────────

function _insertFitButton() {
  const toolbar = document.getElementById("graph-toolbar");
  if (!toolbar || document.getElementById("graph-fit-btn")) return;
  const btn = document.createElement("button");
  btn.id = "graph-fit-btn";
  btn.className = "icon-btn";
  btn.title = "Fit graph to view";
  btn.textContent = "⊡ Fit";
  btn.style.cssText = "font-size:11px;padding:3px 8px;";
  btn.addEventListener("click", () => { if (_cy) _cy.fit(undefined, 40); });
  toolbar.appendChild(btn);
}

// ── Wire graph toolbar controls ───────────────────────────────────────────────

/**
 * Set up reaction-toggle, flow-highlight select, and Fit button.
 * Called once from app.js init after DOM ready.
 */
function initGraphControls() {
  _insertFitButton();

  // Reaction toggle
  const toggle = document.getElementById("graph-reaction-toggle");
  if (toggle) {
    toggle.addEventListener("change", () => {
      graphState.includeReactions = toggle.checked;
      if (document.getElementById("view-graph")?.style.display !== "none") {
        renderAndInsertGraph();
      }
    });
  }

  // Flow-highlight select — populate + re-render on change
  const flowSel = document.getElementById("graph-flow-select");
  if (flowSel) {
    const flows = SURFACES.filter(s => s.meta?.type === "flow");
    flowSel.innerHTML =
      '<option value="">— highlight flow —</option>' +
      flows.map(s =>
        `<option value="${escAttr(s.id)}">${escAttr(s.id + " · " + (s.meta?.name || s.file))}</option>`
      ).join("");

    flowSel.addEventListener("change", () => {
      graphState.highlightFlowId = flowSel.value;
      if (!_cy) return;
      // Re-apply highlight without full rebuild for performance
      if (graphState.highlightFlowId) {
        const { flowPath } = renderGraph(graphState);
        _applyFlowHighlight(flowPath);
      } else {
        _cy.elements().removeClass("highlighted dimmed");
      }
    });
  }

  // Layout preset select — re-run layout on the live Cytoscape instance
  const layoutSel = document.getElementById("graph-layout-select");
  if (layoutSel) {
    layoutSel.addEventListener("change", () => {
      graphState.layoutName = layoutSel.value;
      if (document.getElementById("view-graph")?.style.display !== "none") renderAndInsertGraph();
    });
  }
}

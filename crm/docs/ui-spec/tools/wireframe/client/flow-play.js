// wireframe/client/flow-play.js
// BROWSER: Flow play 2.0 — step-through timer, narration banner, highlight wiring.
// Depends on: region-model.js (edgeById, narrate), app-chrome.js (switchView),
//             app.js (navigateTo, renderMain, surfaceById, showToast, currentView).
// Load order: html-shell.mjs inlines this file BEFORE app.js — so app.js symbols
// (navigateTo, surfaceById, etc.) are NOT yet declared when this file is parsed.
// That is safe because all cross-file calls happen inside function bodies (flowPlay,
// executeFlowStep, populateStoryboard …) that are only invoked AFTER app.js has run
// its init block and all function declarations are hoisted into the shared script scope.

// ── Flow play state ───────────────────────────────────────────────────────────
let flowActive = null;   // { surface, steps:string[] } when playing
let flowStepIdx = 0;
let flowTimer = null;
const FLOW_STEP_MS = 1500; // ms per step

// ── DOM refs (safe to call after DOMContentLoaded — we're inline script) ──────
function getBanner()   { return document.getElementById("narration-banner"); }
function getFlowSel()  { return document.getElementById("flow-select"); }
function getBtnPlay()  { return document.getElementById("btn-flow-play"); }
function getBtnStop()  { return document.getElementById("btn-flow-stop"); }

// ── Highlight helpers ─────────────────────────────────────────────────────────

/** Remove all active-region / active-el classes from the layout view. */
function clearHighlights() {
  for (const el of document.querySelectorAll(".active-region, .active-el"))
    el.classList.remove("active-region", "active-el");
}

/**
 * Re-render Layout view with highlights for the given edge, then apply CSS classes.
 * Switches to layout view so the highlight is visible.
 * @param {object} edge - from edgeById(stepId)
 */
function applyHighlight(edge) {
  if (!edge) return;
  const surface = surfaceById[edge.from];
  if (!surface) return;

  // Switch to layout tab so highlight is visible during play
  if (currentView !== "layout") switchView("layout");

  // Re-render with highlight options so CSS classes are in the fresh markup
  document.getElementById("view-layout").innerHTML =
    renderLayout(surface, { activeId: edge.id, activeRegion: edge.region });

  // Wire action buttons again (renderMain is not called here — we render directly)
  for (const btn of document.querySelectorAll("#view-layout .action-btn"))
    btn.addEventListener("click", () => handleInteraction(btn));
  for (const chip of document.querySelectorAll("#view-layout .listener-chip"))
    chip.addEventListener("click", () =>
      showToast("Reaction [" + (chip.dataset.id || "") + "]: " + (chip.getAttribute("title") || ""), 3500));
}

// ── Narration banner ──────────────────────────────────────────────────────────

function showNarrationBanner(text, stepNum, total) {
  const banner = getBanner();
  if (!banner) return;
  banner.querySelector(".nb-step").textContent = "Step " + stepNum + "/" + total;
  banner.querySelector(".nb-text").textContent = text;
  banner.classList.remove("hidden");
}

function hideNarrationBanner() {
  const banner = getBanner();
  if (banner) banner.classList.add("hidden");
}

// ── Step execution ────────────────────────────────────────────────────────────

/**
 * Execute a single flow step: navigate to its surface, apply highlight, show banner.
 * @param {string} stepId - action ID
 * @param {number} idx - 0-based index
 * @param {number} total
 */
function executeFlowStep(stepId, idx, total) {
  const edge = edgeById(stepId);

  // Navigate to owning surface if known
  if (edge?.from && surfaceById[edge.from]) {
    // Use direct assignment to avoid polluting navStack during play
    currentSurface = surfaceById[edge.from];
    renderMain();
    updateBreadcrumb();
    updateBackBtn();
    updateSidebarActive();
  }

  // Apply highlight overlay on the rendered layout
  applyHighlight(edge);

  // Show narration banner
  showNarrationBanner(narrate(stepId), idx + 1, total);
}

// ── Play / Stop controls ──────────────────────────────────────────────────────

function flowPlay() {
  const sel = getFlowSel();
  if (!sel || !sel.value) { showToast("Select a flow first"); return; }
  const surface = surfaceById[sel.value];
  if (!surface?.contract?.flow?.steps?.length) {
    showToast("Flow has no steps"); return;
  }
  flowStop(); // clear any running play
  flowActive = { surface, steps: surface.contract.flow.steps };
  flowStepIdx = 0;
  getBtnPlay()?.setAttribute("disabled", "");
  getBtnStop()?.removeAttribute("disabled");

  // Execute first step immediately, then advance on interval
  executeFlowStep(flowActive.steps[0], 0, flowActive.steps.length);

  flowTimer = setInterval(() => {
    flowStepIdx++;
    if (flowStepIdx >= flowActive.steps.length) {
      flowStop();
      showToast("Flow complete ✓", 2500);
      return;
    }
    executeFlowStep(flowActive.steps[flowStepIdx], flowStepIdx, flowActive.steps.length);
  }, FLOW_STEP_MS);
}

function flowStop() {
  if (flowTimer) { clearInterval(flowTimer); flowTimer = null; }
  flowActive = null;
  flowStepIdx = 0;
  clearHighlights();
  hideNarrationBanner();
  getBtnPlay()?.removeAttribute("disabled");
  getBtnStop()?.setAttribute("disabled", "");
}

// ── Storyboard tab population ─────────────────────────────────────────────────

/**
 * Populate #view-storyboard with the filmstrip for the selected flow surface.
 * Wire card clicks → navigateTo.
 * @param {object|null} flowSurface
 */
function populateStoryboard(flowSurface) {
  const container = document.getElementById("view-storyboard");
  if (!container) return;

  if (!flowSurface || flowSurface.meta?.type !== "flow") {
    container.innerHTML = '<p class="sb-hint">Select a flow surface to see its storyboard.</p>';
    return;
  }

  container.innerHTML = renderStoryboard(flowSurface);

  // Wire card clicks → navigateTo the step's surface
  for (const card of container.querySelectorAll(".sb-card[data-from]")) {
    const sid = card.dataset.from;
    if (sid) card.addEventListener("click", () => navigateTo(sid));
  }
}

// ── Flow select change handler ────────────────────────────────────────────────

function onFlowSelectChange() {
  const sel = getFlowSel();
  if (!sel) return;
  flowStop();
  const surface = sel.value ? surfaceById[sel.value] : null;

  // If storyboard tab is active, refresh it immediately
  if (currentView === "storyboard") populateStoryboard(surface);
}

// ── Init (called once by app.js after DOM + SURFACES ready) ──────────────────

/**
 * Populate the flow <select> with all type==='flow' surfaces and pre-warm edge index.
 * Called from app.js init block (flow-play.js is inlined before app.js).
 */
function initFlowBar() {
  // Pre-warm lazy edge index singleton so first storyboard render is fast
  edgeById("__warmup__");

  const sel = getFlowSel();
  if (!sel) return;
  const flows = SURFACES.filter(s => s.meta?.type === "flow");
  sel.innerHTML = '<option value="">— select flow —</option>' +
    flows.map(s =>
      `<option value="${escAttr(s.id)}">${escAttr(s.id + " · " + (s.meta?.name || s.file))}</option>`
    ).join("");
}

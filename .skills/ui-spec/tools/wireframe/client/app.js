// wireframe/client/app.js
// BROWSER: state, navigation, overlay, interaction handler, renderMain, init.
// Chrome helpers (sidebar, breadcrumb, bottombar, switchView) live in app-chrome.js,
// which is inlined just before this file by html-shell.mjs.
// Depends on: region-model.js, render-regionbox.js, app-chrome.js (all inlined prior).

// ── Index + State ─────────────────────────────────────────────────────────────
const surfaceById = {};
for (const s of SURFACES) { if (s.id) surfaceById[s.id] = s; }

let navStack = [];        // string[] of surface IDs visited — shared mutable state; also reassigned in app-chrome.js (breadcrumb crumb-click truncates it)
let currentSurface = null;
let overlayStack = [];    // string[] of surface IDs shown as overlay
let currentView = "layout"; // "layout" | "blueprint"

// ── Helpers ───────────────────────────────────────────────────────────────────
function showToast(msg, duration) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), duration || 2800);
}

function typeBadgeClass(type) {
  const map = { screen:"badge-screen", modal:"badge-modal", panel:"badge-panel",
                overlay:"badge-overlay", component:"badge-component", flow:"badge-flow" };
  return map[type] || "badge-default";
}

/**
 * Scroll to and briefly flash the action button matching actionId.
 * Called after navigateTo(); uses setTimeout(50) to wait for renderMain().
 */
function highlightAction(actionId) {
  setTimeout(() => {
    const escaped = actionId.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    const btn = document.querySelector('[data-id="' + escaped + '"]');
    if (!btn) return;
    if (typeof btn.scrollIntoView === "function") btn.scrollIntoView({ behavior: "smooth", block: "center" });
    btn.classList.add("action-highlight");
    setTimeout(() => btn.classList.remove("action-highlight"), 1800);
  }, 50);
}

/**
 * Read URL hash on init and navigate to the referenced surface or action.
 * Surface hash:  #S14       → navigate to S14.
 * Action hash:   #A-S14-009 → navigate to S14 + highlight that action button.
 * Invalid hash   → silently ignored.
 */
function resolveInitialHash() {
  const hash = location.hash.slice(1); // strip leading "#"
  if (!hash) return;
  // Action-id pattern: one or more letters, dash, then surface-id segment (e.g. A-S14-009)
  const actionMatch = hash.match(/^[A-Za-z]+-([A-Z]{1,2}\d+)/);
  if (actionMatch) {
    const sid = actionMatch[1];
    if (surfaceById[sid]) { navigateTo(sid); highlightAction(hash); }
  } else if (surfaceById[hash]) {
    navigateTo(hash);
  }
  // invalid hash → fall through silently
}

// ── Render main surface area ───────────────────────────────────────────────────
function renderMain() {
  if (!currentSurface) return;
  const s = currentSurface;
  // Reset blueprint-link guard so initBlueprintLinks() re-runs for the new surface.
  document.getElementById("blueprint-pre")?.removeAttribute("data-linked");
  const meta = s.meta || {};
  const type = meta.type || "unknown";

  // Update surface card header fields
  document.getElementById("surface-id").textContent = s.id || "?";
  document.getElementById("surface-name").textContent = meta.name || s.file;
  const badge = document.getElementById("surface-type-badge");
  badge.textContent = type;
  badge.className = "type-badge " + typeBadgeClass(type);
  document.getElementById("surface-region-chips").innerHTML =
    (meta.regions || []).map(r => `<span class="region-chip">${esc(r)}</span>`).join("");

  // Errors
  const errEl = document.getElementById("surface-errors");
  if (s.errors && s.errors.length) {
    errEl.textContent = "⚠ " + s.errors.join("; ");
    errEl.style.display = "";
  } else {
    errEl.style.display = "none";
  }

  // Interactions view — stacked region boxes (always rendered; visible via Interactions subtab).
  const layoutDiv = document.getElementById("view-layout");
  layoutDiv.innerHTML = renderLayout(s);
  rewireActionButtons(layoutDiv);  // rewireActionButtons defined in render-grid.js

  // Grid view — CSS grid (Phase 6): rendered when surface has a ui-layout model.
  // Layout subtab shown first and default-active; surfaces without layout fall back to Interactions.
  const gridDiv    = document.getElementById("view-grid");
  const gridSubtab = document.getElementById("subtab-grid");
  if (s.layout && gridDiv) {
    gridDiv.innerHTML = renderGrid(s);  // renderGrid defined in render-grid.js
    rewireActionButtons(gridDiv);
    rewireInspectorHover(gridDiv, s);   // inspector hover — defined in render-grid.js
    if (gridSubtab) gridSubtab.style.display = "";
    switchView("grid");
  } else {
    if (gridDiv)    gridDiv.innerHTML = "";
    if (gridSubtab) gridSubtab.style.display = "none";
    switchView("layout");
  }

  // Blueprint view — original ASCII
  document.getElementById("blueprint-pre").textContent =
    s.asciiLayout || "(no ASCII layout for this surface)";

  // States subtab — ST-* state cards with ERR-* chips (Phase 4)
  document.getElementById("view-states").innerHTML = renderStates(s);

  updateBottomBar();
  // Blueprint ↔ region-box 2-way links (blueprint-link.js)
  initBlueprintLinks();
}

// ── Navigation ────────────────────────────────────────────────────────────────
function navigateTo(surfaceId) {
  const surface = surfaceById[surfaceId];
  if (!surface) { showToast("Surface not found: " + surfaceId); return; }
  if (currentSurface) navStack.push(currentSurface.id);
  currentSurface = surface;
  overlayStack = [];
  closeOverlay();
  renderMain();
  updateBreadcrumb();
  updateBackBtn();
  updateSidebarActive();
  // Sync URL hash without adding a history entry (no back-button spam).
  try { history.replaceState(null, "", "#" + surfaceId); } catch (e) { /* file:// or CSP */ }
}

function goBack() {
  if (overlayStack.length > 0) {
    overlayStack.pop();
    overlayStack.length > 0 ? openOverlayFor(overlayStack[overlayStack.length - 1]) : closeOverlay();
    return;
  }
  if (navStack.length === 0) return;
  currentSurface = surfaceById[navStack.pop()] || currentSurface;
  renderMain();
  updateBreadcrumb();
  updateBackBtn();
  updateSidebarActive();
}

// ── Overlay ───────────────────────────────────────────────────────────────────
function openOverlayFor(surfaceId) {
  const surface = surfaceById[surfaceId] ||
    { id: surfaceId, file: surfaceId, errors: ["Not found"], meta: {}, contract: {} };
  const meta = surface.meta || {};
  const type = meta.type || "unknown";
  const regionChips = (meta.regions || []).map(r => `<span class="region-chip">${esc(r)}</span>`).join("");
  const card = document.getElementById("overlay-card");
  card.innerHTML = `
    <div class="surface-header" style="border-radius:10px 10px 0 0">
      <span class="surface-id">${esc(surface.id || "?")}</span>
      <span class="surface-name">${esc(meta.name || surface.file)}</span>
      <span class="type-badge ${typeBadgeClass(type)}">${esc(type)}</span>
      <span class="region-chips">${regionChips}</span>
    </div>
    <div style="padding:16px 20px">
      ${surface.errors && surface.errors.length
        ? `<div class="surface-errors">⚠ ${esc(surface.errors.join("; "))}</div>` : ""}
      ${renderLayout(surface)}
    </div>`;
  for (const btn of card.querySelectorAll(".action-btn"))
    btn.addEventListener("click", () => handleInteraction(btn));
  for (const chip of card.querySelectorAll(".listener-chip"))
    chip.addEventListener("click", () =>
      showToast("Reaction [" + (chip.dataset.id || "") + "]: " + (chip.getAttribute("title") || ""), 3500));
  document.getElementById("overlay-backdrop").classList.remove("hidden");
  if (!overlayStack.includes(surfaceId)) overlayStack.push(surfaceId);
  updateBackBtn();
}

function closeOverlay() {
  document.getElementById("overlay-backdrop").classList.add("hidden");
  document.getElementById("overlay-card").innerHTML = "";
  overlayStack = [];
  updateBackBtn();
}

// ── Interaction handler ───────────────────────────────────────────────────────
function handleInteraction(btn) {
  const action = btn.dataset.action;
  const target = btn.dataset.target;
  const id = btn.dataset.id || "?";
  switch (action) {
    case "navigate":      navigateTo(target); break;
    case "open_overlay":  openOverlayFor(target); break;
    case "close_overlay":
    case "return_to_invoker": closeOverlay(); break;
    case "mutate":
      showToast("[" + id + "] mutate: " + (btn.querySelector(".meta")?.textContent || target || "self")); break;
    case "emit_event":
      showToast("[" + id + "] emit: " + (target || "event"), 3000); break;
    default:
      showToast("[" + id + "] " + (action || "?") + (target ? ": " + target : ""));
  }
}

// ── Wire static controls ──────────────────────────────────────────────────────
document.getElementById("btn-back").addEventListener("click", goBack);
document.getElementById("btn-toggle-sidebar").addEventListener("click", () =>
  document.getElementById("sidebar").classList.toggle("collapsed"));
document.getElementById("btn-collapse").addEventListener("click", () =>
  document.getElementById("sidebar").classList.add("collapsed"));
document.getElementById("overlay-backdrop").addEventListener("click", e => {
  if (e.target === document.getElementById("overlay-backdrop")) closeOverlay();
});
// Top tabs (Surface/Storyboard/Graph) + surface sub-tabs (Interactions/Blueprint)
for (const tab of document.querySelectorAll(".tab:not([disabled]), .subtab"))
  tab.addEventListener("click", () => switchView(tab.dataset.view));

// ── Wire flow-bar controls (flow-play.js functions) ───────────────────────────
document.getElementById("flow-select")?.addEventListener("change", onFlowSelectChange);
document.getElementById("btn-flow-play")?.addEventListener("click", flowPlay);
document.getElementById("btn-flow-stop")?.addEventListener("click", flowStop);

// ── Init ──────────────────────────────────────────────────────────────────────
// Flow select population + edge-index warm-up handled by flow-play.js (initFlowBar).
// Graph controls (reaction toggle + flow-highlight select) wired by graph-controls.js (initGraphControls).
initFlowBar();
initGraphControls();
buildSidebar();
// Page-level legend (below the card) — single source legendHtml() in render-grid.js.
const pageLegend = document.getElementById("page-legend");
if (pageLegend) pageLegend.innerHTML = legendHtml(true);
const firstScreen = SURFACES.find(s => s.meta?.type === "screen") || SURFACES[0];
if (firstScreen) {
  currentSurface = firstScreen;
  renderMain();
  updateBreadcrumb();
  updateBackBtn();
  updateSidebarActive();
  // Override initial surface if URL hash specifies a different surface or action.
  resolveInitialHash();
} else {
  document.getElementById("view-layout").innerHTML =
    '<p style="color:#9ca3af;padding:40px;text-align:center">No surfaces found. Check spec.config.yaml.</p>';
}

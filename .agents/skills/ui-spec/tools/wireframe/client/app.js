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

// ── Render main surface area ───────────────────────────────────────────────────
function renderMain() {
  if (!currentSurface) return;
  const s = currentSurface;
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

  // Interactions view — region boxes
  document.getElementById("view-layout").innerHTML = renderLayout(s);

  // Blueprint view — original ASCII
  document.getElementById("blueprint-pre").textContent =
    s.asciiLayout || "(no ASCII layout for this surface)";

  // Wire action button clicks
  for (const btn of document.querySelectorAll("#view-layout .action-btn"))
    btn.addEventListener("click", () => handleInteraction(btn));
  // Reaction chips: click → informational toast
  for (const chip of document.querySelectorAll("#view-layout .listener-chip"))
    chip.addEventListener("click", () =>
      showToast("Reaction [" + (chip.dataset.id || "") + "]: " + (chip.getAttribute("title") || ""), 3500));

  updateBottomBar();
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
const firstScreen = SURFACES.find(s => s.meta?.type === "screen") || SURFACES[0];
if (firstScreen) {
  currentSurface = firstScreen;
  renderMain();
  updateBreadcrumb();
  updateBackBtn();
  updateSidebarActive();
} else {
  document.getElementById("view-layout").innerHTML =
    '<p style="color:#9ca3af;padding:40px;text-align:center">No surfaces found. Check spec.config.yaml.</p>';
}

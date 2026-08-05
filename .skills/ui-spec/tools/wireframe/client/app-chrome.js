// wireframe/client/app-chrome.js
// BROWSER: sidebar build, bottom bar, breadcrumb, view tab switching.
// Loaded before app.js; relies on SURFACES, esc, escAttr (region-model.js),
// and navigateTo / currentSurface / currentView / navStack (app.js provides these).
// Wired into DOM by app.js init after DOMContentLoaded equivalent (inline script).

// ── Sidebar ───────────────────────────────────────────────────────────────────
function buildSidebar() {
  const content = document.getElementById("sidebar-content");
  const groups = {};
  for (const s of SURFACES) {
    const type = s.meta?.type || "unknown";
    if (!groups[type]) groups[type] = [];
    groups[type].push(s);
  }
  const order = ["screen","modal","panel","overlay","component","flow","unknown"];
  const sorted = [...new Set([...order, ...Object.keys(groups)])].filter(t => groups[t]);
  let html = "";
  for (const type of sorted) {
    html += `<div class="type-group"><div class="type-label">${esc(type)}s</div>`;
    for (const s of groups[type]) {
      html += `<div class="sidebar-item" data-sid="${escAttr(s.id || "")}">
        <span class="sid-badge">${esc(s.id || "?")}</span>
        <span>${esc(s.meta?.name || s.file)}</span>
      </div>`;
    }
    html += "</div>";
  }
  content.innerHTML = html;

  // Inject search box above the type-groups (prepend so it scrolls with sidebar but stays at top).
  const searchWrap = document.createElement("div");
  searchWrap.className = "sidebar-search";
  searchWrap.innerHTML = `<input id="sidebar-search-input" type="search" placeholder="Search surfaces…" autocomplete="off">`;
  content.prepend(searchWrap);
  document.getElementById("sidebar-search-input")
    ?.addEventListener("input", e => filterSidebar(e.target.value));

  for (const item of content.querySelectorAll(".sidebar-item")) {
    item.addEventListener("click", () => { if (item.dataset.sid) navigateTo(item.dataset.sid); });
  }
}

/**
 * Filter sidebar items by surface id/name substring (case-insensitive).
 * If the raw term matches an action id (via edgeById), also navigates to the owning surface
 * and highlights the action button — Enter not required, it reacts on every keystroke.
 */
function filterSidebar(term) {
  const q = term.trim().toLowerCase();
  for (const item of document.querySelectorAll(".sidebar-item")) {
    const sid  = (item.dataset.sid || "").toLowerCase();
    const name = (item.querySelector("span:last-child")?.textContent || "").toLowerCase();
    item.style.display = (!q || sid.includes(q) || name.includes(q)) ? "" : "none";
  }
  // Action-id exact match: navigate to owning surface + flash the action button.
  if (q && typeof surfaceById !== "undefined") {
    const edge = edgeById(term.trim()); // edgeById is a lazy singleton from region-model.js
    if (edge?.from && surfaceById[edge.from]) {
      navigateTo(edge.from);
      highlightAction(term.trim()); // highlightAction declared in app.js
    }
  }
}

function updateSidebarActive() {
  for (const el of document.querySelectorAll(".sidebar-item"))
    el.classList.toggle("active", el.dataset.sid === currentSurface?.id);
}

// ── Bottom bar ────────────────────────────────────────────────────────────────
function updateBottomBar() {
  const bar = document.getElementById("bottombar");
  if (!currentSurface) { bar.innerHTML = ""; return; }
  const meta = currentSurface.meta || {};
  const rules = Array.isArray(meta.rules) ? meta.rules : [];
  const platforms = Array.isArray(meta.platforms) ? meta.platforms
    : (meta.platforms ? [meta.platforms] : []);
  let html = "";
  if (rules.length)
    html += '<div class="rules-wrap"><span style="color:#94a3b8;margin-right:4px">Rules:</span>'
      + rules.map(r => `<span class="rule-chip">${esc(r)}</span>`).join("") + "</div>";
  if (platforms.length)
    html += '<div class="rules-wrap"><span style="color:#94a3b8;margin-right:4px">Platforms:</span>'
      + platforms.map(p => `<span class="platform-chip">${esc(p)}</span>`).join("") + "</div>";
  if (!html) html = '<span style="color:#94a3b8">—</span>';
  bar.innerHTML = html;
}

// ── Breadcrumb ────────────────────────────────────────────────────────────────
function updateBreadcrumb() {
  const bc = document.getElementById("breadcrumb");
  const crumbs = [...navStack, currentSurface?.id].filter(Boolean);
  bc.innerHTML = crumbs.map((id, i) => {
    const s = surfaceById[id];
    const label = s ? id + (s.meta?.name ? " · " + s.meta.name : "") : id;
    if (i === crumbs.length - 1)
      return `<span class="crumb" style="color:#e2e8f0">${esc(label)}</span>`;
    return `<span class="crumb" data-sid="${escAttr(id)}">${esc(label)}</span><span class="crumb-sep">›</span>`;
  }).join("");
  for (const el of bc.querySelectorAll(".crumb[data-sid]")) {
    el.addEventListener("click", () => {
      const sid = el.dataset.sid;
      const idx = navStack.indexOf(sid);
      if (idx !== -1) { navStack = navStack.slice(0, idx); navigateTo(sid); } // navStack is shared mutable state declared in app.js; slice here truncates to the clicked crumb position
    });
  }
}

function updateBackBtn() {
  document.getElementById("btn-back").disabled =
    navStack.length === 0 && overlayStack.length === 0;
}

// ── View tab switching (Grid / Interactions / Blueprint / States / Storyboard / Graph) ─
function switchView(view) {
  currentView = view;
  // Show only the active view container. Explicit "block" (not "") overrides the CSS
  // `#view-blueprint{display:none}` / `#view-graph{display:none}` ID rules.
  // "grid" (Phase 6) added to the list; element guarded for backward compat.
  for (const v of ["layout", "blueprint", "storyboard", "states", "graph", "grid"]) {
    const el = document.getElementById("view-" + v);
    if (el) el.style.display = v === view ? "block" : "none";
  }

  const toolbar = document.getElementById("graph-toolbar");
  if (toolbar) toolbar.style.display = view === "graph" ? "" : "none";
  const surfaceWrap = document.getElementById("surface-wrap");
  if (surfaceWrap) surfaceWrap.style.display = view === "graph" ? "none" : "";

  // Grid view carries its own legend in the right rail — hide the page-level one there.
  const pageLegend = document.getElementById("page-legend");
  if (pageLegend) pageLegend.style.display = view === "grid" ? "none" : "";

  // "Surface" top tab stays active for all surface sub-views (layout / blueprint / states / grid).
  const isSurfaceView = ["layout", "blueprint", "states", "grid"].includes(view);
  for (const tab of document.querySelectorAll(".tab:not([disabled])"))
    tab.classList.toggle("active", tab.dataset.view === view || (tab.dataset.view === "layout" && isSurfaceView));
  for (const st of document.querySelectorAll(".subtab"))
    st.classList.toggle("active", st.dataset.view === view);
  const subtabBar = document.getElementById("surface-subtabs");
  if (subtabBar) subtabBar.style.display = isSurfaceView ? "" : "none";

  if (view === "storyboard") {
    const sel = document.getElementById("flow-select");
    populateStoryboard(sel && sel.value ? surfaceById[sel.value] : null);
  }

  // When switching to graph, render it (renderGraph defined in render-graph.js)
  if (view === "graph") renderAndInsertGraph();
}

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
  for (const item of content.querySelectorAll(".sidebar-item")) {
    item.addEventListener("click", () => { if (item.dataset.sid) navigateTo(item.dataset.sid); });
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

// ── View tab switching (Layout / Blueprint / Storyboard / Graph) ─────────────
function switchView(view) {
  currentView = view;
  // Show only the active view container. Explicit "block" (not "") overrides the CSS
  // `#view-blueprint{display:none}` / `#view-graph{display:none}` ID rules.
  for (const v of ["layout", "blueprint", "storyboard", "graph"])
    document.getElementById("view-" + v).style.display = v === view ? "block" : "none";

  const toolbar = document.getElementById("graph-toolbar");
  if (toolbar) toolbar.style.display = view === "graph" ? "" : "none";
  const surfaceWrap = document.getElementById("surface-wrap");
  if (surfaceWrap) surfaceWrap.style.display = view === "graph" ? "none" : "";

  // Top tabs are scopes: "Surface" (data-view "layout") stays active for all surface sub-views.
  const isSurfaceView = view === "layout" || view === "blueprint";
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

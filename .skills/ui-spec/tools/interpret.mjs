// interpret.mjs — Runtime wireframe interpreter for ui-spec.
// Reads all spec files, generates a self-contained interactive HTML wireframe,
// and opens it in the default browser.
//
// Usage:
//   node interpret.mjs [--root <spec-root>]
//
// Add to package.json scripts: "interpret": "node interpret.mjs"

import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { exec } from "node:child_process";
import { specRoot, contractTag } from "./config.mjs";
import { extractAll } from "./extract.mjs";

// ─── Prose extraction ────────────────────────────────────────────────────────

/** Strip frontmatter (---...---) and contract fenced block from raw markdown.
 *  Returns remaining prose text. */
function extractProse(raw) {
  // Strip frontmatter
  let text = raw.replace(/^---[\s\S]*?---\n?/, "");
  // Strip fenced contract block(s): ```yaml <contractTag> ... ```
  const fenceRe = new RegExp("```yaml\\s+" + contractTag + "[\\s\\S]*?```", "g");
  text = text.replace(fenceRe, "");
  return text;
}

/** Find the first ASCII art block in prose.
 *  Looks for lines containing box-drawing chars or +--+ table patterns. */
function findAsciiBlock(prose) {
  const lines = prose.split("\n");
  const boxChars = /[┌┐└┘│─┬┴├┤┼╔╗╚╝║═]/;
  const pseudoBox = /\+[-=+]{2,}/;

  let blockStart = -1;
  let blockEnd = -1;
  let inBlock = false;

  for (let i = 0; i < lines.length; i++) {
    const hasBox = boxChars.test(lines[i]) || pseudoBox.test(lines[i]);
    if (hasBox && !inBlock) {
      blockStart = i;
      inBlock = true;
    } else if (inBlock && !hasBox && lines[i].trim() === "" ) {
      // Allow one blank line inside block
      if (i + 1 < lines.length && (boxChars.test(lines[i + 1]) || pseudoBox.test(lines[i + 1]))) {
        continue; // keep going
      }
      blockEnd = i;
      break;
    }
  }

  if (blockStart === -1) return null;
  if (blockEnd === -1) blockEnd = lines.length;

  // Include a few lines before/after for context
  const start = Math.max(0, blockStart - 1);
  const end = Math.min(lines.length, blockEnd + 1);
  return lines.slice(start, end).join("\n");
}

// ─── Build surface data ───────────────────────────────────────────────────────

function buildSurfaceData() {
  const surfaces = [];
  for (const item of extractAll()) {
    const rawPath = join(specRoot, item.file.replace(/\//g, require_sep()));
    let prose = "";
    let asciiLayout = null;
    try {
      const raw = readFileSync(rawPath, "utf8");
      prose = extractProse(raw);
      asciiLayout = findAsciiBlock(prose);
    } catch { /* file unreadable, skip prose */ }

    surfaces.push({
      file: item.file,
      id: item.id,
      meta: item.meta,
      contract: item.contract,
      prose,
      asciiLayout,
      errors: item.errors,
    });
  }
  return surfaces;
}

function require_sep() {
  return process.platform === "win32" ? "\\" : "/";
}

// ─── HTML template ────────────────────────────────────────────────────────────

function buildHtml(surfaces) {
  const dataJson = JSON.stringify(surfaces, null, 2);

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UI Spec Wireframe</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; font-size: 14px; background: #f0f2f5; color: #1a1a1a; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

  /* ── Top bar ── */
  #topbar { background: #1e293b; color: #e2e8f0; display: flex; align-items: center; gap: 8px; padding: 0 12px; height: 44px; flex-shrink: 0; z-index: 100; }
  #topbar h1 { font-size: 13px; font-weight: 600; color: #94a3b8; letter-spacing: .05em; margin-right: 8px; }
  #breadcrumb { display: flex; align-items: center; gap: 4px; flex: 1; overflow: hidden; }
  .crumb { font-size: 12px; color: #94a3b8; cursor: pointer; white-space: nowrap; }
  .crumb:hover { color: #e2e8f0; }
  .crumb-sep { color: #475569; font-size: 11px; }
  #btn-back { background: #334155; border: none; color: #94a3b8; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }
  #btn-back:hover { background: #475569; color: #e2e8f0; }
  #btn-back:disabled { opacity: .4; cursor: default; }

  /* ── Body layout ── */
  #layout { display: flex; flex: 1; overflow: hidden; }

  /* ── Sidebar ── */
  #sidebar { width: 220px; background: #fff; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; flex-shrink: 0; overflow: hidden; transition: width .2s; }
  #sidebar.collapsed { width: 0; }
  #sidebar-header { padding: 8px 12px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
  #sidebar-header span { font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: .06em; }
  #btn-collapse { background: none; border: none; cursor: pointer; font-size: 16px; color: #94a3b8; padding: 0 2px; }
  #sidebar-content { overflow-y: auto; flex: 1; padding: 8px 0; }
  .type-group { margin-bottom: 4px; }
  .type-label { font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: .08em; padding: 4px 12px 2px; }
  .sidebar-item { padding: 5px 12px; cursor: pointer; font-size: 12px; color: #374151; display: flex; align-items: center; gap: 6px; }
  .sidebar-item:hover { background: #f1f5f9; }
  .sidebar-item.active { background: #eff6ff; color: #1d4ed8; font-weight: 600; }
  .sid-badge { font-size: 10px; color: #94a3b8; font-family: monospace; }

  /* ── Main content ── */
  #main { flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative; }
  #surface-wrap { flex: 1; overflow-y: auto; padding: 24px; }

  /* ── Surface card ── */
  .surface-card { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,.1); max-width: 900px; margin: 0 auto; }
  .surface-header { padding: 14px 20px 10px; border-bottom: 1px solid #f1f5f9; display: flex; align-items: center; gap: 10px; }
  .surface-id { font-family: monospace; font-size: 13px; font-weight: 700; color: #374151; }
  .surface-name { font-size: 16px; font-weight: 600; color: #111827; }
  .type-badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 9999px; text-transform: uppercase; letter-spacing: .06em; }
  .badge-screen   { background: #dbeafe; color: #1d4ed8; }
  .badge-modal    { background: #e5e7eb; color: #374151; }
  .badge-panel    { background: #d1fae5; color: #065f46; }
  .badge-overlay  { background: #fef3c7; color: #92400e; }
  .badge-component{ background: #ede9fe; color: #5b21b6; }
  .badge-flow     { background: #fce7f3; color: #9d174d; }
  .badge-default  { background: #f3f4f6; color: #374151; }

  /* ── ASCII layout ── */
  .ascii-wrap { padding: 16px 20px; border-bottom: 1px solid #f1f5f9; }
  .ascii-wrap pre { font-family: 'Courier New', Courier, monospace; font-size: 12px; line-height: 1.5; color: #1f2937; white-space: pre; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 4px; padding: 12px; overflow-x: auto; }
  .ascii-title { font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px; }

  /* ── Interactions ── */
  .interactions-wrap { padding: 16px 20px; }
  .interactions-title { font-size: 11px; font-weight: 600; color: #6b7280; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 10px; }
  .interaction-grid { display: flex; flex-wrap: wrap; gap: 8px; }
  .action-btn { border: none; border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: filter .1s, transform .1s; position: relative; }
  .action-btn:hover { filter: brightness(1.08); transform: translateY(-1px); }
  .action-btn:active { transform: translateY(0); filter: brightness(.95); }
  .btn-navigate    { background: #dbeafe; color: #1d4ed8; }
  .btn-open_overlay{ background: #ede9fe; color: #5b21b6; }
  .btn-close_overlay,
  .btn-return_to_invoker { background: #fee2e2; color: #991b1b; }
  .btn-mutate      { background: #ffedd5; color: #9a3412; }
  .btn-emit_event  { background: #dcfce7; color: #166534; }
  .btn-external    { background: #f3f4f6; color: #374151; }
  .btn-default     { background: #f3f4f6; color: #374151; }
  .guard-badge { font-size: 10px; background: rgba(0,0,0,.1); border-radius: 3px; padding: 1px 5px; color: inherit; }
  .region-tag { font-size: 10px; color: #9ca3af; font-family: monospace; }
  .no-interactions { color: #9ca3af; font-size: 12px; font-style: italic; padding: 4px 0; }

  /* ── Surface errors ── */
  .surface-errors { margin: 12px 20px; padding: 8px 12px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 4px; font-size: 12px; color: #b91c1c; }

  /* ── Bottom bar ── */
  #bottombar { background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 6px 16px; display: flex; align-items: center; gap: 12px; flex-shrink: 0; font-size: 11px; color: #64748b; flex-wrap: wrap; }
  .rules-wrap { display: flex; gap: 4px; align-items: center; }
  .rule-chip { background: #e0f2fe; color: #075985; border-radius: 3px; padding: 1px 6px; font-family: monospace; font-size: 10px; }
  .platform-chip { background: #f3f4f6; color: #374151; border-radius: 3px; padding: 1px 6px; font-size: 10px; }

  /* ── Modal overlay ── */
  #overlay-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,.45); backdrop-filter: blur(2px); display: flex; align-items: center; justify-content: center; z-index: 200; animation: fadeIn .15s ease; }
  #overlay-backdrop.hidden { display: none; }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  #overlay-card { background: #fff; border-radius: 10px; box-shadow: 0 20px 60px rgba(0,0,0,.3); width: 90%; max-width: 700px; max-height: 85vh; overflow-y: auto; animation: slideUp .15s ease; }
  @keyframes slideUp { from { transform: translateY(12px); opacity: .6; } to { transform: translateY(0); opacity: 1; } }

  /* ── Toast ── */
  #toast { position: fixed; bottom: 60px; left: 50%; transform: translateX(-50%); background: #1e293b; color: #e2e8f0; padding: 8px 20px; border-radius: 6px; font-size: 12px; z-index: 300; opacity: 0; transition: opacity .2s; pointer-events: none; white-space: nowrap; }
  #toast.show { opacity: 1; }

  /* ── Flash animation ── */
  @keyframes flash { 0%{background:#fff} 30%{background:#fef9c3} 100%{background:#fff} }
  .surface-card.flash { animation: flash .6s ease; }

  /* ── Info panel ── */
  #info-panel { position: fixed; top: 44px; right: 0; width: 280px; background: #fff; border-left: 1px solid #e2e8f0; box-shadow: -4px 0 12px rgba(0,0,0,.08); height: calc(100vh - 44px); overflow-y: auto; z-index: 150; transform: translateX(100%); transition: transform .2s; padding: 16px; }
  #info-panel.open { transform: translateX(0); }
  #info-panel h3 { font-size: 13px; font-weight: 700; color: #374151; margin-bottom: 10px; display: flex; justify-content: space-between; }
  #btn-close-info { background: none; border: none; cursor: pointer; font-size: 18px; color: #94a3b8; }
  .info-row { margin-bottom: 8px; font-size: 12px; }
  .info-label { font-weight: 600; color: #6b7280; margin-bottom: 2px; }
  .info-value { color: #374151; font-family: monospace; }

  /* ── Topbar controls ── */
  #topbar-right { display: flex; align-items: center; gap: 6px; margin-left: auto; }
  .icon-btn { background: #334155; border: none; color: #94a3b8; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 13px; }
  .icon-btn:hover { background: #475569; color: #e2e8f0; }

  /* ── Flow mode ── */
  #flow-bar { background: #1e3a5f; border-top: 1px solid #2d4a6e; color: #bfdbfe; padding: 6px 16px; display: flex; align-items: center; gap: 10px; font-size: 12px; flex-shrink: 0; }
  #flow-bar.hidden { display: none; }
  #flow-select { background: #0f2744; color: #bfdbfe; border: 1px solid #2d4a6e; border-radius: 4px; padding: 3px 8px; font-size: 12px; cursor: pointer; }
  .flow-step { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 3px; }
  .flow-step.active { background: #1d4ed8; color: #fff; }
  .flow-step.done { background: #065f46; color: #d1fae5; }
  #btn-flow-play { background: #1d4ed8; border: none; color: #fff; padding: 3px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; }
  #btn-flow-play:hover { background: #1e40af; }
  #btn-flow-stop { background: #475569; border: none; color: #e2e8f0; padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }

  /* ── Sidebar toggle btn when collapsed ── */
  #btn-open-sidebar { display: none; }
  #sidebar.collapsed ~ * #btn-open-sidebar { display: inline-flex; }
</style>
</head>
<body>

<div id="topbar">
  <h1>ui-spec</h1>
  <button id="btn-back" disabled>← Back</button>
  <div id="breadcrumb"></div>
  <div id="topbar-right">
    <button class="icon-btn" id="btn-toggle-sidebar" title="Toggle sidebar">☰</button>
    <button class="icon-btn" id="btn-toggle-info" title="Surface info">ℹ</button>
    <button class="icon-btn" id="btn-toggle-flow" title="Flow mode">▶ Flow</button>
  </div>
</div>

<div id="flow-bar" class="hidden">
  <span>Flow:</span>
  <select id="flow-select"><option value="">— select —</option></select>
  <span id="flow-steps"></span>
  <button id="btn-flow-play">Play</button>
  <button id="btn-flow-stop">Stop</button>
</div>

<div id="layout">
  <div id="sidebar">
    <div id="sidebar-header">
      <span>Surfaces</span>
      <button id="btn-collapse" title="Collapse">‹</button>
    </div>
    <div id="sidebar-content" id="sidebar-list"></div>
  </div>

  <div id="main">
    <div id="surface-wrap">
      <div id="surface-root"></div>
    </div>
    <div id="bottombar"></div>
  </div>
</div>

<div id="overlay-backdrop" class="hidden">
  <div id="overlay-card"></div>
</div>

<div id="info-panel">
  <h3>Surface Info <button id="btn-close-info">×</button></h3>
  <div id="info-content"></div>
</div>

<div id="toast"></div>

<script>
// ── Embedded spec data ────────────────────────────────────────────────────────
const SURFACES = ${dataJson};

// ── Index by ID ───────────────────────────────────────────────────────────────
const surfaceById = {};
for (const s of SURFACES) {
  if (s.id) surfaceById[s.id] = s;
}

// ── State ─────────────────────────────────────────────────────────────────────
let navStack = [];           // [{id, name}]
let currentSurface = null;
let overlayStack = [];       // stack of surface IDs shown as overlay
let flowActive = null;       // {steps: [{surfaceId, actionId}], idx: number, timer}

// ── Helpers ───────────────────────────────────────────────────────────────────
function typeBadgeClass(type) {
  const map = { screen:'badge-screen', modal:'badge-modal', panel:'badge-panel',
                overlay:'badge-overlay', component:'badge-component', flow:'badge-flow' };
  return map[type] || 'badge-default';
}

function actionBtnClass(action, target) {
  if (action === 'close_overlay' || target === 'return_to_invoker' || action === 'return_to_invoker') return 'btn-close_overlay';
  const map = { navigate:'btn-navigate', open_overlay:'btn-open_overlay',
                mutate:'btn-mutate', emit_event:'btn-emit_event', external:'btn-external' };
  return map[action] || 'btn-default';
}

function showToast(msg, duration = 2800) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), duration);
}

// ── Render surface card ───────────────────────────────────────────────────────
function renderCard(surface, container, isOverlay = false) {
  if (!surface) {
    container.innerHTML = '<p style="color:#9ca3af;padding:20px">Surface not found.</p>';
    return;
  }
  const meta = surface.meta || {};
  const contract = surface.contract || {};
  const interactions = contract.interactions || [];
  const type = meta.type || 'screen';

  let html = \`<div class="surface-card" id="surface-card-\${isOverlay ? 'ov' : 'main'}">
    <div class="surface-header">
      <span class="surface-id">\${surface.id || '?'}</span>
      <span class="surface-name">\${meta.name || surface.file}</span>
      <span class="type-badge \${typeBadgeClass(type)}">\${type}</span>
    </div>\`;

  // Errors
  if (surface.errors && surface.errors.length) {
    html += \`<div class="surface-errors">⚠ \${surface.errors.join('; ')}</div>\`;
  }

  // ASCII layout
  if (surface.asciiLayout) {
    html += \`<div class="ascii-wrap"><div class="ascii-title">Layout</div><pre>\${escHtml(surface.asciiLayout)}</pre></div>\`;
  }

  // Interactions
  html += '<div class="interactions-wrap"><div class="interactions-title">Interactions</div><div class="interaction-grid">';
  if (interactions.length === 0) {
    html += '<span class="no-interactions">No interactions defined</span>';
  } else {
    for (const ix of interactions) {
      const cls = actionBtnClass(ix.action, ix.target);
      const guardBadge = ix.guard ? \`<span class="guard-badge" title="Guard: \${escAttr(ix.guard)}">if</span>\` : '';
      const regionTag = ix.region ? \`<span class="region-tag">[\${ix.region}]</span>\` : '';
      const label = ix.element || ix.id || '?';
      html += \`<button class="action-btn \${cls}"
        data-action="\${escAttr(ix.action || '')}"
        data-target="\${escAttr(ix.target || '')}"
        data-id="\${escAttr(ix.id || '')}"
        data-surface="\${escAttr(surface.id || '')}"
        title="\${escAttr(formatInteractionTitle(ix))}"
      >\${escHtml(label)}\${guardBadge}\${regionTag}</button>\`;
    }
  }
  html += '</div></div></div>';
  container.innerHTML = html;

  // Attach click handlers
  for (const btn of container.querySelectorAll('.action-btn')) {
    btn.addEventListener('click', () => handleInteraction(btn));
  }
}

function formatInteractionTitle(ix) {
  let s = \`[\${ix.id || '?'}] \${ix.trigger || ''} → \${ix.action || ''}\`;
  if (ix.target) s += ' → ' + ix.target;
  if (ix.guard) s += \`  (if: \${ix.guard})\`;
  return s;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function escAttr(s) {
  return String(s).replace(/"/g,'&quot;');
}

// ── Navigation ────────────────────────────────────────────────────────────────
function navigateTo(surfaceId) {
  const surface = surfaceById[surfaceId];
  if (!surface) { showToast(\`Surface \${surfaceId} not found\`); return; }

  if (currentSurface) navStack.push(currentSurface.id);
  currentSurface = surface;
  overlayStack = [];
  closeOverlay();
  renderMain();
  updateBreadcrumb();
  updateBackBtn();
  updateSidebarActive();
  updateBottomBar();
  updateInfoPanel();
}

function goBack() {
  if (overlayStack.length > 0) {
    overlayStack.pop();
    if (overlayStack.length > 0) {
      openOverlayFor(overlayStack[overlayStack.length - 1]);
    } else {
      closeOverlay();
    }
    return;
  }
  if (navStack.length === 0) return;
  const prevId = navStack.pop();
  currentSurface = surfaceById[prevId] || currentSurface;
  renderMain();
  updateBreadcrumb();
  updateBackBtn();
  updateSidebarActive();
  updateBottomBar();
  updateInfoPanel();
}

function renderMain() {
  const root = document.getElementById('surface-root');
  renderCard(currentSurface, root, false);
}

// ── Overlay ───────────────────────────────────────────────────────────────────
function openOverlayFor(surfaceId) {
  const surface = surfaceById[surfaceId];
  const backdrop = document.getElementById('overlay-backdrop');
  const card = document.getElementById('overlay-card');
  renderCard(surface || { id: surfaceId, file: surfaceId, errors: ['Not found'], meta: {}, contract: {} }, card, true);
  backdrop.classList.remove('hidden');
  if (!overlayStack.includes(surfaceId)) overlayStack.push(surfaceId);
  updateBackBtn();
}

function closeOverlay() {
  document.getElementById('overlay-backdrop').classList.add('hidden');
  document.getElementById('overlay-card').innerHTML = '';
  overlayStack = [];
  updateBackBtn();
}

// ── Handle button click ───────────────────────────────────────────────────────
function handleInteraction(btn) {
  const action = btn.dataset.action;
  const target = btn.dataset.target;

  switch (action) {
    case 'navigate':
      navigateTo(target);
      break;

    case 'open_overlay':
      openOverlayFor(target);
      break;

    case 'close_overlay':
    case 'return_to_invoker':
      closeOverlay();
      break;

    case 'mutate': {
      const card = document.getElementById('surface-card-main');
      if (card) { card.classList.remove('flash'); void card.offsetWidth; card.classList.add('flash'); }
      showToast(\`Mutate: \${target || 'self'}\`);
      break;
    }

    case 'emit_event': {
      // Find surfaces listening to this event
      const listeners = SURFACES.filter(s => {
        const lt = s.meta?.listens_to;
        if (!lt) return false;
        if (Array.isArray(lt)) return lt.includes(target);
        return lt === target;
      });
      const lNames = listeners.map(s => s.id || s.file).join(', ') || 'none';
      showToast(\`Event: \${target} → listened by: \${lNames}\`, 3500);
      break;
    }

    case 'external':
      showToast(\`External: \${target}\`);
      break;

    default:
      showToast(\`\${action}: \${target || 'self'}\`);
  }
}

// ── Breadcrumb ────────────────────────────────────────────────────────────────
function updateBreadcrumb() {
  const bc = document.getElementById('breadcrumb');
  const crumbs = [...navStack, currentSurface?.id].filter(Boolean);
  bc.innerHTML = crumbs.map((id, i) => {
    const s = surfaceById[id];
    const label = s ? \`\${id} \${s.meta?.name ? '· ' + s.meta.name : ''}\` : id;
    if (i === crumbs.length - 1) return \`<span class="crumb" style="color:#e2e8f0">\${escHtml(label)}</span>\`;
    return \`<span class="crumb" data-sid="\${id}">\${escHtml(label)}</span><span class="crumb-sep">›</span>\`;
  }).join('');
  for (const el of bc.querySelectorAll('.crumb[data-sid]')) {
    el.addEventListener('click', () => {
      const sid = el.dataset.sid;
      // Pop stack to this point
      const idx = navStack.indexOf(sid);
      if (idx !== -1) { navStack = navStack.slice(0, idx); navigateTo(sid); }
    });
  }
}

function updateBackBtn() {
  const btn = document.getElementById('btn-back');
  btn.disabled = navStack.length === 0 && overlayStack.length === 0;
}

// ── Bottom bar ────────────────────────────────────────────────────────────────
function updateBottomBar() {
  const bar = document.getElementById('bottombar');
  if (!currentSurface) { bar.innerHTML = ''; return; }
  const meta = currentSurface.meta || {};
  const rules = Array.isArray(meta.rules) ? meta.rules : [];
  const platforms = Array.isArray(meta.platforms) ? meta.platforms : (meta.platforms ? [meta.platforms] : []);
  const hosts = Array.isArray(meta.hosts) ? meta.hosts : [];

  let html = '';
  if (rules.length) {
    html += '<div class="rules-wrap"><span style="color:#94a3b8;margin-right:4px">Rules:</span>' +
      rules.map(r => \`<span class="rule-chip">\${escHtml(r)}</span>\`).join('') + '</div>';
  }
  if (platforms.length) {
    html += '<div class="rules-wrap"><span style="color:#94a3b8;margin-right:4px">Platforms:</span>' +
      platforms.map(p => \`<span class="platform-chip">\${escHtml(p)}</span>\`).join('') + '</div>';
  }
  if (hosts.length) {
    html += '<div class="rules-wrap"><span style="color:#94a3b8;margin-right:4px">Hosts:</span>' +
      hosts.map(h => \`<span class="platform-chip">\${escHtml(String(h))}</span>\`).join('') + '</div>';
  }
  if (!html) html = '<span style="color:#cbd5e1">No metadata</span>';
  bar.innerHTML = html;
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
function buildSidebar() {
  const content = document.getElementById('sidebar-content');
  const groups = {};
  for (const s of SURFACES) {
    const type = s.meta?.type || 'unknown';
    if (!groups[type]) groups[type] = [];
    groups[type].push(s);
  }

  // Order: screen, modal, panel, overlay, component, flow, unknown
  const order = ['screen','modal','panel','overlay','component','flow','unknown'];
  const sorted = [...new Set([...order, ...Object.keys(groups)])].filter(t => groups[t]);

  let html = '';
  for (const type of sorted) {
    html += \`<div class="type-group"><div class="type-label">\${type}s</div>\`;
    for (const s of groups[type]) {
      html += \`<div class="sidebar-item" data-sid="\${escAttr(s.id || '')}">
        <span class="sid-badge">\${escHtml(s.id || '?')}</span>
        <span>\${escHtml(s.meta?.name || s.file)}</span>
      </div>\`;
    }
    html += '</div>';
  }
  content.innerHTML = html;

  for (const item of content.querySelectorAll('.sidebar-item')) {
    item.addEventListener('click', () => {
      const sid = item.dataset.sid;
      if (sid) navigateTo(sid);
    });
  }
}

function updateSidebarActive() {
  for (const el of document.querySelectorAll('.sidebar-item')) {
    el.classList.toggle('active', el.dataset.sid === currentSurface?.id);
  }
}

// ── Info panel ────────────────────────────────────────────────────────────────
function updateInfoPanel() {
  const panel = document.getElementById('info-content');
  if (!currentSurface) { panel.innerHTML = ''; return; }
  const meta = currentSurface.meta || {};
  const contract = currentSurface.contract || {};
  const interactions = contract.interactions || [];

  // Connected surfaces (navigate/open_overlay targets)
  const connected = [...new Set(interactions
    .filter(ix => ['navigate','open_overlay'].includes(ix.action) && ix.target && !ix.target.startsWith('external:'))
    .map(ix => ix.target))];

  let html = \`
    <div class="info-row"><div class="info-label">ID</div><div class="info-value">\${escHtml(meta.id || '—')}</div></div>
    <div class="info-row"><div class="info-label">Type</div><div class="info-value">\${escHtml(meta.type || '—')}</div></div>
    <div class="info-row"><div class="info-label">File</div><div class="info-value" style="font-size:11px">\${escHtml(currentSurface.file)}</div></div>
    <div class="info-row"><div class="info-label">Status</div><div class="info-value">\${escHtml(meta.status || '—')}</div></div>
    <div class="info-row"><div class="info-label">Platforms</div><div class="info-value">\${escHtml(JSON.stringify(meta.platforms || []))}</div></div>
    <div class="info-row"><div class="info-label">Regions</div><div class="info-value">\${escHtml(JSON.stringify(meta.regions || []))}</div></div>
    <div class="info-row"><div class="info-label">Rules</div><div class="info-value">\${escHtml(JSON.stringify(meta.rules || []))}</div></div>
    <div class="info-row"><div class="info-label">Interactions</div><div class="info-value">\${interactions.length}</div></div>
    <div class="info-row"><div class="info-label">Connected to</div><div class="info-value">\${escHtml(connected.join(', ') || 'none')}</div></div>
  \`;
  if (currentSurface.errors?.length) {
    html += \`<div class="info-row"><div class="info-label" style="color:#dc2626">Errors</div><div class="info-value" style="color:#dc2626">\${escHtml(currentSurface.errors.join('; '))}</div></div>\`;
  }
  panel.innerHTML = html;
}

// ── Flow mode ─────────────────────────────────────────────────────────────────
function buildFlowSelector() {
  const sel = document.getElementById('flow-select');
  const flowSurfaces = SURFACES.filter(s => s.meta?.type === 'flow');
  for (const f of flowSurfaces) {
    const opt = document.createElement('option');
    opt.value = f.id;
    opt.textContent = \`\${f.id} — \${f.meta?.name || f.file}\`;
    sel.appendChild(opt);
  }
  sel.addEventListener('change', () => loadFlow(sel.value));
}

function loadFlow(flowId) {
  if (!flowId) { document.getElementById('flow-steps').innerHTML = ''; flowActive = null; return; }
  const surface = surfaceById[flowId];
  if (!surface) return;
  const steps = surface.contract?.flow?.steps || [];
  flowActive = { steps, idx: -1, timer: null };
  renderFlowSteps();
}

function renderFlowSteps() {
  const wrap = document.getElementById('flow-steps');
  if (!flowActive) { wrap.innerHTML = ''; return; }
  wrap.innerHTML = flowActive.steps.map((step, i) => {
    let cls = 'flow-step';
    if (i === flowActive.idx) cls += ' active';
    else if (i < flowActive.idx) cls += ' done';
    return \`<span class="\${cls}">\${escHtml(typeof step === 'string' ? step : step.surface || step.id || JSON.stringify(step))}</span>\`;
  }).join('<span style="color:#4b6ea8;padding:0 2px">→</span>');
}

function playFlow() {
  if (!flowActive) return;
  if (flowActive.timer) clearInterval(flowActive.timer);
  flowActive.idx = 0;
  advanceFlowStep();
  flowActive.timer = setInterval(() => {
    flowActive.idx++;
    if (flowActive.idx >= flowActive.steps.length) {
      clearInterval(flowActive.timer);
      flowActive.timer = null;
      showToast('Flow complete');
    } else {
      advanceFlowStep();
    }
    renderFlowSteps();
  }, 1500);
}

function advanceFlowStep() {
  const step = flowActive.steps[flowActive.idx];
  if (!step) return;
  const raw = typeof step === 'string' ? step : (step.surface || step.id || '');
  // Action IDs are A-{SURFACE}-{seq} (e.g. A-S01-002) — extract surface prefix
  const fromAction = raw.match(/^A-([A-Z][0-9]+)-/);
  const sid = fromAction ? fromAction[1] : raw;
  if (sid && surfaceById[sid]) navigateTo(sid);
  renderFlowSteps();
}

// ── Wire controls ─────────────────────────────────────────────────────────────
document.getElementById('btn-back').addEventListener('click', goBack);

document.getElementById('btn-toggle-sidebar').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('collapsed');
});

document.getElementById('btn-collapse').addEventListener('click', () => {
  document.getElementById('sidebar').classList.add('collapsed');
});

document.getElementById('btn-toggle-info').addEventListener('click', () => {
  document.getElementById('info-panel').classList.toggle('open');
});

document.getElementById('btn-close-info').addEventListener('click', () => {
  document.getElementById('info-panel').classList.remove('open');
});

document.getElementById('btn-toggle-flow').addEventListener('click', () => {
  document.getElementById('flow-bar').classList.toggle('hidden');
});

document.getElementById('btn-flow-play').addEventListener('click', playFlow);

document.getElementById('btn-flow-stop').addEventListener('click', () => {
  if (flowActive?.timer) { clearInterval(flowActive.timer); flowActive.timer = null; }
  if (flowActive) { flowActive.idx = -1; renderFlowSteps(); }
});

document.getElementById('overlay-backdrop').addEventListener('click', (e) => {
  if (e.target === document.getElementById('overlay-backdrop')) closeOverlay();
});

// ── Init ──────────────────────────────────────────────────────────────────────
buildSidebar();
buildFlowSelector();

// Navigate to first screen-type surface, or just the first surface
const firstScreen = SURFACES.find(s => s.meta?.type === 'screen') || SURFACES[0];
if (firstScreen) {
  currentSurface = firstScreen;
  renderMain();
  updateBreadcrumb();
  updateBackBtn();
  updateSidebarActive();
  updateBottomBar();
  updateInfoPanel();
} else {
  document.getElementById('surface-root').innerHTML =
    '<p style="color:#9ca3af;padding:40px;text-align:center">No surfaces found. Check your spec.config.yaml and surface directories.</p>';
}
</script>
</body>
</html>`;
}

// ─── Open in browser ──────────────────────────────────────────────────────────

function openBrowser(filePath) {
  const normalized = filePath.replace(/\\/g, "/");
  const fileUrl = `file:///${normalized}`;
  const cmd =
    process.platform === "win32" ? `start "" "${fileUrl}"` :
    process.platform === "darwin" ? `open "${fileUrl}"` :
    `xdg-open "${fileUrl}"`;
  exec(cmd, (err) => {
    if (err) console.warn("Could not open browser automatically:", err.message);
  });
}

// ─── Main ─────────────────────────────────────────────────────────────────────

console.log(`ui-spec interpret — reading spec from: ${specRoot}`);

const surfaces = buildSurfaceData();
console.log(`  Found ${surfaces.length} surface(s)`);

const genDir = join(specRoot, "generated");
if (!existsSync(genDir)) mkdirSync(genDir, { recursive: true });

const outPath = join(genDir, "wireframe.html");
const html = buildHtml(surfaces);
writeFileSync(outPath, html, "utf8");

console.log(`  Wireframe written: ${outPath}`);
console.log("  Opening in browser...");
openBrowser(outPath);

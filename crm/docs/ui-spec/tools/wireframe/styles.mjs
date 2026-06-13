// wireframe/styles.mjs
// NODE: exports combined CSS string for wireframe-v2.html.
// Phase 1 chrome styles; Phase 2 additions in styles-phase2.mjs.
// Sources: mockup s01-regionbox-mockup.html (region-box styles)
//          + interpret.mjs chrome styles (sidebar/breadcrumb/overlay/topbar/toast/bottombar).

import { CSS2 } from "./styles-phase2.mjs";
import { CSS3 } from "./styles-phase3.mjs";

const CSS1 = `
*,*::before,*::after { box-sizing:border-box; margin:0; padding:0; }
body { font-family:system-ui,Segoe UI,sans-serif; font-size:14px; background:#f0f2f5;
       color:#1a1a1a; height:100vh; display:flex; flex-direction:column; overflow:hidden; }

/* ── Topbar ── */
#topbar { background:#1e293b; color:#e2e8f0; display:flex; align-items:center; gap:8px;
          padding:0 12px; height:46px; flex-shrink:0; z-index:100; }
#topbar h1 { font-size:13px; font-weight:600; color:#94a3b8; letter-spacing:.05em; }
.tabs { display:flex; gap:4px; margin-left:8px; }
.tab { background:#334155; border:none; color:#cbd5e1; padding:5px 12px; border-radius:5px;
       cursor:pointer; font-size:12px; }
.tab:hover { background:#475569; }
.tab.active { background:#2563eb; color:#fff; }
.tab[disabled] { opacity:.45; cursor:not-allowed; }
#topbar-right { display:flex; align-items:center; gap:6px; margin-left:auto; }
.icon-btn { background:#334155; border:none; color:#94a3b8; padding:4px 8px; border-radius:4px;
            cursor:pointer; font-size:13px; }
.icon-btn:hover { background:#475569; color:#e2e8f0; }
#btn-back { background:#334155; border:none; color:#94a3b8; padding:4px 10px; border-radius:4px;
            cursor:pointer; font-size:12px; }
#btn-back:hover { background:#475569; color:#e2e8f0; }
#btn-back:disabled { opacity:.4; cursor:default; }
#breadcrumb { display:flex; align-items:center; gap:4px; flex:1; overflow:hidden; }
.crumb { font-size:12px; color:#94a3b8; cursor:pointer; white-space:nowrap; }
.crumb:hover { color:#e2e8f0; }
.crumb-sep { color:#475569; font-size:11px; }

/* ── Body layout ── */
#layout { display:flex; flex:1; overflow:hidden; }

/* ── Sidebar ── */
#sidebar { width:220px; background:#fff; border-right:1px solid #e2e8f0; display:flex;
           flex-direction:column; flex-shrink:0; overflow:hidden; transition:width .2s; }
#sidebar.collapsed { width:0; }
#sidebar-header { padding:8px 12px; background:#f8fafc; border-bottom:1px solid #e2e8f0;
                  display:flex; justify-content:space-between; align-items:center; }
#sidebar-header span { font-size:11px; font-weight:600; color:#64748b;
                       text-transform:uppercase; letter-spacing:.06em; }
#btn-collapse { background:none; border:none; cursor:pointer; font-size:16px;
                color:#94a3b8; padding:0 2px; }
#sidebar-content { overflow-y:auto; flex:1; padding:8px 0; }
.type-group { margin-bottom:4px; }
.type-label { font-size:10px; font-weight:700; color:#94a3b8; text-transform:uppercase;
              letter-spacing:.08em; padding:4px 12px 2px; }
.sidebar-item { padding:5px 12px; cursor:pointer; font-size:12px; color:#374151;
                display:flex; align-items:center; gap:6px; }
.sidebar-item:hover { background:#f1f5f9; }
.sidebar-item.active { background:#eff6ff; color:#1d4ed8; font-weight:600; }
.sid-badge { font-size:10px; color:#94a3b8; font-family:monospace; }

/* ── Main content ── */
#main { flex:1; display:flex; flex-direction:column; overflow:hidden; }
#surface-wrap { flex:1; overflow-y:auto; padding:24px; }

/* ── Surface card ── */
.surface-card { background:#fff; border-radius:10px; box-shadow:0 1px 4px rgba(0,0,0,.1);
                max-width:900px; margin:0 auto; overflow:hidden; }
.surface-header { padding:14px 20px; border-bottom:1px solid #f1f5f9; display:flex;
                  align-items:center; gap:10px; flex-wrap:wrap; }
.surface-id { font-family:ui-monospace,monospace; font-size:13px; font-weight:700; color:#374151; }
.surface-name { font-size:16px; font-weight:600; color:#111827; }
.type-badge { font-size:10px; font-weight:700; padding:2px 8px; border-radius:9999px;
              text-transform:uppercase; letter-spacing:.06em; }
.badge-screen   { background:#dbeafe; color:#1d4ed8; }
.badge-modal    { background:#e5e7eb; color:#374151; }
.badge-panel    { background:#d1fae5; color:#065f46; }
.badge-overlay  { background:#fef3c7; color:#92400e; }
.badge-component{ background:#ede9fe; color:#5b21b6; }
.badge-flow     { background:#fce7f3; color:#9d174d; }
.badge-default  { background:#f3f4f6; color:#374151; }
.region-chips { display:flex; gap:4px; margin-left:auto; flex-wrap:wrap; }
.region-chip { font-size:10px; font-family:ui-monospace,monospace; background:#f1f5f9;
               color:#64748b; border-radius:3px; padding:1px 6px; }
.surface-body { padding:18px 20px; }
.surface-errors { margin:0 0 12px; padding:8px 12px; background:#fef2f2;
                  border:1px solid #fecaca; border-radius:4px; font-size:12px; color:#b91c1c; }

/* ── Surface sub-tabs (Interactions | Blueprint) — two views of the same surface ── */
#surface-subtabs { display:flex; gap:2px; padding:6px 20px 0; border-bottom:1px solid #f1f5f9; }
.subtab { background:none; border:none; border-bottom:2px solid transparent; color:#64748b;
          padding:6px 12px; cursor:pointer; font-size:12px; font-weight:600; margin-bottom:-1px; }
.subtab:hover { color:#1e293b; }
.subtab.active { color:#2563eb; border-bottom-color:#2563eb; }

/* ── Region box (ported from mockup) ── */
.region-box { border:1px solid #e2e8f0; border-radius:8px; margin-bottom:14px; background:#fff; }
.region-box:last-child { margin-bottom:0; }
.region-label { font-size:11px; font-weight:700; color:#475569; text-transform:uppercase;
                letter-spacing:.07em; background:#f8fafc; padding:7px 12px;
                border-bottom:1px solid #eef2f6; border-radius:8px 8px 0 0;
                display:flex; align-items:center; justify-content:space-between; }
.region-count { font-size:10px; font-weight:600; color:#94a3b8; background:#fff;
                border:1px solid #e2e8f0; border-radius:9999px; padding:0 7px; }
.region-body { padding:12px; display:flex; flex-wrap:wrap; gap:8px; align-items:flex-start; }
.region-box.empty { border-style:dashed; opacity:.7; }
.region-box.empty .region-label { background:#fcfdfe; }
.region-empty-note { padding:11px 12px; font-size:12px; font-style:italic; color:#9ca3af; }

/* ── Action buttons ── */
.action-btn { border:none; border-radius:7px; padding:7px 12px; cursor:pointer;
              text-align:left; display:flex; flex-direction:column; gap:2px;
              min-width:120px; position:relative; transition:filter .1s,transform .1s; }
.action-btn:hover { filter:brightness(1.05); transform:translateY(-1px); }
.action-btn .el { font-size:12.5px; font-weight:600; font-family:ui-monospace,monospace; }
.action-btn .meta { font-size:10px; opacity:.8; }
.btn-navigate      { background:#dbeafe; color:#1d4ed8; }
.btn-open_overlay  { background:#ede9fe; color:#5b21b6; }
.btn-mutate        { background:#ffedd5; color:#9a3412; }
.btn-emit_event    { background:#dcfce7; color:#166534; }
.btn-close_overlay { background:#fee2e2; color:#991b1b; }
.btn-default       { background:#f3f4f6; color:#374151; }
.guard-pill { position:absolute; top:-6px; right:-6px; font-size:9px; font-weight:700;
              background:#fde68a; color:#92400e; border:1px solid #fff;
              border-radius:9999px; padding:1px 6px; }

/* ── Reaction / listener chips ── */
.listener-chip { border:1px dashed #94a3b8; cursor:pointer;
                 background:repeating-linear-gradient(45deg,#fafbfc,#fafbfc 6px,#f3f4f6 6px,#f3f4f6 12px);
                 color:#475569; border-radius:7px; padding:6px 11px;
                 display:flex; flex-direction:column; gap:2px; min-width:120px; }
.listener-chip .top { display:flex; align-items:center; gap:5px; }
.listener-chip .bolt { font-size:11px; }
.listener-chip .el { font-size:12px; font-weight:600; font-family:ui-monospace,monospace; color:#374151; }
.listener-chip .on { font-size:10px; color:#7c3aed; font-family:ui-monospace,monospace; }
.listener-chip .meta { font-size:10px; color:#64748b; }

/* ── Blueprint (ASCII) view ── */
#view-blueprint { display:none; }
.blueprint-note { font-size:11px; color:#9ca3af; margin-bottom:8px; }
#view-blueprint pre { font-family:"Cascadia Mono",Consolas,"DejaVu Sans Mono","Courier New",monospace; font-size:12px; line-height:1.55;
                      white-space:pre; background:#f8fafc; border:1px solid #e5e7eb;
                      border-radius:6px; padding:14px; overflow-x:auto; color:#1f2937; }

/* ── Bottom bar ── */
#bottombar { background:#f8fafc; border-top:1px solid #e2e8f0; padding:6px 16px;
             display:flex; align-items:center; gap:12px; flex-shrink:0;
             font-size:11px; color:#64748b; flex-wrap:wrap; }
.rules-wrap { display:flex; gap:4px; align-items:center; }
.rule-chip { background:#e0f2fe; color:#075985; border-radius:3px; padding:1px 6px;
             font-family:monospace; font-size:10px; }
.platform-chip { background:#f3f4f6; color:#374151; border-radius:3px; padding:1px 6px; font-size:10px; }

/* ── Overlay backdrop + card ── */
#overlay-backdrop { position:fixed; inset:0; background:rgba(0,0,0,.45);
                    backdrop-filter:blur(2px); display:flex; align-items:center;
                    justify-content:center; z-index:200; animation:fadeIn .15s ease; }
#overlay-backdrop.hidden { display:none; }
@keyframes fadeIn { from{opacity:0} to{opacity:1} }
#overlay-card { background:#fff; border-radius:10px; box-shadow:0 20px 60px rgba(0,0,0,.3);
                width:90%; max-width:700px; max-height:85vh; overflow-y:auto;
                animation:slideUp .15s ease; }
@keyframes slideUp { from{transform:translateY(12px);opacity:.6} to{transform:translateY(0);opacity:1} }

/* ── Toast ── */
#toast { position:fixed; bottom:60px; left:50%; transform:translateX(-50%);
         background:#1e293b; color:#e2e8f0; padding:8px 20px; border-radius:6px;
         font-size:12px; z-index:300; opacity:0; transition:opacity .2s;
         pointer-events:none; white-space:nowrap; }
#toast.show { opacity:1; }

/* ── Legend ── */
.legend { margin-top:20px; background:#fff; border:1px solid #e2e8f0; border-radius:8px;
          padding:12px 16px; font-size:11px; color:#64748b; max-width:900px; margin-left:auto; margin-right:auto; }
.legend h4 { font-size:11px; text-transform:uppercase; letter-spacing:.06em;
             color:#475569; margin-bottom:8px; }
.legend-row { display:flex; flex-wrap:wrap; gap:14px; align-items:center; }
.legend-item { display:flex; align-items:center; gap:6px; }
.swatch { width:14px; height:14px; border-radius:4px; display:inline-block; }
`;

export const CSS = CSS1 + CSS2 + CSS3;

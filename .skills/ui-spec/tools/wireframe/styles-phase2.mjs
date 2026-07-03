// wireframe/styles-phase2.mjs
// NODE: Phase 2 CSS additions — flow bar, narration banner, highlight, mini region-box, storyboard filmstrip.
// Concatenated by styles.mjs into the final CSS export.

export const CSS2 = `
/* ── Phase 2: Flow bar (select + play/stop) ── */
#flow-bar { display:flex; align-items:center; gap:4px; }
#flow-select { background:#334155; border:1px solid #475569; color:#cbd5e1; padding:3px 6px;
               border-radius:4px; font-size:11px; max-width:180px; cursor:pointer; }
#flow-select:focus { outline:2px solid #2563eb; }

/* ── Phase 2: Narration banner (fixed below topbar during play) ── */
#narration-banner { position:sticky; top:0; z-index:90; background:#1d4ed8; color:#fff;
                    display:flex; align-items:center; gap:10px; padding:6px 16px;
                    font-size:12px; flex-shrink:0; animation:slideDown .2s ease; }
#narration-banner.hidden { display:none; }
@keyframes slideDown { from{transform:translateY(-100%);opacity:0} to{transform:translateY(0);opacity:1} }
.nb-step { font-weight:700; font-size:11px; background:rgba(255,255,255,.2);
           border-radius:9999px; padding:1px 8px; white-space:nowrap; }
.nb-text { flex:1; font-family:ui-monospace,monospace; font-size:11px; opacity:.95; }
.nb-close { background:rgba(255,255,255,.15); border:none; color:#fff; border-radius:4px;
            padding:2px 8px; cursor:pointer; font-size:12px; margin-left:auto; }
.nb-close:hover { background:rgba(255,255,255,.3); }

/* ── Phase 2: Active region highlight + active element pulse ── */
.region-box.active-region { outline:2px solid #2563eb; outline-offset:1px; }
@keyframes pulse { 0%,100%{box-shadow:0 0 0 0 rgba(37,99,235,.5)} 50%{box-shadow:0 0 0 5px rgba(37,99,235,0)} }
.action-btn.active-el { animation:pulse 1s ease infinite; outline:2px solid #2563eb; }

/* ── Phase 2: Mini region-box (storyboard cards — readable, no shrink) ── */
.mini { pointer-events:none; }
.mini .region-box { margin-bottom:8px; }
.mini .region-label { padding:5px 10px; font-size:10px; }
.mini .region-body { padding:8px 10px; gap:6px; }
.mini .action-btn { padding:5px 10px; min-width:90px; border-radius:6px; }
.mini .action-btn .el { font-size:11px; }
.mini .action-btn .meta { font-size:9px; }
.mini .listener-chip { padding:5px 10px; min-width:90px; border-radius:6px; }
.mini .listener-chip .el { font-size:11px; }
.mini .listener-chip .on,.mini .listener-chip .meta { font-size:9px; }
.mini .guard-pill { font-size:8px; }
.mini-unknown { color:#9ca3af; font-style:italic; padding:8px; font-size:12px; }

/* ── Phase 2: Storyboard — vertical scroll list of large cards ── */
#view-storyboard { padding:16px; }
.sb-header { display:flex; align-items:baseline; gap:10px; margin-bottom:16px;
             padding-bottom:10px; border-bottom:1px solid #e2e8f0; flex-wrap:wrap; }
.sb-flow-name { font-weight:700; font-size:14px; color:#1e293b;
                font-family:ui-monospace,monospace; }
.sb-goal { font-size:12px; color:#475569; font-style:italic; }
.sb-hint { color:#9ca3af; font-style:italic; padding:24px 0; font-size:12px; text-align:center; }
.sb-filmstrip { display:flex; flex-direction:column; align-items:center; gap:0; }
.sb-step-wrap { display:flex; flex-direction:column; align-items:center; width:100%; }
.sb-card { background:#fff; border:1px solid #e2e8f0; border-radius:10px; padding:14px;
           width:100%; max-width:680px; cursor:pointer; transition:box-shadow .15s,border-color .15s;
           display:flex; flex-direction:column; gap:8px; }
.sb-card:hover { border-color:#2563eb; box-shadow:0 2px 12px rgba(37,99,235,.15); }
.sb-step-num { font-size:10px; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:.07em; }
.sb-mini { border:1px solid #f1f5f9; border-radius:6px; background:#f8fafc; padding:8px; }
.sb-cap { font-size:12px; color:#374151; line-height:1.5; font-family:ui-monospace,monospace;
          word-break:break-word; }
.sb-arrow { font-size:22px; color:#cbd5e1; padding:6px 0; align-self:center; }

/* ── Phase 2: Branch annotations ── */
.sb-branches { margin-top:14px; background:#fffbeb; border:1px solid #fde68a;
               border-radius:6px; padding:10px 14px; }
.sb-branches-label { font-size:10px; font-weight:700; color:#92400e; text-transform:uppercase;
                     letter-spacing:.07em; margin-bottom:6px; }
.sb-branch-item { display:flex; align-items:center; gap:6px; margin-bottom:4px; font-size:11px; }
.sb-branch-item:last-child { margin-bottom:0; }
.sb-branch-fork { font-size:13px; color:#b45309; flex-shrink:0; }
.sb-branch-when { color:#92400e; font-weight:600; }
.sb-branch-arrow { color:#b45309; }
.sb-branch-action { color:#374151; }
.sb-branch-id { font-family:ui-monospace,monospace; font-size:10px; color:#9ca3af; }

/* ── Phase 2 (search + hash): Sidebar search input ── */
.sidebar-search { padding:8px 10px 4px; }
.sidebar-search input[type=search] {
  width:100%; box-sizing:border-box; padding:5px 8px;
  background:#1e293b; border:1px solid #334155; border-radius:6px;
  color:#e2e8f0; font-size:12px; outline:none;
}
.sidebar-search input[type=search]:focus { border-color:#60a5fa; }
.sidebar-search input[type=search]::placeholder { color:#64748b; }

/* ── Phase 2 (search + hash): Action highlight flash ── */
@keyframes action-flash {
  0%,100% { outline:none; }
  15%,85% { outline:2px solid #f59e0b; outline-offset:2px; }
  50%      { background:#fde68a !important; }
}
.action-highlight { animation: action-flash 1.8s ease; }

/* ── Blueprint ↔ region-box 2-way linking ── */
/* Region name spans injected into <pre> by blueprint-link.js */
.bp-region-span { cursor:pointer; border-bottom:1px dotted #60a5fa; border-radius:2px; }
.bp-region-span:hover { background:#1e3a5f; color:#93c5fd; border-bottom-color:transparent; }
.bp-span-active { background:#f59e0b !important; color:#000 !important; border-bottom:none !important; border-radius:2px; }
/* Region-label click hint (cursor + underline when hovering) */
.region-label-link { cursor:pointer; }
.region-label-link:hover .region-count { /* keep, no extra change */ }
.region-label-link:hover { text-decoration:underline; color:#1d4ed8; }
/* Flash animation for region-box when navigated from Blueprint */
@keyframes region-flash { 0%,100%{background:inherit} 30%{background:#fde68a} }
.region-box-flash { animation:region-flash 1.6s ease; }
`;

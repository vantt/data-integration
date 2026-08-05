// wireframe/styles-content.mjs
// NODE: CSS for the typed content renderer (render-content.js) — lo-fi wireframe
// idioms: buttons, inputs, selects, checklists, chips, tabs, table/list skeletons,
// kpi, slot placeholders. Concatenated by styles.mjs into the final CSS export.

export const CSSC = `
/* ── Content model: cell container ─────────────────────────────────────────── */
.gc-content { display:flex; flex-direction:column; gap:6px; font-size:13px; min-width:0; }

/* Horizontal group */
.wf-row { display:flex; align-items:center; gap:6px; flex-wrap:wrap; min-width:0; }

/* ── Text primitives ───────────────────────────────────────────────────────── */
.wf-h    { font-size:15px; font-weight:700; color:#0f172a; }
.wf-text { color:#334155; line-height:1.45; }

/* ── Button — visibly a button (border + fill), primary = dark fill ────────── */
.wf-btn {
  display:inline-block; padding:3px 10px; border:1px solid #64748b; border-radius:6px;
  background:#fff; color:#1e293b; font-size:12px; font-weight:600; line-height:1.4;
  cursor:pointer; white-space:nowrap;
}
.wf-btn-primary { background:#1e293b; border-color:#1e293b; color:#fff; }
.wf-actionable:hover { outline:2px solid #93c5fd; outline-offset:1px; }

/* ── Input / select — empty outlined boxes with muted placeholder ──────────── */
.wf-input, .wf-select {
  display:inline-flex; align-items:center; gap:6px; min-width:90px;
  padding:3px 8px; border:1px solid #cbd5e1; border-radius:5px;
  background:#f8fafc; color:#94a3b8; font-size:12px; font-style:italic;
}
.wf-select-caret { color:#64748b; font-style:normal; }

/* ── Checklist ─────────────────────────────────────────────────────────────── */
.wf-checklist { display:flex; flex-direction:column; gap:3px; }
.wf-check { display:flex; align-items:center; gap:6px; color:#334155; }
.wf-checkbox {
  display:inline-flex; align-items:center; justify-content:center;
  width:14px; height:14px; border:1.5px solid #64748b; border-radius:3px;
  font-size:10px; color:#fff; background:#fff; flex-shrink:0;
}
.wf-checkbox.wf-checked { background:#1e293b; border-color:#1e293b; }

/* ── Chips / badge — display-only, visually distinct from buttons ──────────── */
.wf-chips { display:inline-flex; gap:4px; flex-wrap:wrap; }
.wf-chip {
  padding:1px 8px; border-radius:999px; background:#e2e8f0; color:#475569;
  font-size:11px; white-space:nowrap;
}
.wf-badge {
  padding:1px 7px; border-radius:4px; background:#fef3c7; color:#92400e;
  font-size:11px; font-weight:700; letter-spacing:.03em; white-space:nowrap;
}

/* ── Tabs ──────────────────────────────────────────────────────────────────── */
.wf-tabs { display:flex; gap:2px; border-bottom:2px solid #e2e8f0; }
.wf-tab {
  padding:4px 10px; font-size:12px; color:#64748b; border-bottom:2px solid transparent;
  margin-bottom:-2px; white-space:nowrap;
}
.wf-tab-active { color:#0f172a; font-weight:700; border-bottom-color:#1e293b; }

/* ── Table skeleton ────────────────────────────────────────────────────────── */
.wf-table { width:100%; border-collapse:collapse; font-size:12px; }
.wf-table th {
  text-align:left; padding:4px 8px; color:#475569; font-weight:700;
  border-bottom:2px solid #cbd5e1; background:#f8fafc; white-space:nowrap;
}
.wf-table td { padding:5px 8px; border-bottom:1px solid #e2e8f0; }

/* Skeleton bar — greyed content placeholder in table/list rows */
.wf-skel {
  display:inline-block; height:9px; border-radius:4px; background:#e2e8f0;
}

/* ── List skeleton — first row shows the item template, rest are ghosts ────── */
.wf-list { display:flex; flex-direction:column; }
.wf-list-item { padding:5px 2px; border-bottom:1px solid #eef2f7; }
.wf-list-text { color:#334155; font-size:12px; }
.wf-list-ghost { color:#b6c2d1; }

/* ── KPI — big number with small label ─────────────────────────────────────── */
.wf-kpi { display:inline-flex; flex-direction:column; gap:1px; }
/* KPIs sitting side-by-side in a row need clear separation ("8.2tr  3", not "8.2tr 3") */
.wf-row > .wf-kpi:not(:last-child) { margin-right: 14px; }
.wf-kpi-label { font-size:10px; text-transform:uppercase; letter-spacing:.06em; color:#94a3b8; }
.wf-kpi-value { font-size:18px; font-weight:800; color:#0f172a; line-height:1.15; }

/* ── Divider ───────────────────────────────────────────────────────────────── */
.wf-divider { border:none; border-top:1px solid #e2e8f0; margin:2px 0; }

/* ── Slot — hatched placeholder for hosted panels / dynamic content ────────── */
.wf-slot {
  flex:1; min-height:64px; display:flex; align-items:center; justify-content:center;
  border:1.5px dashed #94a3b8; border-radius:6px; color:#64748b; font-size:12px;
  background:repeating-linear-gradient(45deg,#f8fafc,#f8fafc 8px,#eef2f7 8px,#eef2f7 16px);
}

/* Unknown primitive — validator warns; make it visible, not invisible */
.wf-unknown { color:#b91c1c; font-size:11px; border:1px dashed #b91c1c; padding:0 6px; border-radius:4px; }
`;

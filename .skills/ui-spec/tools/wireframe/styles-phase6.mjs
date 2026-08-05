// wireframe/styles-phase6.mjs
// NODE: Phase 6 CSS additions — CSS grid renderer (grid cells, sample content,
// floating banners, variant switcher, inline chips, inspector panel).
// Concatenated by styles.mjs into final CSS export.

export const CSS6 = `
/* ── Phase 6: Grid view container ──────────────────────────────────────────── */
#view-grid { padding: 16px 0; }

/* Surfaces with a ui-layout grid need real width for the honest viewport frame
   (1280px desktop) + 300px inspector — relax the default 900px card cap. */
.surface-card:has(.grid-with-inspector) { max-width: 1560px; }

/* ── Grid + inspector flex wrapper ─────────────────────────────────────────── */
/* grid-with-inspector: flex row — grid-main grows, inspector fixed 300px. */
.grid-with-inspector {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.grid-main {
  flex: 1;
  min-width: 0;
}

/* Grid wrapper — driven by inline style (grid-template-columns + grid-template-areas).
   No max-width / centering — the flex parent (.grid-main) handles sizing. */
.grid-container {
  padding: 16px;
  background: #f1f5f9;
  border-radius: 8px;
}

/* ── Viewport frame — honest device width around the grid ──────────────────── */
/* max-width comes inline from viewportSpec (1280 desktop / 390 mobile / 560 modal). */
.viewport-frame {
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  padding: 6px;
}

.vp-label {
  font-size: 10px;
  color: #94a3b8;
  text-align: right;
  padding: 0 4px 4px;
  letter-spacing: .04em;
}

/* ── Grid cell card ─────────────────────────────────────────────────────────── */
/* Each distinct region = one grid cell card.
   Padding + min-height give cells breathing room even when empty.
   Flex column so gc-sample stretches naturally. */
.grid-cell {
  min-width: 0;
  background: #fff;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  padding: 10px 12px;
  min-height: 56px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* ── Grid cell inner elements ─────────────────────────────────────────────── */

/* Region label: very small, muted, uppercase — subordinate to sample text */
.gc-label {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: .09em;
  color: #94a3b8;
  line-height: 1.2;
  margin-bottom: 2px;
}

/* Sample text: THE dominant element stakeholders read */
.gc-sample {
  font-size: 13px;
  color: #111827;
  line-height: 1.55;
  word-break: break-word;
  flex: 1;
}

/* ── Inline chips (sample text [bracket] tokens) ────────────────────────────── */
/* Subtle button-look: 1px border, radius 4, cursor pointer.
   Renders directly inside gc-sample text flow (inline-block). */
.gc-inline-chip {
  display: inline-block;
  max-width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0 4px;
  cursor: pointer;
  font-size: inherit;
  color: inherit;
  background: transparent;
  vertical-align: baseline;
  transition: background .1s, border-color .1s;
  white-space: normal;
  overflow-wrap: break-word;
  user-select: none;
}
.gc-inline-chip:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
}

/* Mapped chip: has a known action-id → highlight in blue to signal interactivity */
.gc-inline-chip.gc-inline-chip-mapped {
  border-color: #93c5fd;
  color: #1d4ed8;
}
.gc-inline-chip.gc-inline-chip-mapped:hover {
  background: #dbeafe;
  border-color: #60a5fa;
}

/* ── Child sub-layout mini-sections (layout.children, 1 level) ─────────────── */
/* Vertical stack of child blocks inside the parent cell (e.g. S03 sidebar).
   Each child repeats the gc-label/gc-sample grammar; thin top divider
   separates blocks so the rail reads as stacked cards. */
.gc-children {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 6px;
}
.gc-child {
  border-top: 1px solid #eef2f6;
  padding-top: 8px;
}
.gc-child .gc-sample { flex: unset; }

/* ── Floating region toggle button ──────────────────────────────────────────── */
.floating-toggle {
  font-size: 11px;
  padding: 4px 12px;
  background: #1e293b;
  border: 1px solid #f59e0b;
  color: #f59e0b;
  border-radius: 4px;
  cursor: pointer;
  margin: 8px 4px 0 0;
}
.floating-toggle:hover { background: #334155; }
.floating-toggle-active {
  background: #dc2626 !important;
  border-color: #dc2626 !important;
  color: #fff !important;
}

/* ── Floating region banner (shown when toggle ON) ───────────────────────── */
.floating-banner {
  border: 2px dashed #ef4444;
  border-radius: 6px;
  padding: 10px;
  margin-top: 10px;
  background: #fff1f2;
}

/* Floating cell: same card shape as .grid-cell but red-tinted */
.gc-floating {
  background: #fff1f2;
  border-color: #fecaca;
}
.gc-floating .gc-label { color: #ef4444; }

/* ── Variant switcher ────────────────────────────────────────────────────── */
.variant-switcher {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #94a3b8;
  flex-wrap: wrap;
}
.variant-btn {
  font-size: 11px;
  padding: 3px 10px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 4px;
  cursor: pointer;
  color: #94a3b8;
}
.variant-btn:hover { background: #334155; }
.variant-btn.active { border-color: #60a5fa; color: #60a5fa; }

/* ── Inspector panel ─────────────────────────────────────────────────────── */
/* Fixed 300px right column, sticky below topbar. */
/* Right rail: inspector + legend stacked; the rail (not the inspector) is sticky. */
.grid-rail {
  width: 300px;
  flex-shrink: 0;
  position: sticky;
  top: 72px;
  align-self: flex-start;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.grid-inspector {
  width: 100%;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
  font-size: 12px;
}

/* Legend inside the rail: compact card, items wrap in the narrow column. */
.legend-rail {
  max-width: none;
  margin: 0;
}
.legend-rail .legend-row { gap: 8px 12px; }

.gi-header {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: #94a3b8;
  padding: 7px 10px 5px;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
}

.gi-content {
  padding: 10px;
  min-height: 80px;
}

.gi-footer {
  font-size: 10px;
  color: #94a3b8;
  padding: 4px 10px 6px;
  border-top: 1px solid #f1f5f9;
  font-style: italic;
  background: #f8fafc;
}

/* Inspector default state */
.gi-hint {
  color: #94a3b8;
  font-style: italic;
  font-size: 11px;
}
.gi-surface-meta {
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
}

/* Inspector region view */
.gi-region-name {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: #475569;
  margin-bottom: 7px;
  padding-bottom: 4px;
  border-bottom: 1px solid #f1f5f9;
}
.gi-row {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 5px;
  margin-bottom: 5px;
  align-items: baseline;
}
.gi-row-reaction { opacity: 0.65; }
.gi-el {
  font-family: ui-monospace, monospace;
  font-size: 10px;
  color: #374151;
  font-weight: 600;
}
.gi-sep {
  color: #94a3b8;
  font-size: 10px;
}
.gi-act {
  color: #2563eb;
  font-size: 10px;
}
.gi-guard {
  color: #d97706;
  font-size: 10px;
  font-style: italic;
}
.gi-empty {
  color: #94a3b8;
  font-size: 11px;
  font-style: italic;
}

/* Inspector chip view */
.gi-chip-title {
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 8px;
  color: #1d4ed8;
}
.gi-unmapped {
  color: #94a3b8;
  font-size: 11px;
  font-style: italic;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f1f5f9;
}
.gi-contract {
  margin-top: 2px;
}
.gi-kv {
  display: flex;
  gap: 6px;
  margin-bottom: 4px;
  align-items: flex-start;
}
.gi-k {
  font-family: ui-monospace, monospace;
  font-size: 10px;
  color: #94a3b8;
  min-width: 58px;
  flex-shrink: 0;
  padding-top: 1px;
}
.gi-v {
  color: #111827;
  font-size: 11px;
  word-break: break-word;
}
.gi-kv .gi-guard {
  font-size: 11px;
  font-style: italic;
  color: #d97706;
}

/* Clickable target button inside inspector */
.gi-target-btn {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  font-size: 11px;
  padding: 0;
  text-decoration: underline;
  font-family: inherit;
  line-height: inherit;
}
.gi-target-btn:hover { color: #1d4ed8; }
`;

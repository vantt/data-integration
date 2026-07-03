// wireframe/styles-phase4.mjs
// NODE: Phase 4 CSS additions — States subtab: state cards, ST id badges, ERR chips.
// Concatenated by styles.mjs into the final CSS export.

export const CSS4 = `
/* ── Phase 4: States subtab view ───────────────────────────────────────────── */
#view-states { padding: 16px 0; }

/* State card — neutral light card matching .region-box visual language */
.state-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 10px;
  background: #f8fafc;
}
.state-card:last-child { margin-bottom: 0; }

.state-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

/* ST-* id badge — soft blue pill */
.state-id {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  background: #dbeafe;
  color: #1d4ed8;
  padding: 2px 7px;
  border-radius: 9999px;
  white-space: nowrap;
  font-weight: 700;
  letter-spacing: .02em;
}

.state-label {
  font-weight: 600;
  font-size: 13px;
  color: #111827;
  line-height: 1.4;
}

.state-desc {
  font-size: 12px;
  color: #64748b;
  margin: 4px 0 8px;
  line-height: 1.5;
}

.state-err-refs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}

/* ERR-* chips: known = blue, unknown = orange */
.err-chip {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 9999px;
  cursor: default;
  font-family: ui-monospace, monospace;
  font-weight: 600;
  letter-spacing: .01em;
}
.err-chip.known   { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
.err-chip.unknown { background: #ffedd5; color: #9a3412; border: 1px solid #fed7aa; }

/* Empty-state message when no ST-* entries declared */
.states-empty {
  color: #94a3b8;
  font-size: 13px;
  padding: 32px 24px;
  text-align: center;
  font-style: italic;
}
`;

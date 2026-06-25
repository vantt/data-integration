/* ============================================================
   Shared helpers + atoms for the CRM prototype.
   Exposes components/utilities on window.
   ============================================================ */
const { useState, useEffect, useRef, useCallback } = React;

/* ── Formatters ─────────────────────────────────────────── */
function fmtVND(n) {
  if (n == null) return "—";
  return new Intl.NumberFormat("vi-VN").format(Math.round(n)) + "đ";
}
function fmtVNDShort(n) {
  if (n == null) return "—";
  if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + "tỷ";
  if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "tr";
  if (n >= 1e3) return Math.round(n / 1e3) + "k";
  return String(n);
}
// store UTC ISO → display ICT (UTC+7)
function ictParts(iso) {
  const d = new Date(iso);
  const ms = d.getTime() + 7 * 3600 * 1000;
  const t = new Date(ms);
  const pad = (x) => String(x).padStart(2, "0");
  return {
    dd: pad(t.getUTCDate()), mm: pad(t.getUTCMonth() + 1), yyyy: t.getUTCFullYear(),
    HH: pad(t.getUTCHours()), MM: pad(t.getUTCMinutes()),
  };
}
function fmtDate(iso) { if (!iso) return "—"; const p = ictParts(iso); return `${p.dd}/${p.mm}/${p.yyyy}`; }
function fmtDateOnly(d) { if (!d) return "—"; const [y, m, day] = d.split("-"); return `${day}/${m}/${y}`; }
function fmtTime(iso) { if (!iso) return "—"; const p = ictParts(iso); return `${p.HH}:${p.MM}`; }
function fmtDateTime(iso) { if (!iso) return "—"; const p = ictParts(iso); return `${p.dd}/${p.mm}/${p.yyyy} ${p.HH}:${p.MM}`; }
const NOW = new Date("2026-06-14T03:30:00Z").getTime();
function relTime(iso) {
  if (!iso) return "—";
  const diff = NOW - new Date(iso).getTime();
  const m = Math.round(diff / 60000);
  if (m < 1) return "vừa xong";
  if (m < 60) return `${m} phút trước`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} giờ trước`;
  const d = Math.round(h / 24);
  if (d < 30) return `${d} ngày trước`;
  return fmtDate(iso);
}
function hoursSince(iso) { return (NOW - new Date(iso).getTime()) / 3600000; }

/* ── Icons (hand-drawn, 1.3 stroke, round caps — Precision) ── */
function Icon({ name, size = 16 }) {
  const p = { fill: "none", stroke: "currentColor", strokeWidth: 1.3, strokeLinecap: "round", strokeLinejoin: "round" };
  const svg = (children) => <svg width={size} height={size} viewBox="0 0 16 16" {...p}>{children}</svg>;
  switch (name) {
    case "worklist": return svg(<><path d="M3 2.5h7l3 3v8H3z" /><path d="M9.5 2.5v3.5H13" /><path d="M5.5 9h5M5.5 11.3h3" /></>);
    case "customers": return svg(<><circle cx="6" cy="6" r="2.4" /><path d="M2.3 13c.4-2.2 2-3.4 3.7-3.4S9.3 10.8 9.7 13" /><path d="M10.4 4.2a2.2 2.2 0 0 1 0 4.2M11.4 9.7c1.4.3 2.4 1.4 2.7 3.1" /></>);
    case "inbox": return svg(<><path d="M2 4.5 8 8.5l6-4" /><rect x="2" y="3" width="12" height="10" rx="1.5" /></>);
    case "tasks": return svg(<><rect x="2.5" y="2.5" width="11" height="11" rx="1.5" /><path d="M5.2 8l1.8 1.8L11 6" /></>);
    case "segments": return svg(<><circle cx="8" cy="8" r="5.5" /><path d="M8 8 8 2.5M8 8l4.8 2.7" /></>);
    case "campaigns": return svg(<><path d="M2.5 6.5 12 3v8L2.5 9.5z" /><path d="M2.5 6.5v3M5 9.8v2.7h2V10.4" /></>);
    case "ads": return svg(<><path d="M2.5 11V8M6 11V5M9.5 11V6.5M13 11V3.5" /></>);
    case "dedup": return svg(<><circle cx="6" cy="8" r="3.2" /><circle cx="10" cy="8" r="3.2" /></>);
    case "settings": return svg(<><circle cx="8" cy="8" r="2" /><circle cx="8" cy="8" r="5.4" /><path d="M8 1.4v1.2M8 13.4v1.2M14.6 8h-1.2M2.6 8H1.4" /></>);
    case "search": return svg(<><circle cx="7" cy="7" r="4.5" /><path d="M10.5 10.5 14 14" /></>);
    case "plus": return svg(<><path d="M8 3v10M3 8h10" /></>);
    case "back": return svg(<><path d="M9.5 3.5 5 8l4.5 4.5" /></>);
    case "chevron": return svg(<><path d="M6 4l4 4-4 4" /></>);
    case "chevdown": return svg(<><path d="M4 6l4 4 4-4" /></>);
    case "close": return svg(<><path d="M4 4l8 8M12 4l-8 8" /></>);
    case "check": return svg(<><path d="M3.5 8.5 6.5 11.5 12.5 5" /></>);
    case "phone": return svg(<><path d="M5.2 2.8 6.6 5 5.4 6.4a8 8 0 0 0 4.2 4.2L11 9.4l2.2 1.4c.4.3.5.8.2 1.2-1 1.4-2.8 1.8-5 .8A12 12 0 0 1 3.2 7C2.2 4.8 2.6 3 4 2c.4-.3.9-.2 1.2.2z" /></>);
    case "edit": return svg(<><path d="M10.5 2.8 13.2 5.5 5.5 13.2 2.8 13.8 3.4 11z" /></>);
    case "trash": return svg(<><path d="M3.5 4.5h9M6 4.5V3h4v1.5M5 4.5l.6 8.5h4.8L11 4.5" /></>);
    case "tag": return svg(<><path d="M2.5 2.5h5L13 8l-5 5-5.5-5.5z" /><circle cx="5.2" cy="5.2" r=".9" /></>);
    case "filter": return svg(<><path d="M2.5 3.5h11L9.3 8.3v4l-2.6 1.3v-5.3z" /></>);
    case "clock": return svg(<><circle cx="8" cy="8" r="5.5" /><path d="M8 5v3l2 1.4" /></>);
    case "money": return svg(<><circle cx="8" cy="8" r="5.5" /><path d="M8 5v6M6.4 6.4h2.4a1.1 1.1 0 0 1 0 2.2H6.6h2.2a1.1 1.1 0 0 1 0 2.2H6.4" /></>);
    case "user": return svg(<><circle cx="8" cy="5.5" r="2.6" /><path d="M3.2 13.2c.5-2.6 2.4-4 4.8-4s4.3 1.4 4.8 4" /></>);
    case "merge": return svg(<><path d="M5 2.5v3.2c0 1.2.8 2 2 2.3l2 .6c1.2.3 2 1.1 2 2.3v.6M5 2.5 3.5 4M5 2.5 6.5 4M11 11.5 9.5 13M11 11.5l1.5 1.5" /></>);
    case "link": return svg(<><path d="M6.5 9.5 9.5 6.5M5.5 7 4 8.5a2.1 2.1 0 0 0 3 3L8.5 10M10.5 9 12 7.5a2.1 2.1 0 0 0-3-3L7.5 6" /></>);
    case "doc": return svg(<><path d="M4 2.5h5L12 5.5v8H4z" /><path d="M8.5 2.5V6H12" /></>);
    case "warn": return svg(<><path d="M8 2.5 14 13H2z" /><path d="M8 6.5v3M8 11.2v.1" /></>);
    case "bolt": return svg(<><path d="M8.5 2 4 9h3.2l-.7 5L12 7H8.8z" /></>);
    case "dots": return svg(<><circle cx="4" cy="8" r=".9" /><circle cx="8" cy="8" r=".9" /><circle cx="12" cy="8" r=".9" /></>);
    case "logout": return svg(<><path d="M6 3.5H3.5v9H6M9 5.5 11.5 8 9 10.5M11.5 8H6" /></>);
    case "external": return svg(<><path d="M6 3.5H3.5v9h9V10M9.5 3.5H13v3.5M13 3.5 7.5 9" /></>);
    case "copy": return svg(<><rect x="5.5" y="5.5" width="7" height="7" rx="1" /><path d="M3.5 9.5h-1v-7h7v1" /></>);
    case "refresh": return svg(<><path d="M13 8a5 5 0 1 1-1.5-3.5M13 2.5V5h-2.5" /></>);
    case "palette": return svg(<><path d="M8 1.7C4.3 1.7 1.4 4.3 1.4 7.7c0 2.6 2 4.4 4.1 4.4.95 0 1.5-.6 1.5-1.35 0-.5-.3-.8-.3-1.25 0-.62.5-1.1 1.25-1.1h1.2c2.3 0 4.05-1.6 4.05-3.9 0-2.95-2.75-4.8-5.25-4.8z" /><circle cx="4.5" cy="7.2" r=".85" fill="currentColor" stroke="none" /><circle cx="6.3" cy="4.7" r=".85" fill="currentColor" stroke="none" /><circle cx="9.4" cy="4.6" r=".85" fill="currentColor" stroke="none" /><circle cx="11.2" cy="6.8" r=".85" fill="currentColor" stroke="none" /></>);
    default: return null;
  }
}

/* ── Action-type meta (C03) ─────────────────────────────── */
const ACTION_META = {
  CALL_NOW: { label: "CALL NOW", tone: "coral" },
  WIN_BACK: { label: "WIN BACK", tone: "amber" },
  REORDER_NUDGE: { label: "REORDER", tone: "moss" },
  UPSELL: { label: "UPSELL", tone: "amber" },
  CROSS_SELL: { label: "CROSS-SELL", tone: "honey" },
  LOYALTY_REWARD: { label: "LOYALTY", tone: "default" },
};
const GROUP_TONE = { GOLD: "amber", VIP: "amber", SILVER: "default", NEW: "moss" };
const STATUS_META = {
  active: { label: "active", cls: "good" }, at_risk: { label: "at_risk", cls: "warn" },
  churned: { label: "churned", cls: "bad" },
};
const SIGNAL_META = {
  IMMINENT: "moss", STEADY: "default", WANING: "warn", DORMANT: "bad", UNKNOWN: "muted",
};

/* ── Badge / chip atoms ─────────────────────────────────── */
function Bdg({ tone, children, dot }) {
  const cls = tone === "good" ? "bdg--good" : tone === "warn" ? "bdg--warn" : tone === "bad" ? "bdg--bad" : tone === "accent" ? "bdg--accent" : "";
  return <span className={"bdg " + cls}>{dot && <span className="bdg__dot" />}{children}</span>;
}
function Chip({ tone, children }) {
  const cls = tone === "moss" ? "chip--moss" : tone === "amber" ? "chip--amber" : tone === "coral" ? "chip--coral" : "";
  return <span className={"chip " + cls}>{children}</span>;
}
function GroupBadge({ group }) {
  const tone = GROUP_TONE[group] === "amber" ? "accent" : GROUP_TONE[group] === "moss" ? "good" : "";
  return <Bdg tone={tone}>{group}</Bdg>;
}
function StatusBadge({ status }) {
  const m = STATUS_META[status] || { label: status, cls: "" };
  return <Bdg tone={m.cls} dot>{m.label}</Bdg>;
}
function Avatar({ user, size = 26 }) {
  const u = typeof user === "string" ? window.DB.userById(user) : user;
  const init = u ? u.initials : "—";
  return (
    <span style={{
      width: size, height: size, flex: "none", borderRadius: "var(--radii-pill)",
      display: "grid", placeItems: "center", background: "var(--bg-raised)",
      border: "1px solid var(--border-strong)", color: "var(--fg-1)",
      fontFamily: "var(--font-mono)", fontSize: size * 0.4, letterSpacing: "0.02em",
    }}>{init}</span>
  );
}

/* ── C06 Freshness Badge ────────────────────────────────── */
function FreshnessBadge({ table, at, plain }) {
  const h = hoursSince(at);
  const state = h < 24 ? "fresh" : h < 48 ? "stale" : "very";
  const tone = state === "fresh" ? "good" : state === "stale" ? "warn" : "bad";
  const mark = state === "fresh" ? "✓" : state === "very" ? "✗" : "⚠";
  const txt = state === "fresh" ? `cập nhật ${fmtTime(at)} ICT`
    : state === "stale" ? `${fmtTime(at)} ICT (hôm qua)` : "quá 48h — liên hệ admin";
  if (plain) return (
    <span className="crm-nav__sync" title={`${table} · ${fmtDateTime(at)} ICT`} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span className={"verdict-dot verdict-dot--sm"} style={{ "--vtone": tone === "good" ? "var(--moss-500)" : tone === "warn" ? "var(--honey-500)" : "var(--coral-500)" }} />
      {table}: {txt}
    </span>
  );
  return <Bdg tone={tone} dot>{mark} {txt}</Bdg>;
}

/* ── C04 Tag Chips ──────────────────────────────────────── */
function TagChips({ tagIds, editable, onAdd, onRemove, maxVisible = 6 }) {
  const all = (tagIds || []).map((id) => window.DB.tagById(id)).filter(Boolean);
  const shown = all.slice(0, maxVisible);
  const extra = all.length - shown.length;
  const tone = (t) => t.tone === "amber" ? "amber" : t.tone === "moss" ? "moss" : t.tone === "coral" ? "coral" : "";
  return (
    <div className="chips" style={{ gap: "var(--sp-2)" }}>
      {shown.map((t) => (
        <span key={t.id} className={"chip " + (tone(t) ? "chip--" + tone(t) : "")} style={editable ? { paddingRight: 4 } : null}>
          {t.label}
          {editable && <button className="chip-x" onClick={() => onRemove && onRemove(t.id)} aria-label="remove"
            style={{ border: 0, background: "transparent", color: "inherit", cursor: "pointer", padding: "0 2px", opacity: .7, lineHeight: 1 }}>✕</button>}
        </span>
      ))}
      {extra > 0 && <span className="chip">+{extra}</span>}
      {editable && <button className="fchip" onClick={onAdd} style={{ padding: "3px 8px" }}><Icon name="plus" size={11} /></button>}
      {all.length === 0 && !editable && <span className="muted" style={{ fontSize: 12 }}>—</span>}
    </div>
  );
}

/* ── C03 Action Queue Card ──────────────────────────────── */
function ActionQueueCard({ action, party, compact, onTask, onCall, onOpen }) {
  const m = ACTION_META[action.type] || { label: action.type, tone: "default" };
  return (
    <div className={"aq-card" + (compact ? " aq-card--compact" : "")} onClick={() => onOpen && onOpen(party)}>
      <div className="aq-card__top">
        <Chip tone={m.tone}>{m.label}</Chip>
        {action.value > 0 && (
          <span className="aq-card__val">
            <span className="aq-card__val-label">GT dự kiến</span>
            <Icon name="money" size={13} />
            {fmtVND(action.value)}
          </span>
        )}
      </div>
      <div className="aq-card__rationale">{action.rationale}</div>
      {!compact && (
        <div className="aq-card__foot">
          <button className="btn btn--secondary aq-card__cta" onClick={(e) => { e.stopPropagation(); onCall && onCall(action, party); }}>
            <Icon name="phone" size={13} /> Gọi ngay
          </button>
          <button className="btn btn--ghost aq-card__cta" onClick={(e) => { e.stopPropagation(); onTask && onTask(action, party); }}>
            <Icon name="clock" size={13} /> Đặt lịch
          </button>
        </div>
      )}
    </div>
  );
}

/* ── C05 Filter Bar (faceted selects) ───────────────────── */
function FilterSelect({ label, value, options, onChange }) {
  return (
    <div className="fsel">
      <div className="fsel__label caption">{label}</div>
      <div className="fsel__field">
        <select value={value} onChange={(e) => onChange(e.target.value)}>
          {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <span className="fsel__chev"><Icon name="chevdown" size={12} /></span>
      </div>
    </div>
  );
}
function FilterBar({ filters, values, onChange, onClear, right }) {
  const activeCount = Object.keys(values || {}).filter((k) => values[k] && values[k] !== "all").length;
  return (
    <div className="toolbar">
      <div className="toolbar__filters">
        {filters.map((f) => (
          <FilterSelect key={f.field} label={f.label} value={values[f.field] || "all"}
            options={f.options} onChange={(v) => onChange(f.field, v)} />
        ))}
        {activeCount > 0 && <button className="toolbar__reset" onClick={onClear}>Xóa filter ({activeCount})</button>}
      </div>
      {right}
    </div>
  );
}

/* ── Modal shell ────────────────────────────────────────── */
function Modal({ title, sub, onClose, children, actions, width = 480 }) {
  useEffect(() => {
    const h = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="modal-scrim" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal" style={{ width }} role="dialog" aria-modal="true">
        <div className="modal__head">
          <div>
            <div className="modal__title">{title}</div>
            {sub && <div className="modal__sub">{sub}</div>}
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="Đóng"><Icon name="close" size={14} /></button>
        </div>
        <div className="modal__body">{children}</div>
        {actions && <div className="modal__actions">{actions}</div>}
      </div>
    </div>
  );
}
/* form field helpers */
function Field({ label, required, children, hint, error }) {
  return (
    <label className="field">
      {label && <span className="field__label">{label}{required && <span className="field__req"> *</span>}</span>}
      {children}
      {hint && !error && <span className="field__hint">{hint}</span>}
      {error && <span className="field__error">{error}</span>}
    </label>
  );
}
function TextInput(props) { return <input className="inp" {...props} />; }
function TextArea(props) { return <textarea className="inp inp--area" {...props} />; }
function Select({ value, onChange, children }) {
  return <div className="inp-sel"><select value={value} onChange={onChange}>{children}</select><span className="inp-sel__chev"><Icon name="chevdown" size={12} /></span></div>;
}

/* ── Empty / loading / page states ──────────────────────── */
function EmptyState({ title, sub, cta, icon }) {
  return (
    <div className="state">
      <div className="state__inner">
        {icon && <div className="state__icon"><Icon name={icon} size={28} /></div>}
        <div className="state__title">{title}</div>
        {sub && <div className="state__sub">{sub}</div>}
        {cta && <div className="state__actions">{cta}</div>}
      </div>
    </div>
  );
}
function PageHead({ eyebrow, title, sub, aside }) {
  return (
    <div className="crm-pagehead">
      <div>
        {eyebrow && <div className="caption crm-pagehead__eyebrow">{eyebrow}</div>}
        <h1 className="crm-pagehead__title">{title}</h1>
        {sub && <div className="crm-pagehead__sub">{sub}</div>}
      </div>
      {aside && <div className="crm-pagehead__aside">{aside}</div>}
    </div>
  );
}

/* Sparkline */
function Spark({ data, w = 76, h = 22 }) {
  const max = Math.max(...data), min = Math.min(...data);
  const rng = max - min || 1;
  const pts = data.map((v, i) => [(i / (data.length - 1)) * w, h - ((v - min) / rng) * (h - 3) - 1.5]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const area = d + ` L ${w} ${h} L 0 ${h} Z`;
  return <svg className="spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`}><path className="area" d={area} /><path d={d} /></svg>;
}

Object.assign(window, {
  fmtVND, fmtVNDShort, fmtDate, fmtDateOnly, fmtTime, fmtDateTime, relTime, hoursSince, ictParts, NOW,
  Icon, ACTION_META, GROUP_TONE, STATUS_META, SIGNAL_META,
  Bdg, Chip, GroupBadge, StatusBadge, Avatar, FreshnessBadge, TagChips, ActionQueueCard,
  FilterSelect, FilterBar, Modal, Field, TextInput, TextArea, Select, EmptyState, PageHead, Spark,
});

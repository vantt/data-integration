/* detailView — shared UI primitives (Precision-grounded) */

/* bilingual label helper — reads <html data-lang> ("en" | "vi") */
function tr(en, vi){
  const lang = document.documentElement.getAttribute("data-lang") || "en";
  return lang === "vi" ? vi : en;
}

/* VND money formatter */
function fmtVND(v){
  if (v === null || v === undefined) return null;
  return new Intl.NumberFormat("vi-VN").format(Math.round(v)) + " ₫";
}
function Money({ v, className }){
  const s = fmtVND(v);
  if (s === null) return <span className={"dash "+(className||"")}>—</span>;
  return <span className={className}>{s}</span>;
}

/* pct with tone */
function Pct({ v, invert }){
  if (v === null || v === undefined) return <span className="dash">—</span>;
  const good = invert ? v < 0 : v >= 25;
  return <span className={"pct "+(good ? "pct--good" : v < 15 ? "pct--bad" : "")}>{v.toFixed(1)}%</span>;
}

/* Badge — tones: neutral/good/warn/bad/accent */
function Badge({ tone="neutral", dot, children }){
  const cls = tone === "good" ? "bdg bdg--good" : tone === "warn" ? "bdg bdg--warn"
    : tone === "bad" ? "bdg bdg--bad" : tone === "accent" ? "bdg bdg--accent" : "bdg";
  return <span className={cls}>{dot && <i className="bdg__dot" />}{children}</span>;
}

/* map status strings → tone */
function statusTone(s){
  const good = ["COMPLETED","PAID","DELIVERED","ACTIVE","VERIFIED"];
  const warn = ["PROCESSING","SHIPPED","IN_TRANSIT","AT_RISK","PARTIAL","PENDING"];
  const bad  = ["RETURNED","CANCELLED","CHURNED","FAILED","UNPAID"];
  if (good.includes(s)) return "good";
  if (warn.includes(s)) return "warn";
  if (bad.includes(s)) return "bad";
  return "neutral";
}
function valueGroupTone(g){
  return ["VIP","PLATINUM"].includes(g) ? "accent" : g === "GOLD" ? "warn" : "neutral";
}

/* Caveat note */
function Caveat({ tone="info", rule, mark, children }){
  const cls = "caveat caveat--"+tone + (rule ? " caveat--rule" : "");
  const m = mark || (tone === "warn" ? "⚠" : "ⓘ");
  return <div className={cls}><span className="caveat__mark">{m}</span><div>{children}</div></div>;
}

/* KPI stat */
function Kpi({ label, value, sub, hero }){
  return (
    <div className={"kpi"+(hero?" kpi--hero":"")}>
      <div className="kpi__label">{label}</div>
      <div className="kpi__val">{value}</div>
      {sub && <div className="kpi__sub">{sub}</div>}
    </div>
  );
}

/* status pill (text + dot) */
function StatusPill({ status }){
  const tone = statusTone(status);
  const cls = tone === "good" ? "status--ready" : tone === "warn" ? "status--warn"
    : tone === "bad" ? "status--blocked" : "status--locked";
  return <span className={"status "+cls}><span className="mono" style={{fontSize:11, letterSpacing:"0.06em"}}>{status}</span></span>;
}

/* eyebrow caption */
function Eyebrow({ children, accent, className }){
  return <div className={"caption"+(accent?" caption--accent":"")+(className?" "+className:"")}>{children}</div>;
}

/* Sparkline — values array (relative), renders an area+line svg */
function Sparkline({ data=[], w=120, h=30 }){
  if (!data.length) return null;
  const max = Math.max(...data), min = Math.min(...data);
  const span = (max - min) || 1;
  const step = w / (data.length - 1 || 1);
  const pts = data.map((d,i)=>[i*step, h - 2 - ((d - min)/span)*(h-4)]);
  const line = pts.map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+" "+p[1].toFixed(1)).join(" ");
  const area = line + ` L ${w} ${h} L 0 ${h} Z`;
  return (
    <svg className="spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true">
      <path className="area" d={area} />
      <path d={line} />
    </svg>
  );
}

/* timestamp + relative */
function relTime(days){
  if (days === null || days === undefined) return null;
  if (days === 0) return "today";
  if (days < 30) return days + "d ago";
  if (days < 365) return Math.round(days/30) + "mo ago";
  return (days/365).toFixed(1) + "y ago";
}

Object.assign(window, {
  tr, fmtVND, Money, Pct, Badge, statusTone, valueGroupTone,
  Caveat, Kpi, StatusPill, Eyebrow, Sparkline, relTime,
});

/* detailView — Profit / Loss verdict
   ────────────────────────────────────────────────────────────
   A single, glanceable signal: is this order lãi (profit), lỗ (loss),
   lãi mỏng (thin margin), or chưa xác định (indeterminate)?

   Anchored to CHANNEL NET PROFIT — the true bottom line after platform
   fees, not gross. An order can look fine at gross and still lose money
   once the marketplace takes its cut; the verdict tells that truth.

   Truth-first: when COGS is unverified we make NO profit/loss claim —
   we say "chưa xác định" and stop. Never imply a number we can't prove.

   Reads three knobs off <html> (set by the Tweaks panel), matching the
   app's data-lang / data-theme pattern:
     data-verdict-style  bar | rule | gauge   — visual treatment
     data-verdict-thin   <number>             — net-margin %% below which profit is "thin"
     data-verdict-demo   auto | profit | thin | loss | indeterminate
*/

const VERDICT_META = {
  profit:        { tone:"moss",  color:"var(--moss-500)",  en:"Profitable",   vi:"Lãi",          eyebrow_en:"PROFIT",       eyebrow_vi:"LÃI" },
  thin:          { tone:"honey", color:"var(--honey-500)", en:"Thin margin",  vi:"Lãi mỏng",     eyebrow_en:"THIN MARGIN",  eyebrow_vi:"LÃI MỎNG" },
  loss:          { tone:"coral", color:"var(--coral-500)", en:"Loss",         vi:"Lỗ",           eyebrow_en:"LOSS",         eyebrow_vi:"LỖ" },
  indeterminate: { tone:"mute",  color:"var(--fg-tertiary)", en:"Unverified", vi:"Chưa xác định", eyebrow_en:"UNVERIFIED",   eyebrow_vi:"CHƯA XÁC ĐỊNH" },
};

function deriveVerdict(f){
  const root = document.documentElement;
  const thin = parseFloat(root.getAttribute("data-verdict-thin")) || 10;
  const demo = root.getAttribute("data-verdict-demo") || "auto";

  const indeterminate = (f.cogs_amount === null || f.channel_net_profit === null);
  let state;
  if (demo !== "auto"){
    state = demo;
  } else if (indeterminate){
    state = "indeterminate";
  } else if (f.channel_net_profit < 0){
    state = "loss";
  } else if (f.channel_net_margin_pct < thin){
    state = "thin";
  } else {
    state = "profit";
  }

  return {
    state,
    meta: VERDICT_META[state],
    thin,
    profit: f.channel_net_profit,        // null when unverified
    margin: f.channel_net_margin_pct,    // null when unverified
    gross:  f.gross_profit,
    fees:   f.platform_fees,
    real_indeterminate: indeterminate,
  };
}

/* one-line plain-language explanation — Fraunces voice for the rule treatment */
function verdictLine(v){
  const m = (v.margin == null) ? null : v.margin.toFixed(1) + "%";
  if (v.state === "indeterminate"){
    return tr("Profit can't be computed — COGS is unverified for this order.",
              "Chưa thể tính lãi/lỗ — giá vốn (COGS) chưa được xác minh cho đơn này.");
  }
  if (v.state === "loss"){
    if (v.gross != null && v.gross > 0){
      return tr(`Gross looked positive (+${fmtVND(v.gross)}) but ${fmtVND(v.fees)} of platform fees turned it into a ${fmtVND(Math.abs(v.profit))} loss.`,
                `Lợi nhuận gộp vẫn dương (+${fmtVND(v.gross)}) nhưng ${fmtVND(v.fees)} phí sàn đẩy đơn thành lỗ ${fmtVND(Math.abs(v.profit))}.`);
    }
    return tr(`This order loses ${fmtVND(Math.abs(v.profit))} after every fee — a ${m} net margin.`,
              `Đơn này lỗ ${fmtVND(Math.abs(v.profit))} sau mọi chi phí — biên ròng ${m}.`);
  }
  if (v.state === "thin"){
    return tr(`Only ${fmtVND(v.profit)} survives after fees — a slim ${m} net margin.`,
              `Chỉ còn ${fmtVND(v.profit)} sau chi phí — biên ròng mỏng ${m}.`);
  }
  return tr(`Clears ${fmtVND(v.profit)} after every fee — a comfortable ${m} net margin.`,
            `Lãi ${fmtVND(v.profit)} sau mọi chi phí — biên ròng ${m} thoải mái.`);
}

/* signed money + signed margin, mono */
function SignedMoney({ v }){
  if (v == null) return <span className="dash">—</span>;
  const sign = v < 0 ? "−" : v > 0 ? "+" : "";
  return <span>{sign}{fmtVND(Math.abs(v))}</span>;
}
function SignedPct({ v }){
  if (v == null) return <span className="dash">—</span>;
  const sign = v < 0 ? "−" : "";
  return <span>{sign}{Math.abs(v).toFixed(1)}%</span>;
}

/* ── Treatment A — verdict bar (tinted slab) ── */
function VerdictBar({ v }){
  return (
    <div className={"verdict verdict--bar verdict--"+v.meta.tone}>
      <span className="verdict-dot" aria-hidden="true" />
      <div className="verdict-bar__body">
        <div className="verdict-word">{tr(v.meta.en, v.meta.vi)}</div>
        <div className="verdict-line">{verdictLine(v)}</div>
      </div>
      <div className="verdict-bar__figs">
        <div className="verdict-net"><SignedMoney v={v.profit} /></div>
        <div className="verdict-sub">
          <SignedPct v={v.margin} /> {tr("net","ròng")}
          {v.state !== "indeterminate" && v.gross != null &&
            <> · {tr("gross","gộp")} <SignedMoney v={v.gross} /></>}
        </div>
      </div>
    </div>
  );
}

/* ── Treatment B — rule strip (sanctioned 2px left border, editorial voice) ── */
function VerdictRule({ v }){
  return (
    <div className={"verdict verdict--rule verdict--"+v.meta.tone}>
      <div className="verdict-rule__eyebrow">
        <span className="verdict-dot verdict-dot--sm" aria-hidden="true" />
        {tr("Verdict","Kết luận")} · {tr(v.meta.eyebrow_en, v.meta.eyebrow_vi)}
      </div>
      <p className="verdict-rule__voice voice"><em>{verdictLine(v)}</em></p>
    </div>
  );
}

/* ── Treatment C — margin gauge (segmented meter + marker) ── */
function VerdictGauge({ v }){
  const MIN = -15, MAX = 45, RANGE = MAX - MIN;
  const thin = v.thin;
  const lossW = ((0 - MIN) / RANGE) * 100;
  const thinW = (thin / RANGE) * 100;
  const goodW = ((MAX - thin) / RANGE) * 100;
  const hasMark = v.margin != null && v.state !== "indeterminate";
  const clamped = hasMark ? Math.max(MIN, Math.min(MAX, v.margin)) : 0;
  const pos = ((clamped - MIN) / RANGE) * 100;

  return (
    <div className={"verdict verdict--gauge verdict--"+v.meta.tone}>
      <div className="verdict-gauge__head">
        <div className="verdict-gauge__verdict">
          <span className="verdict-dot verdict-dot--sm" aria-hidden="true" />
          <span className="verdict-word">{tr(v.meta.en, v.meta.vi)}</span>
        </div>
        <div className="verdict-gauge__figs">
          <span className="verdict-net"><SignedMoney v={v.profit} /></span>
          <span className="verdict-gauge__pct"><SignedPct v={v.margin} /> {tr("net","ròng")}</span>
        </div>
      </div>
      <div className="vg-track" role="img"
        aria-label={tr("Net margin", "Biên ròng") + " " + (v.margin==null?"—":v.margin.toFixed(1)+"%")}>
        <span className="vg-zone vg-zone--loss" style={{width: lossW+"%"}} />
        <span className="vg-zone vg-zone--thin" style={{width: thinW+"%"}} />
        <span className="vg-zone vg-zone--good" style={{width: goodW+"%"}} />
        {hasMark && <span className="vg-mark" style={{left: pos+"%"}} />}
        {!hasMark && <span className="vg-mark vg-mark--none" />}
      </div>
      <div className="vg-scale">
        <span>{tr("Loss","Lỗ")}</span>
        <span className="vg-scale__zero">0</span>
        <span>{thin}%</span>
        <span>{MAX}%+</span>
      </div>
    </div>
  );
}

function ProfitVerdict({ o }){
  const v = deriveVerdict(o.financial);
  const style = document.documentElement.getAttribute("data-verdict-style") || "bar";
  if (style === "rule")  return <VerdictRule v={v} />;
  if (style === "gauge") return <VerdictGauge v={v} />;
  return <VerdictBar v={v} />;
}

/* ── Sidebar glance chip — always-visible, compact, same logic ── */
function VerdictGlance({ o }){
  const v = deriveVerdict(o.financial);
  return (
    <div className={"verdict-glance verdict--"+v.meta.tone}
      title={verdictLine(v)}>
      <span className="verdict-dot verdict-dot--sm" aria-hidden="true" />
      <span className="verdict-glance__word">{tr(v.meta.en, v.meta.vi)}</span>
      <span className="verdict-glance__fig">
        {v.state === "indeterminate"
          ? <span className="dash">—</span>
          : <><span className="verdict-glance__pct"><SignedPct v={v.margin} /></span> <SignedMoney v={v.profit} /></>}
      </span>
    </div>
  );
}

Object.assign(window, { deriveVerdict, ProfitVerdict, VerdictGlance, VERDICT_META });

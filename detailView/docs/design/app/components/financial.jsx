/* detailView — Financial tab (redesigned)
   ═══════════════════════════════════════════════════════════
   Zones top → bottom:
   1. Verdict bar + COGS source badge + fully-loaded footnote
   2. Composition bar (where the money goes)
   3. P&L Waterfall (VAT bridge, EN labels, VN tooltips, % before amount)
   4. Cost breakdown (grouped ledger + PROMO_GOODS, OVERHEAD)
   5. COGS reconciliation (collapsed, audit-only)
   ═══════════════════════════════════════════════════════════ */

/* ── tooltip data (EN label → VN name + definition) ─────── */
const TOOLTIP_MAP = {
  "Gross revenue":          "Doanh thu gộp — Giá bán × SL, trước chiết khấu, đã gồm VAT.",
  "Discount":               "Chiết khấu — Coupon, khuyến mãi, combo, giảm giá nhân viên…",
  "Total collected":        "Tổng thu từ khách — Số tiền khách thực trả, VAT đã nhúng.",
  "Tax amount":             "VAT nhúng trong giá bán — Sapo tính sẵn 8/108 hoặc 10/110; 0 cho xuất khẩu.",
  "Net revenue":            "Doanh thu thuần — Sau chiết khấu, đã trừ VAT — con số P&L.",
  "COGS":                   "Giá vốn hàng bán — Giá vốn bình quân gia quyền lúc xuất. Cơ sở không-VAT.",
  "Gross profit":           "Lãi gộp — Net Revenue − COGS.",
  "Promo goods cost":       "Chi phí hàng tặng — Giá vốn hàng KM/biếu tặng, chi phí marketing.",
  "Platform fees":          "Phí sàn — Phí sàn TMĐT (hạ tầng, voucher Xtra, phí xử lý giao dịch…).",
  "Channel net profit":     "Lãi đóng góp (theo kênh) — Số để ra quyết định nhận/đẩy đơn.",
  "Allocated overhead":     "Chi phí vận hành phân bổ — Chi phí quản lý DN phân bổ xuống đơn; ước tính.",
  "Fully-loaded net profit":"Lãi ròng đầy đủ — Lãi đóng góp − chi phí vận hành. Để báo cáo.",
};

const COGS_BADGE_TIP = {
  "sapo_mac": "Giá vốn từ tồn kho Sapo (phủ ~100% đơn đã giao)",
  "misa":     "Giá vốn kế toán TK632 từ MISA",
  "both":     "Có cả Sapo-MAC và MISA (đối chiếu được)",
  "none":     "Chưa có giá vốn → margin chưa xác định",
};

const COGS_BADGE_TONE = {
  "sapo_mac": "good",
  "misa":     "neutral",
  "both":     "good",
  "none":     "warn",
};

const COGS_BADGE_LABEL = {
  "sapo_mac": "Sapo-MAC",
  "misa":     "MISA",
  "both":     "Sapo + MISA",
  "none":     "No COGS",
};

/* ── COGS source badge ────────────────────────────────────── */
function CogsBadge({ source }){
  if (!source) return null;
  const tone = COGS_BADGE_TONE[source] || "neutral";
  const label = COGS_BADGE_LABEL[source] || source;
  const tip = COGS_BADGE_TIP[source] || "";
  return <Badge tone={tone} dot><span title={tip}>{label}</span></Badge>;
}

/* ── Fully-loaded footnote ────────────────────────────────── */
function FullyLoadedNote({ f }){
  if (f.allocated_overhead == null || f.fully_loaded_net_profit == null) return null;
  const sign = f.fully_loaded_net_profit >= 0 ? "+" : "−";
  return (
    <div className="fl-note" title={TOOLTIP_MAP["Fully-loaded net profit"]}>
      <span className="fl-note__mark">ⓘ</span>
      <span>
        {tr("After operating cost allocation (est.):","Sau phân bổ chi phí vận hành (ước tính):")}{" "}
        <span className="fl-note__fig">
          {tr("Fully-loaded net profit","Lãi ròng đầy đủ")}{" "}
          <span className="mono">{sign}{fmtVND(Math.abs(f.fully_loaded_net_profit))}</span>
          {f.fully_loaded_margin_pct != null && <span className="mono"> · {f.fully_loaded_margin_pct.toFixed(1)}%</span>}
        </span>
      </span>
    </div>
  );
}

/* ── Composition bar ──────────────────────────────────────── */
function CompositionBar({ f }){
  const net = f.net_revenue;
  if (!net || net <= 0) return null;

  const cogs  = f.cogs_amount || 0;
  const promo = f.promo_goods_cost || 0;
  const fees  = f.platform_fees || 0;
  const oh    = f.allocated_overhead || 0;
  const costs = cogs + promo + fees + oh;
  const profit = net - costs;

  const pct = (v) => Math.max(0, (v / net) * 100);
  const segments = [];
  if (cogs  > 0) segments.push({ key:"cogs",   cls:"comp-seg--cogs",   w: pct(cogs),   label: tr("COGS","Giá vốn"),               amount: cogs });
  if (promo > 0) segments.push({ key:"promo",  cls:"comp-seg--promo",  w: pct(promo),  label: tr("Promo","Hàng tặng"),             amount: promo });
  if (fees  > 0) segments.push({ key:"fees",   cls:"comp-seg--fees",   w: pct(fees),   label: tr("Platform fees","Phí sàn"),       amount: fees });
  if (oh    > 0) segments.push({ key:"oh",     cls:"comp-seg--oh",     w: pct(oh),     label: tr("Overhead","Vận hành"),            amount: oh });
  segments.push({
    key: "profit",
    cls: profit >= 0 ? "comp-seg--profit" : "comp-seg--loss",
    w: pct(Math.abs(profit)),
    label: profit >= 0 ? tr("Profit","Lãi ròng") : tr("Loss","Lỗ"),
    amount: profit
  });

  // If total > 100%, normalize (happens when profit is negative)
  const totalW = segments.reduce((a, s) => a + s.w, 0);
  const scale = totalW > 100 ? 100 / totalW : 1;

  return (
    <div className="comp-bar-wrap">
      <div className="comp-bar__head">
        <span className="comp-bar__title caption">
          {tr("NET REVENUE COMPOSITION","CƠ CẤU DOANH THU THUẦN")}
        </span>
      </div>
      <div className="comp-bar" role="img"
        aria-label={tr("Revenue composition","Cơ cấu doanh thu")}>
        {segments.map(s => (
          <div key={s.key} className={"comp-seg " + s.cls}
            style={{ width: (s.w * scale).toFixed(1) + "%" }}
            title={s.label + " " + (s.w).toFixed(1) + "%"}>
            {s.w * scale > 8 && <span className="comp-seg__pct">{Math.round(s.w)}%</span>}
          </div>
        ))}
      </div>
      <div className="comp-legend">
        {segments.map(s => (
          <span key={s.key} className="comp-legend__item">
            <i className={"comp-legend__dot " + s.cls} />
            {s.label}
            <span className="comp-legend__pct mono">{s.w.toFixed(1)}%</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── Enhanced waterfall row (4-column: op | label | pct | amount) ── */
function WfRowPL({ op, label, tooltip, pctVal, amount, neg, total, result, decision }){
  const opCls = op === "+" ? "wf-op--add"
    : op === "−" ? "wf-op--sub"
    : op === "=" ? "wf-op--eq" : "";
  const rowCls = "wf-row wf-row--pl"
    + (total ? " wf-row--total" : "")
    + (result ? " wf-row--result" : "")
    + (decision ? " wf-row--decision" : "");
  const tipText = tooltip ? (TOOLTIP_MAP[tooltip] || tooltip) : null;
  return (
    <div className={rowCls}>
      <div className={"wf-op " + opCls}>{op}</div>
      <div className="wf-label" title={tipText || undefined}>
        {label}
      </div>
      <div className="wf-pct mono">
        {pctVal != null && <span>{pctVal.toFixed(1)}%</span>}
      </div>
      <div className={"wf-amt" + (neg ? " wf-amt--neg" : "")}>
        {neg ? "−" : ""}<Money v={amount} />
      </div>
    </div>
  );
}

/* ── Main Financial component (redesigned) ────────────────── */
function OrderFinancialNew({ o }){
  const f = o.financial;

  /* US CrossBorder — keep existing variant */
  if (f.is_us){
    return (
      <div className="tabpanel stack-4">
        <PanelHead title={tr("Financial","Tài chính")} sub="fact_us_shipment_economics" />
        <ProfitVerdict o={o} />
        {f.cogs_source && <div className="verdict-addons"><CogsBadge source={f.cogs_source} /></div>}
        <Caveat tone="warn" rule>
          <b>{tr("US CrossBorder order.","Đơn US CrossBorder.")}</b> {tr("Domestic","Doanh thu nội địa")} <span className="mono">net_revenue = 0</span> {tr("— revenue is sourced from US shipment economics.","— doanh thu lấy từ kinh tế lô hàng US.")}
        </Caveat>
        <div className="waterfall">
          <WfRow op=" " label={tr("US revenue (excl VAT)","Doanh thu US (trước VAT)")} amount={f.us_revenue_excl_vat} bar={92} />
          <WfRow op="+" label={tr("US VAT / sales tax","VAT / thuế US")} amount={f.tax_amount} />
          <WfRow op="=" label={tr("US revenue (incl VAT)","Doanh thu US (gồm VAT)")} amount={f.us_revenue_incl_vat} total />
          <WfRow op="−" label={<span>{tr("COGS","Giá vốn")} <span className="caption" style={{marginLeft:6}}>MISA</span></span>} amount={f.cogs_amount} neg badge={<Badge tone="good">has_cogs</Badge>} />
          <WfRow op="=" label={<span>{tr("Gross profit","Lợi nhuận gộp")} · <Pct v={f.gross_margin_pct} /></span>} amount={f.gross_profit} result />
        </div>
        <div className="row-flex" style={{gap:"var(--sp-3)"}}>
          <Badge tone="accent" dot>US CrossBorder</Badge>
          <Badge>{f.us_line_item_count} {tr("line items","dòng hàng")}</Badge>
          {f.has_unpriced_sku && <Badge tone="warn" dot>has_unpriced_sku</Badge>}
        </div>
        {f.has_unpriced_sku &&
          <Caveat tone="warn">{tr("One or more SKUs have no US price — line totals may be incomplete.","Một hoặc nhiều SKU chưa có giá US — tổng dòng có thể chưa đầy đủ.")}</Caveat>}
        <Caveat tone="info">{tr("Returns","Trả hàng")}: <Money v={f.return_amount} /> — {tr("reference only, not subtracted from this order's P&L.","chỉ tham chiếu, không trừ vào P&L của đơn.")}</Caveat>
      </div>
    );
  }

  /* Domestic P&L — redesigned */
  const hasCogs     = f.cogs_amount != null;
  const hasPromo    = f.promo_goods_cost != null && f.promo_goods_cost > 0;
  const hasOverhead = f.allocated_overhead != null && f.allocated_overhead > 0;
  const hasPlatform = f.platform_fees > 0;
  const net         = f.net_revenue || 0;
  const cogsSource  = f.cogs_source || (hasCogs ? "misa" : "none");
  const platform    = o.header.channel_name || "platform";

  /* pct helpers — all on net revenue basis */
  const pctOf = (v) => (v != null && net > 0) ? (v / net) * 100 : null;

  return (
    <div className="tabpanel stack-4">
      {/* ── Zone 1: Verdict ── */}
      <PanelHead title={tr("Financial","Tài chính")} sub="fact_orders · fact_order_economics" />
      <div className="verdict-zone">
        <ProfitVerdict o={o} />
        <div className="verdict-addons">
          <CogsBadge source={cogsSource} />
        </div>
        <FullyLoadedNote f={f} />
      </div>

      {/* ── Zone 2: Composition bar ── */}
      {hasCogs && <CompositionBar f={f} />}

      {/* ── Zone 3: P&L Waterfall ── */}
      <div className="waterfall waterfall--pl">
        {/* header row */}
        <div className="wf-row wf-row--head">
          <div className="wf-op"></div>
          <div className="wf-label caption">{tr("P&L LINE","DÒNG P&L")}</div>
          <div className="wf-pct caption" style={{textAlign:"right"}}>%</div>
          <div className="wf-amt caption" style={{textAlign:"right"}}>{tr("AMOUNT","SỐ TIỀN")}</div>
        </div>

        {/* Revenue block (VAT bridge) */}
        <WfRowPL op=" "
          label={<span>{tr("Gross revenue","Doanh thu gộp")} <span className="wf-tag">{tr("[incl VAT]","[gồm VAT]")}</span></span>}
          tooltip="Gross revenue"
          amount={f.gross_revenue} />
        <WfRowPL op="−"
          label={<span>{tr("Discount","Chiết khấu")} <Badge>bundle</Badge></span>}
          tooltip="Discount"
          amount={f.discount_amount} neg />
        <WfRowPL op="="
          label={<span>{tr("Net revenue","Doanh thu thuần")} <span className="wf-tag">{tr("[excl VAT]","[trừ VAT]")}</span></span>}
          tooltip="Net revenue"
          amount={f.net_revenue} total />
        <WfRowPL op="+"
          label={<span>{tr("Tax amount","VAT đầu ra")} <span className="wf-tag">{tr("[embedded in price]","[nhúng trong giá]")}</span></span>}
          tooltip="Tax amount"
          amount={f.tax_amount} />
        <WfRowPL op="="
          label={<span>{tr("Total collected","Tổng thu từ khách")} <span className="wf-tag">{tr("[incl VAT]","[gồm VAT]")}</span></span>}
          tooltip="Total collected"
          amount={f.total_collected} total />

        {/* Cost block */}
        <WfRowPL op="−"
          label={<span>{tr("COGS","Giá vốn")} {cogsSource !== "none" && <CogsBadge source={cogsSource} />}{cogsSource === "none" && <Badge tone="warn" dot>{tr("unverified","chưa xác minh")}</Badge>}</span>}
          tooltip="COGS"
          pctVal={pctOf(f.cogs_amount)}
          amount={f.cogs_amount} neg />
        <WfRowPL op="="
          label={<span>{tr("Gross profit","Lãi gộp")}</span>}
          tooltip="Gross profit"
          pctVal={f.gross_margin_pct}
          amount={f.gross_profit} result />

        {/* Promo goods — conditional */}
        {hasPromo &&
          <WfRowPL op="−"
            label={<span>{tr("Promo goods cost","Chi phí hàng tặng")} <span className="wf-tag">promo</span></span>}
            tooltip="Promo goods cost"
            pctVal={pctOf(f.promo_goods_cost)}
            amount={f.promo_goods_cost} neg />}

        {/* Platform fees */}
        {hasPlatform &&
          <WfRowPL op="−"
            label={<span>{tr("Platform fees","Phí sàn")} <span className="wf-tag">{platform}</span> <span className="wf-detail-link">▸ {tr("detail","chi tiết")}</span></span>}
            tooltip="Platform fees"
            pctVal={pctOf(f.platform_fees)}
            amount={f.platform_fees} neg />}

        {/* ★ DECISION TIER — Channel net profit */}
        <WfRowPL op="="
          label={<span><span className="wf-star" aria-hidden="true">★</span> {tr("Channel net profit","Lãi đóng góp (kênh)")}</span>}
          tooltip="Channel net profit"
          pctVal={f.channel_net_margin_pct}
          amount={f.channel_net_profit} result decision />
      </div>

      {/* Fully-loaded footer (muted, below waterfall, conditional) */}
      {hasOverhead && (
        <div className="wf-footer-muted">
          <div className="wf-footer-row">
            <span className="wf-footer__op">+</span>
            <span className="wf-footer__label">
              {tr("Allocated overhead","Chi phí vận hành phân bổ")}
              {" "}<span className="wf-tag">{tr("[est.]","[ước tính]")}</span>
              {f.is_overhead_estimated && <Badge tone="warn">estimated</Badge>}
            </span>
            <span className="wf-footer__amt mono">−{fmtVND(f.allocated_overhead)}</span>
          </div>
          <div className="wf-footer-row wf-footer-row--result">
            <span className="wf-footer__op">=</span>
            <span className="wf-footer__label">
              {tr("Fully-loaded net profit","Lãi ròng đầy đủ")}
              {" "}<span className="wf-tag">{tr("[for reporting]","[để báo cáo]")}</span>
            </span>
            <span className="wf-footer__amt mono">
              {f.fully_loaded_net_profit != null && (
                <>{f.fully_loaded_net_profit >= 0 ? "+" : "−"}{fmtVND(Math.abs(f.fully_loaded_net_profit))}
                  {f.fully_loaded_margin_pct != null && <span className="wf-footer__pct"> {f.fully_loaded_margin_pct.toFixed(1)}%</span>}
                </>
              )}
            </span>
          </div>
        </div>
      )}

      {/* Caveats */}
      {cogsSource === "none" &&
        <Caveat tone="warn">{tr("Margin unverified — no COGS match for this order.","Biên lợi nhuận chưa kiểm chứng — không khớp giá vốn cho đơn này.")}</Caveat>}
      <Caveat tone="info">{tr("Returns","Trả hàng")}: <Money v={f.return_amount} /> — {tr("reference only, not subtracted from this order's P&L.","chỉ tham chiếu, không trừ vào P&L của đơn.")}</Caveat>
    </div>
  );
}

/* ── Cost ledger (extended: PROMO_GOODS, OVERHEAD) ────────── */
const COST_CAT_TONE = {
  COGS: "good", PLATFORM_FEE: "warn", TAX: "neutral",
  SHIPPING: "neutral", DISCOUNT: "accent",
  PROMO_GOODS: "accent", OVERHEAD: "accent",
};

function CostGroupNew({ g, tone }){
  const [open, setOpen] = useState(true);
  const isNew = g.category === "PROMO_GOODS" || g.category === "OVERHEAD";
  return (
    <div className="group" data-open={open}>
      <div className="group__head" onClick={()=>setOpen(!open)}>
        <div className="group__cat">
          <span className="group__chev">▾</span>
          <Badge tone={tone}>{g.category}</Badge>
          {isNew && <span className="group__new-tag">NEW</span>}
          {g.category === "OVERHEAD" && <span className="wf-tag" style={{marginLeft:6}}>(allocated)</span>}
        </div>
        <span className="group__total"><Money v={g.subtotal} /></span>
      </div>
      <div className="group__body tbl-wrap" style={{borderRadius:0, border:0, borderTop:"1px solid var(--border)"}}>
        <table className="tbl tbl--ledger">
          <colgroup>
            <col className="col-type" />
            <col className="col-source" />
            <col className="col-record" />
            <col className="col-feesrc" />
            <col className="col-amount" />
          </colgroup>
          <thead><tr>
            <th>{tr("Cost type","Loại chi phí")}</th>
            <th>{tr("Source","Nguồn")}</th>
            <th>{tr("Record","Bản ghi")}</th>
            <th>{tr("Fee src","Nguồn phí")}</th>
            <th className="num-h">{tr("Amount","Số tiền")}</th>
          </tr></thead>
          <tbody>
            {g.rows.map((r,i)=>(
              <tr key={i}>
                <td className="cell-strong mono" style={{fontSize:12}}>{r.type}</td>
                <td className="muted">{r.source}</td>
                <td className="mono muted" style={{fontSize:11}}>{r.record}</td>
                <td>{r.fee_source==="actual" ? <Badge tone="good">actual</Badge> : <Badge tone="warn">estimated</Badge>}</td>
                <td className="num"><Money v={r.amount} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function OrderCostLedgerNew({ o }){
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Cost breakdown","Sổ chi phí")} sub="fact_order_costs" />
      <div>
        {o.cost_ledger.map((g,i)=>(
          <CostGroupNew key={i} g={g} tone={COST_CAT_TONE[g.category]||"neutral"} />
        ))}
      </div>
      <Caveat tone="info">{tr("Each row is traceable to its source system + record. Fee source marks actual vs estimated.","Mỗi dòng truy vết được tới hệ nguồn + bản ghi. Nguồn phí đánh dấu thực tế / ước tính.")}</Caveat>
    </div>
  );
}

/* ── COGS Reconciliation (collapsed, audit) ───────────────── */
function CogsReconciliation({ f }){
  if (f.cogs_source !== "both") return null;
  if (f.sapo_mac_cogs == null || f.misa_cogs_632 == null) return null;
  const [open, setOpen] = useState(false);
  const sign = f.cogs_variance >= 0 ? "+" : "−";
  const pctSign = f.cogs_variance_pct >= 0 ? "+" : "−";
  return (
    <div className="tabpanel">
      <div className={"recon-panel" + (open ? " recon-panel--open" : "")} onClick={()=>setOpen(!open)}>
        <div className="recon-panel__head">
          <span className="recon-panel__chev">{open ? "▾" : "▸"}</span>
          <span className="recon-panel__title">
            {tr("COGS reconciliation","Đối chiếu COGS")}
          </span>
          <span className="recon-panel__tag caption">{tr("audit · collapsed by default","kiểm toán · gập mặc định")}</span>
        </div>
        {!open && (
          <div className="recon-panel__preview">
            <span>Sapo-MAC <b className="mono">{fmtVND(f.sapo_mac_cogs)}</b></span>
            <span className="recon-sep">vs</span>
            <span>MISA-632 <b className="mono">{fmtVND(f.misa_cogs_632)}</b></span>
            <span className="recon-sep">·</span>
            <span>{tr("variance","lệch")} <b className="mono">{sign}{fmtVND(Math.abs(f.cogs_variance))} ({pctSign}{Math.abs(f.cogs_variance_pct).toFixed(1)}%)</b></span>
          </div>
        )}
      </div>
      {open && (
        <div className="recon-detail" onClick={e=>e.stopPropagation()}>
          <div className="recon-grid">
            <div className="recon-cell">
              <div className="recon-cell__label caption">SAPO-MAC</div>
              <div className="recon-cell__val mono">{fmtVND(f.sapo_mac_cogs)}</div>
              <div className="recon-cell__sub">{tr("Weighted-avg cost at fulfillment","Giá vốn bình quân gia quyền lúc xuất")}</div>
            </div>
            <div className="recon-cell">
              <div className="recon-cell__label caption">MISA TK632</div>
              <div className="recon-cell__val mono">{fmtVND(f.misa_cogs_632)}</div>
              <div className="recon-cell__sub">{tr("Accounting COGS (ledger 632)","Giá vốn kế toán TK632")}</div>
            </div>
            <div className="recon-cell recon-cell--var">
              <div className="recon-cell__label caption">{tr("VARIANCE","LỆCH")}</div>
              <div className={"recon-cell__val mono" + (Math.abs(f.cogs_variance_pct) > 5 ? " recon-cell__val--warn" : "")}>
                {sign}{fmtVND(Math.abs(f.cogs_variance))}
              </div>
              <div className="recon-cell__sub mono">{pctSign}{Math.abs(f.cogs_variance_pct).toFixed(1)}%</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Compose the Financial tab ────────────────────────────── */
function OrderFinancialTabNew({ o }){
  return (
    <div className="tab-sections">
      <OrderFinancialNew o={o} />
      <OrderCostLedgerNew o={o} />
      <CogsReconciliation f={o.financial} />
    </div>
  );
}

/* Export to global scope */
Object.assign(window, {
  OrderFinancialNew, OrderCostLedgerNew, CogsReconciliation, OrderFinancialTabNew,
  CogsBadge, FullyLoadedNote, CompositionBar, WfRowPL, CostGroupNew,
});

/* detailView — Order tab panels */

function WfRow({ op, label, badge, amount, neg, total, result, bar }){
  const opCls = op==="+"?"wf-op--add":op==="−"?"wf-op--sub":op==="="?"wf-op--eq":"";
  return (
    <div className={"wf-row"+(total?" wf-row--total":"")+(result?" wf-row--result":"")}>
      <div className={"wf-op "+opCls}>{op}</div>
      <div className="wf-label">{label}{badge}
        {bar !== undefined && <div className="wf-bar" style={{width: Math.max(6, bar)+"%"}} />}
      </div>
      <div className={"wf-amt"+(neg?" wf-amt--neg":"")}>{neg?"−":""}<Money v={amount} /></div>
    </div>
  );
}

function OrderFinancial({ o }){
  const f = o.financial;
  if (f.is_us){
    return (
      <div className="tabpanel stack-4">
        <PanelHead title={tr("Financial","Tài chính")} sub="fact_us_shipment_economics" />
        <ProfitVerdict o={o} />
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
  const maxRef = f.gross_revenue || f.total_collected;
  const bar = (x)=> Math.round((x / maxRef) * 100);
  const verified = f.cogs_amount !== null;
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Financial","Tài chính")} sub="fact_orders · fact_order_economics" />
      <ProfitVerdict o={o} />
      <div className="waterfall">
        <WfRow op=" " label={tr("Gross revenue","Doanh thu gộp")} amount={f.gross_revenue} bar={bar(f.gross_revenue)} />
        <WfRow op="−" label={<span>{tr("Discount","Chiết khấu")} <Badge>bundle</Badge></span>} amount={f.discount_amount} neg />
        <WfRow op="=" label={tr("Net revenue","Doanh thu thuần")} amount={f.net_revenue} total bar={bar(f.net_revenue)} />
        <WfRow op="+" label={tr("VAT output","VAT đầu ra")} amount={f.tax_amount} />
        <WfRow op="=" label={tr("Total collected","Tổng thu")} amount={f.total_collected} total />
        <WfRow op="−" label={<span>{tr("COGS","Giá vốn")} <span className="caption" style={{marginLeft:6}}>MISA</span>{!verified && <Badge tone="warn" dot>unverified</Badge>}</span>} amount={f.cogs_amount} neg />
        <WfRow op="=" label={<span>{tr("Gross profit","Lợi nhuận gộp")} · <Pct v={f.gross_margin_pct} /></span>} amount={f.gross_profit} result />
        <WfRow op="−" label={<span>{tr("Platform fees","Phí sàn")} <span className="caption" style={{marginLeft:6}}>service · payment · infra · voucher · tax</span></span>} amount={f.platform_fees} neg />
        <WfRow op="=" label={<span>{tr("Channel net profit","Lợi nhuận ròng kênh")} · <Pct v={f.channel_net_margin_pct} /></span>} amount={f.channel_net_profit} result />
      </div>
      {!verified &&
        <Caveat tone="warn">{tr("Margin unverified — no MISA COGS match for this order.","Biên lợi nhuận chưa kiểm chứng — không khớp giá vốn MISA cho đơn này.")}</Caveat>}
      <Caveat tone="info">{tr("Returns","Trả hàng")}: <Money v={f.return_amount} /> — {tr("reference only, not subtracted from this order's P&L.","chỉ tham chiếu, không trừ vào P&L của đơn.")}</Caveat>
    </div>
  );
}

function OrderLineItems({ o }){
  const items = o.line_items;
  const isUS = o.financial.is_us;
  const sumLine = items.reduce((a,b)=>a+b.line,0);
  const net = o.financial.is_us ? o.financial.us_revenue_excl_vat : o.financial.net_revenue;
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Line items","Dòng hàng")} sub="fact_sales × dim_products" />
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr>
            <th>SKU</th><th>{tr("Product / Variant","Sản phẩm / Biến thể")}</th><th>{tr("Brand","Hãng")}</th>
            <th className="num-h">{tr("Qty","SL")}</th><th className="num-h">{tr("Unit","Đơn giá")}</th>
            <th className="num-h">{tr("Line","Thành tiền")}</th><th className="num-h">{tr("Disc.","CK")}</th>
            {isUS && <th className="num-h">US price</th>}
            <th className="num-h">{tr("Wt (g)","KL (g)")}</th>
          </tr></thead>
          <tbody>
            {items.map((it,i)=>(
              <tr key={i}>
                <td className="num" style={{textAlign:"left"}}>{it.sku}</td>
                <td className="cell-strong">{it.name}<span className="cell-sub">{it.variant} · {it.category}</span></td>
                <td className="muted">{it.brand}</td>
                <td className="num">{it.qty}</td>
                <td className="num"><Money v={it.unit} /></td>
                <td className="num cell-strong"><Money v={it.line} /></td>
                <td className="num muted">{it.disc?<Money v={it.disc}/>:<span className="dash">—</span>}</td>
                {isUS && <td className="num">{it.us_price ? it.us_price : <span className="dash">—</span>}</td>}
                <td className="num muted">{it.weight}</td>
              </tr>
            ))}
          </tbody>
          <tfoot><tr>
            <td colSpan={isUS?6:5}>Σ {tr("line revenue","doanh thu dòng")}</td>
            <td className="num cell-strong" colSpan={isUS?3:3}><Money v={sumLine} /> {sumLine===net
              ? <Badge tone="good">{tr("matches net","khớp thuần")}</Badge>
              : <Badge tone="warn">Δ <Money v={Math.abs(sumLine-net)} /></Badge>}</td>
          </tr></tfoot>
        </table>
      </div>
      <Caveat tone="info">{tr("No per-line COGS — cost of goods is recorded at order level only.","Không có giá vốn theo dòng — giá vốn chỉ ghi nhận ở cấp đơn.")}</Caveat>
    </div>
  );
}

function OrderCostLedger({ o }){
  const cat = { COGS:"good", PLATFORM_FEE:"warn", TAX:"neutral", SHIPPING:"neutral", DISCOUNT:"accent" };
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Cost ledger","Sổ chi phí")} sub="fact_order_costs" />
      <div>
        {o.cost_ledger.map((g,i)=>(
          <CostGroup key={i} g={g} tone={cat[g.category]||"neutral"} />
        ))}
      </div>
      <Caveat tone="info">{tr("Each row is traceable to its source system + record. Fee source marks actual vs estimated.","Mỗi dòng truy vết được tới hệ nguồn + bản ghi. Nguồn phí đánh dấu thực tế / ước tính.")}</Caveat>
    </div>
  );
}
function CostGroup({ g, tone }){
  const [open, setOpen] = useState(true);
  return (
    <div className="group" data-open={open}>
      <div className="group__head" onClick={()=>setOpen(!open)}>
        <div className="group__cat">
          <span className="group__chev">▾</span>
          <Badge tone={tone}>{g.category}</Badge>
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
          <thead><tr><th>{tr("Cost type","Loại chi phí")}</th><th>{tr("Source","Nguồn")}</th><th>{tr("Record","Bản ghi")}</th><th>{tr("Fee src","Nguồn phí")}</th><th className="num-h">{tr("Amount","Số tiền")}</th></tr></thead>
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

function OrderPayments({ o }){
  const total = o.payments.reduce((a,b)=>a+b.amount,0);
  const cod = o.payments.filter(p=>p.type==="COD").reduce((a,b)=>a+b.amount,0);
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Payments","Thanh toán")} sub="fact_payments × dim_payment_methods" />
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr><th>{tr("Method","Phương thức")}</th><th>{tr("Type","Loại")}</th><th>{tr("Status","Trạng thái")}</th><th>{tr("Paid on","Ngày trả")}</th><th className="num-h">{tr("Amount","Số tiền")}</th></tr></thead>
          <tbody>
            {o.payments.map((p,i)=>(
              <tr key={i}>
                <td className="cell-strong">{p.method}</td>
                <td className="muted mono" style={{fontSize:12}}>{p.type}</td>
                <td><Badge tone={statusTone(p.status)} dot>{p.status}</Badge></td>
                <td className="mono muted" style={{fontSize:12}}>{p.paid_on}</td>
                <td className="num cell-strong"><Money v={p.amount} /></td>
              </tr>
            ))}
          </tbody>
          <tfoot><tr><td colSpan={4}>Σ {tr("paid","đã trả")} · {cod?tr("COD","COD"):tr("prepaid","trả trước")} {cod?Math.round(cod/total*100):0}%</td><td className="num cell-strong"><Money v={total} /></td></tr></tfoot>
        </table>
      </div>
    </div>
  );
}

/* ── Shipments (leg-level fulfillment) ─────────────────────────────
   An order has 0..N shipment legs. Each leg carries its own status,
   tracking code, carrier/service, and (for COD) a cash amount the
   carrier collects. Designed for N — sorted newest-first by shipped_at,
   NULLs (not-yet-shipped) last. ── */

const SHIP_NOW = new Date("2026-05-30T17:00:00+07:00").getTime();

function shipTone(st){
  if (st === "DELIVERED") return "good";
  if (st === "SHIPPING" || st === "PENDING") return "warn";
  if (st === "CANCELLED" || st === "FAILED") return "bad";
  return "neutral"; // PACKED
}
function shipWord(st){
  const en = { DELIVERED:"delivered", SHIPPING:"shipping", PACKED:"packed", PENDING:"pending", CANCELLED:"cancelled", FAILED:"failed" };
  const vi = { DELIVERED:"đã giao", SHIPPING:"đang giao", PACKED:"đã đóng", PENDING:"chờ xử lý", CANCELLED:"đã huỷ", FAILED:"thất bại" };
  return tr(en[st] || st.toLowerCase(), vi[st] || st.toLowerCase());
}
function shipAgo(dt){
  if (!dt) return null;
  const t = new Date(dt.replace(" ","T") + ":00+07:00").getTime();
  const ms = SHIP_NOW - t;
  if (ms < 3600000) return tr("just now","vừa xong");
  const d = Math.floor(ms / 86400000);
  if (d < 1) return Math.floor(ms/3600000) + tr("h ago"," giờ trước");
  if (d < 30) return d + tr("d ago"," ngày trước");
  if (d < 365) return Math.round(d/30) + tr("mo ago"," tháng trước");
  return (d/365).toFixed(1) + tr("y ago"," năm trước");
}
function shipSortDesc(a,b){
  if (!a.shipped_at && !b.shipped_at) return 0;
  if (!a.shipped_at) return 1;
  if (!b.shipped_at) return -1;
  return a.shipped_at < b.shipped_at ? 1 : a.shipped_at > b.shipped_at ? -1 : 0;
}
function shipSummary(ships){
  const ord = ["DELIVERED","SHIPPING","PACKED","PENDING","CANCELLED","FAILED"];
  const c = {};
  ships.forEach(s => { c[s.status] = (c[s.status]||0) + 1; });
  return ord.filter(k => c[k]).map(k => ({ status:k, count:c[k], tone:shipTone(k) }));
}

/* hand-drawn glyphs — Precision style: 1.3–1.6 stroke, round caps, currentColor */
function CopyGlyph(){
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor"
      strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="4.3" y="4.3" width="6.4" height="6.4" rx="1.2" />
      <path d="M8.4 2.3H3.4a1.1 1.1 0 0 0-1.1 1.1v5" />
    </svg>
  );
}
function CheckGlyph(){
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none" stroke="currentColor"
      strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2.7 6.8 5.3 9.4 10.3 3.7" />
    </svg>
  );
}

/* tiny stage indicator: PACKED → SHIPPING → DELIVERED.
   CANCELLED / FAILED render as a distinct error marker. */
function ShipStages({ status }){
  if (status === "CANCELLED" || status === "FAILED"){
    return (
      <span className="ship-stages ship-stages--err" title={shipWord(status)} aria-hidden="true">
        <span className="ship-stages__err">✕</span>
      </span>
    );
  }
  const stages = ["PACKED","SHIPPING","DELIVERED"];
  const idx = stages.indexOf(status); // PENDING → -1 (none lit yet)
  return (
    <span className="ship-stages" title={tr("packed → shipping → delivered","đóng → giao → nhận")} aria-hidden="true">
      {stages.map((s,i) => (
        <React.Fragment key={s}>
          {i > 0 && <span className={"ship-stages__bar" + (i <= idx ? " is-on" : "")} />}
          <span className={"ship-stages__node" + (i <= idx ? " is-on" : "") + (i === idx ? " is-now" : "")} />
        </React.Fragment>
      ))}
    </span>
  );
}

function ShipmentCard({ s }){
  const [copied, setCopied] = useState(false);
  const tone = shipTone(s.status);
  const ago = shipAgo(s.shipped_at);
  const copy = () => {
    const done = () => { setCopied(true); setTimeout(()=>setCopied(false), 1500); };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(s.tracking_code).then(done, done);
      } else { done(); }
    } catch(e){ done(); }
  };
  return (
    <div className={"ship-card" + (copied ? " ship-card--copied" : "") + (tone==="bad" ? " ship-card--bad" : "")}>
      <div className="ship-card__top">
        <div className="ship-card__lead">
          <Badge tone={tone} dot>{s.status}</Badge>
          <ShipStages status={s.status} />
        </div>
        <div className="ship-card__carrier">
          <span className="ship-carrier__name">{s.carrier}</span>
          <span className="ship-sep">·</span>
          <span className="ship-carrier__svc">{s.shipping_service}</span>
        </div>
      </div>

      <button type="button" className="ship-track" onClick={copy}
        title={tr("Copy tracking code","Sao chép mã vận đơn")}
        aria-label={tr("Tracking code","Mã vận đơn") + " " + s.tracking_code + " — " + tr("copy","sao chép")}>
        <span className="ship-track__label">{tr("Tracking","Mã vận đơn")}</span>
        <span className="ship-track__code">{s.tracking_code}</span>
        <span className={"ship-track__copy" + (copied ? " is-copied" : "")} aria-hidden="true">
          {copied ? <><CheckGlyph /> {tr("copied","đã chép")}</> : <><CopyGlyph /> {tr("copy","chép")}</>}
        </span>
      </button>

      <div className="ship-card__meta">
        <span className="ship-meta__code mono">{s.fulfillment_code}</span>
        <span className="ship-meta__sep">·</span>
        <span className="ship-meta__time">
          {s.shipped_at
            ? <>{tr("shipped","gửi")} <span className="mono">{s.shipped_at}</span> <span className="ship-meta__rel">(ICT · {ago})</span></>
            : <span className="ship-meta__null">{tr("not shipped yet","chưa gửi đi")}</span>}
        </span>
        <span className="ship-meta__sep">·</span>
        <span className="ship-meta__cod">
          {s.cod_amount > 0
            ? <>COD <b className="mono"><Money v={s.cod_amount} /></b></>
            : <span className="muted">COD <span className="dash">—</span></span>}
        </span>
      </div>
    </div>
  );
}

function OrderShipments({ o }){
  const ships = (o.shipments || []).slice().sort(shipSortDesc);
  const n = ships.length;

  return (
    <div className="tabpanel stack-4">
      <div className="panel-head ship-head">
        <div className="ship-head__title">
          <span className="panel-title">{tr("Shipments","Vận đơn")}</span>
          {n > 0 && <span className="ship-count">{n}</span>}
        </div>
        {n > 0
          ? <div className="ship-summary">
              {shipSummary(ships).map((g,i) => (
                <span className="ship-summary__seg" key={g.status}>
                  <i className={"ship-tone-dot ship-tone-dot--" + g.tone} />
                  {g.count} {shipWord(g.status)}
                </span>
              ))}
            </div>
          : <div className="panel-sub">fact_fulfillments · leg-level</div>}
      </div>

      {n === 0
        ? <div className="ship-empty">
            <div className="ship-empty__title voice"><em>{tr("No shipments yet","Chưa có vận đơn")}</em></div>
            <p className="ship-empty__sub">
              {tr("This order has no shipment legs.","Đơn này chưa có chặng giao nào.")}{" "}
              {tr("Fulfillment status is","Trạng thái vận hành là")}{" "}
              <Badge tone={statusTone(o.header.fulfillment_status)} dot>{o.header.fulfillment_status}</Badge>.
            </p>
          </div>
        : <div className="ship-list">
            {ships.map((s,i) => <ShipmentCard key={s.fulfillment_code + i} s={s} />)}
          </div>}

      <div className="note-line">
        <span className="caveat__mark">ⓘ</span>
        <span>{tr("Tracking codes are copy-only — no carrier link map in the serving layer yet.","Mã vận đơn chỉ sao chép — chưa có bản đồ liên kết hãng trong tầng phục vụ.")}</span>
      </div>
    </div>
  );
}

function OrderRecipient({ o, onNavigate }){
  const p = o.parties;
  if (!p){ return null; }
  const r = p.recipient;
  const cust = window.DV_DATA.customers[p.buyer_id];
  const fullAddr = [r.address1, r.ward, r.district, r.province].filter(x=>x && x!=="—").join(", ")
    + (r.country && r.country!=="Việt Nam" ? ", "+r.country : "");
  const goCust = ()=> cust && onNavigate && onNavigate({page:"customer", id:cust.profile.customer_id});

  const relNote = p.relation==="GIFT"
    ? tr("Gift order — the recipient is not the buyer. Use recipient details for any delivery contact; use the buyer for payment, value and history.",
         "Đơn quà tặng — người nhận không phải người mua. Mọi liên hệ giao hàng dùng thông tin người nhận; thanh toán, giá trị và lịch sử dùng người mua.")
    : p.relation==="CROSSBORDER"
    ? tr("Crossborder order — the recipient is the end customer abroad. The buyer placed and paid the order in Vietnam.",
         "Đơn xuyên biên — người nhận là khách cuối ở nước ngoài. Người mua đặt và thanh toán đơn tại Việt Nam.")
    : tr("The recipient differs from the buyer on this order.",
         "Người nhận khác với người mua trên đơn này.");

  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Recipient & delivery","Người nhận & giao hàng")} sub="fact_orders · recipient" />
      <div className="party-split">
        {/* recipient — operational priority. Mirror the buyer card's
           structure (eyebrow → name → badge-row → facts) so the two
           columns read in parallel and the badges align on one row. */}
        <div className="scard scard--recipient scard--lead">
          <Eyebrow accent>{tr("Recipient — receives the goods","Người nhận — nhận hàng")}</Eyebrow>
          <div className="recipient-name" style={{marginTop:"var(--sp-2)"}}>{r.name}</div>
          <div className="badge-row">
            {p.same
              ? <Badge tone="good" dot>{tr("same as buyer","trùng người mua")}</Badge>
              : <Badge tone="warn" dot>{tr("differs from buyer","khác người mua")}</Badge>}
          </div>
          <div className="facts" style={{marginTop:"var(--sp-3)"}}>
            <Fact k={tr("Phone","Điện thoại")} v={r.phone} mono />
            <Fact k={tr("Address","Địa chỉ")} v={fullAddr} />
            {r.country && r.country!=="Việt Nam" && <Fact k={tr("Country","Quốc gia")} v={r.country} />}
          </div>
        </div>
        {/* buyer — the account that placed & paid */}
        <div className="scard">
          <Eyebrow>{tr("Buyer — placed & paid","Người mua — đặt & trả tiền")}</Eyebrow>
          <div className="recipient-name recipient-name--muted" style={{marginTop:"var(--sp-2)"}}>{cust ? cust.profile.full_name : "—"}</div>
          {cust &&
            <>
              <div className="badge-row">
                <Badge>{cust.profile.customer_type}</Badge>
                <Badge tone={valueGroupTone(cust.profile.value_group)} dot>{cust.profile.value_group}</Badge>
              </div>
              <div className="facts" style={{marginTop:"var(--sp-3)"}}>
                <Fact k={tr("Phone","Điện thoại")} v={cust.profile.phone} mono />
                <Fact k={tr("LTV","Giá trị vòng đời")} v={fmtVND(cust.value.ltv)} mono />
              </div>
              <button className="btn btn--secondary party-cta" onClick={goCust}>
                {tr("Open customer","Mở khách hàng")} <span className="mono">→</span>
              </button>
            </>}
        </div>
      </div>
      {!p.same && <Caveat tone="warn" rule>{relNote}</Caveat>}
      {r.note && <Caveat tone="info">{r.note}</Caveat>}
    </div>
  );
}

function OrderFulfillment({ o }){
  const h = o.header, ff = o.fulfillment;
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Fulfillment","Vận hành giao")} sub="fact_orders · fact_order_economics" />
      <div className="row-flex" style={{gap:"var(--sp-2)"}}>
        <Badge tone={statusTone(h.status)} dot>{h.status}</Badge>
        <Badge tone={statusTone(h.payment_status)} dot>{h.payment_status}</Badge>
        <Badge tone={statusTone(h.fulfillment_status)} dot>{h.fulfillment_status}</Badge>
      </div>
      <div className="facts scard">
        <Fact k={tr("Shipped","Đã gửi")} v={h.first_shipped_at} mono />
        <Fact k={tr("Carrier","Vận chuyển")} v={ff.carrier} />
        <Fact k={tr("COD","Thu hộ")} v={ff.cod_amount ? fmtVND(ff.cod_amount) : "—"} mono />
        <Fact k="TTC" v={ff.ttc_hours ? ff.ttc_hours+"h" : tr("in transit","đang giao")} mono />
      </div>
      <Caveat tone="info">{tr("Order-level summary. Per-leg carrier codes and live status are in Shipments above.","Tổng quan cấp đơn. Mã hãng và trạng thái từng chặng ở mục Vận đơn phía trên.")}</Caveat>
    </div>
  );
}

/* ── Returns (leg-level refund events) ─────────────────────────────
   Low-volume: most orders have 0, a few have exactly 1. Muted by
   default — only the refund money and refund_status carry signal.
   Reference only; never deducted from the order's P&L. ── */
function titleCase(s){
  if (!s) return "";
  return s.replace(/\w\S*/g, w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
}

function ReturnCard({ r }){
  const refundTone = r.refund_status === "paid" ? "good" : "warn";
  const retTone = r.return_status === "cancelled" ? "bad" : "neutral";
  const reason = (r.return_reason || "").trim();
  return (
    <div className="ret-card">
      <div className="ret-card__top">
        <div className="ret-amt mono"><Money v={r.refund_amount} /></div>
        <div className="ret-badges">
          <Badge tone={refundTone} dot>{tr("Refund","Hoàn")}: {titleCase(r.refund_status)}</Badge>
          <Badge tone={retTone}>{titleCase(r.return_status)}</Badge>
        </div>
      </div>
      <div className="ret-card__meta">
        <span className="ret-meta__date mono">{r.return_date}</span>
        <span className="ret-meta__ict">ICT</span>
        <span className="ret-sep">·</span>
        <span>{tr("qty","SL")} {r.return_quantity != null
          ? <span className="mono">{r.return_quantity}</span>
          : <span className="ret-na">—</span>}</span>
      </div>
      <div className="ret-card__reason">
        {reason
          ? <><span className="ret-reason__k">{tr("Reason","Lý do")}</span> {reason}</>
          : <span className="ret-reason__none">{tr("No reason recorded","Không ghi lý do")}</span>}
      </div>
    </div>
  );
}

function OrderReturns({ o }){
  const rs = (o.returns || []).slice().sort((a,b) =>
    a.return_date < b.return_date ? 1 : a.return_date > b.return_date ? -1 : 0);
  const n = rs.length;
  const totalRefunded = rs.filter(r => r.refund_status === "paid")
    .reduce((a,b) => a + b.refund_amount, 0);

  return (
    <div className="tabpanel stack-4">
      <div className="panel-head ret-head">
        <div className="ship-head__title">
          <span className="panel-title">{tr("Returns","Trả hàng")}</span>
          {n > 1 && <span className="ship-count">{n}</span>}
        </div>
        {n > 1
          ? <div className="ret-total">{tr("total refunded","tổng đã hoàn")} <b className="mono"><Money v={totalRefunded} /></b></div>
          : <div className="panel-sub">fact_order_returns</div>}
      </div>

      {n === 0
        ? <div className="ret-empty"><span className="ret-empty__dot" />{tr("No returns","Không có trả hàng")}</div>
        : <div className="ret-list">
            {rs.map((r,i) => <ReturnCard key={i} r={r} />)}
          </div>}

      {n > 0 &&
        <div className="note-line">
          <span className="caveat__mark">ⓘ</span>
          <span>{tr("Reference only — returns are not deducted from this order's P&L.","Chỉ tham chiếu — trả hàng không trừ vào P&L của đơn.")}</span>
        </div>}
    </div>
  );
}

function OrderChannelStaff({ o }){
  const c = o.channel, h = o.header;
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Channel & staff","Kênh & nhân sự")} sub="dim_channels · dim_staff · dim_promotions" />
      <div className="kpi-grid" style={{gridTemplateColumns:"1fr 1fr"}}>
        <div className="scard"><Eyebrow accent>{tr("Channel","Kênh")}</Eyebrow>
          <div className="facts" style={{marginTop:"var(--sp-3)"}}>
            <Fact k={tr("Name","Tên")} v={`${c.name} · ${c.code}`} />
            <Fact k={tr("Category","Phân loại")} v={`${c.category} · ${c.format}`} />
            <Fact k={tr("Platform","Nền tảng")} v={`${c.platform} · ${c.brand}`} />
            <Fact k={tr("Market","Thị trường")} v={c.market} />
            <Fact k={tr("Promo","Khuyến mãi")} v={c.promo_codes.length ? `${c.promo_codes.join(", ")} · max ${c.max_discount_rate}% · ${c.primary_nature}` : "—"} />
          </div>
        </div>
        <div className="scard"><Eyebrow accent>{tr("Staff","Nhân sự")}</Eyebrow>
          <div className="facts" style={{marginTop:"var(--sp-3)"}}>
            <Fact k={tr("Seller","Người bán")} v={h.seller} />
            <Fact k={tr("Creator","Người tạo")} v={h.creator} />
            <Fact k={tr("Team","Nhóm")} v={h.team} />
            <Fact k={tr("Branch","Chi nhánh")} v={h.branch} />
          </div>
        </div>
      </div>
    </div>
  );
}

function OrderTimeline({ o }){
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Timeline","Dòng thời gian")} sub="fact_orders · dim_date · dim_time" />
      <div className="timeline scard" style={{paddingLeft:"calc(var(--sp-5) + var(--sp-4))"}}>
        {o.timeline.map((e,i)=>(
          <div key={i} className={"tl-item tl-item--"+(e.kind==="good"?"good":e.kind==="bad"?"bad":e.kind==="normal"?"":"muted")}>
            <div className="tl-time">{e.time} <span className="caption" style={{marginLeft:6}}>ICT</span></div>
            <div className="tl-title">{e.title}</div>
            <div className="tl-meta">{e.meta}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Grouped tabs (4) — each stacks the existing section panels ── */
function OrderFinancialTab({ o }){
  /* Delegate to the redesigned Financial tab (financial.jsx) */
  return <OrderFinancialTabNew o={o} />;
}
function OrderItemsTab({ o }){
  return <OrderLineItems o={o} />;
}
function OrderOperationsTab({ o, onNavigate }){
  return (
    <div className="tab-sections">
      <OrderRecipient o={o} onNavigate={onNavigate} />
      <OrderFulfillment o={o} />
      <OrderShipments o={o} />
      <OrderPayments o={o} />
      <OrderReturns o={o} />
    </div>
  );
}
function OrderContextTab({ o }){
  return (
    <div className="tab-sections">
      <OrderChannelStaff o={o} />
      <OrderTimeline o={o} />
    </div>
  );
}

/* small shared bits used across panels */
function PanelHead({ title, sub }){
  return <div className="panel-head"><div className="panel-title">{title}</div><div className="panel-sub">{sub}</div></div>;
}
function Fact({ k, v, mono }){
  return <div className="fact"><div className="fact__k">{k}</div><div className={"fact__v"+(mono?" mono":"")}>{v}</div></div>;
}

Object.assign(window, {
  OrderFinancial, OrderFinancialNew, OrderLineItems, OrderCostLedger, OrderCostLedgerNew, OrderPayments,
  OrderShipments, OrderRecipient, OrderFulfillment, OrderReturns, OrderChannelStaff, OrderTimeline,
  OrderFinancialTab, OrderItemsTab, OrderOperationsTab, OrderContextTab,
  PanelHead, Fact, WfRow,
});

/* detailView — Order Detail shell (sidebar + tab bar) */

const ORDER_TABS = [
  { id:"financial",  en:"Financial",  vi:"Tài chính",  C: ()=>window.OrderFinancialTab },
  { id:"items",      en:"Items",      vi:"Dòng hàng",  C: ()=>window.OrderItemsTab },
  { id:"operations", en:"Operations", vi:"Vận hành",   C: ()=>window.OrderOperationsTab },
  { id:"context",    en:"Context",    vi:"Ngữ cảnh",   C: ()=>window.OrderContextTab },
];

function OrderDetail({ id, initialTab, onNavigate }){
  const o = window.DV_DATA.orders[id];
  const [tab, setTab] = useState(initialTab || "financial");
  const [loading, setLoading] = useState(false);
  useEffect(()=>{ setTab(initialTab || "financial"); window.scrollTo(0,0); }, [id]);

  if (!o) return <NotFound q={id} onNavigate={onNavigate} kind="order" />;

  function go(t){
    if (t === tab) return;
    setLoading(true); setTab(t);
    setTimeout(()=>setLoading(false), 220); // simulate HTMX lazy load
  }
  const Active = ORDER_TABS.find(t=>t.id===tab).C();

  return (
    <main className="detail-grid page-enter" key={id}>
      <section className="detail-main">
        <div className="tabbar" role="tablist" aria-label="order tabs">
          {ORDER_TABS.map(t=>(
            <button key={t.id} role="tab" aria-selected={tab===t.id} className="tab" onClick={()=>go(t.id)}>
              {tr(t.en,t.vi)}
            </button>
          ))}
        </div>
        <div id="tab-panel" aria-busy={loading}>
          {loading ? <TabSkeleton /> : <Active o={o} onNavigate={onNavigate} />}
        </div>
      </section>
      <OrderSidebar o={o} onNavigate={onNavigate} />
    </main>
  );
}

function OrderSidebar({ o, onNavigate }){
  const h = o.header, f = o.financial, fl = o.flags;
  const cust = window.DV_DATA.customers[h.customer_id];
  return (
    <aside className="detail-sidebar">
      {/* identity */}
      <div className="scard">
        <Eyebrow className="scard__eyebrow">{tr("Order at a glance","Đơn — tổng quan")}</Eyebrow>
        <div className="id-code">{h.order_code}</div>
        <div className="id-sub">order_id {h.order_id}</div>
        <div className="badge-row">
          <Badge tone={statusTone(h.status)} dot>{h.status}</Badge>
          <Badge tone={statusTone(h.payment_status)} dot>{h.payment_status}</Badge>
          <Badge tone={statusTone(h.fulfillment_status)} dot>{h.fulfillment_status}</Badge>
        </div>
      </div>

      {/* money headline */}
      <div className="scard">
        <Eyebrow className="scard__eyebrow" accent>{tr("Money headline","Tài chính chính")}</Eyebrow>
        <div className="money-line money-line--hero">
          <span className="money-line__label">
            {f.is_us ? tr("US revenue","Doanh thu US") : tr("Net revenue","Doanh thu thuần")}
            {f.is_us && <Badge tone="accent">US</Badge>}
          </span>
          <span className="money-line__val"><Money v={f.is_us ? f.us_revenue_incl_vat : f.net_revenue} /></span>
        </div>
        <div className="money-line">
          <span className="money-line__label">{tr("Gross profit","Lợi nhuận gộp")}{f.cogs_amount===null && <Badge tone="warn">unverified</Badge>}</span>
          <span className="money-line__val"><Money v={f.gross_profit} /><Pct v={f.gross_margin_pct} /></span>
        </div>
        <div className="money-line">
          <span className="money-line__label">{tr("Channel net","Ròng kênh")}</span>
          <span className="money-line__val"><Money v={f.channel_net_profit} /><Pct v={f.channel_net_margin_pct} /></span>
        </div>
      </div>

      {/* parties — recipient first (operational priority), then buyer account */}
      <PartiesSidebar o={o} cust={cust} onNavigate={onNavigate} />

      {/* quick facts */}
      <div className="scard">
        <Eyebrow className="scard__eyebrow">{tr("Quick facts","Thông tin nhanh")}</Eyebrow>
        <div className="facts">
          <Fact k={tr("Channel","Kênh")} v={h.channel_name} />
          <Fact k={tr("Seller","Người bán")} v={h.seller} />
          <Fact k={tr("Branch","Chi nhánh")} v={h.branch} />
          <Fact k={tr("Created","Ngày tạo")} v={h.created_at} mono />
          <Fact k={tr("Shipped","Đã gửi")} v={h.first_shipped_at} mono />
          <Fact k={tr("Carrier","Vận chuyển")} v={h.carrier} />
          {h.cod_amount>0 && <Fact k="COD" v={fmtVND(h.cod_amount)} mono />}
        </div>
      </div>

      {/* data-quality flags */}
      <div className="scard">
        <Eyebrow className="scard__eyebrow">{tr("Data-quality flags","Cờ chất lượng dữ liệu")}</Eyebrow>
        <div className="badge-row" style={{marginTop:0}}>
          <Badge tone={fl.is_us?"accent":"neutral"} dot={fl.is_us}>{fl.is_us?"is_us":"domestic"}</Badge>
          <Badge tone={fl.has_cogs?"good":"warn"} dot>{fl.has_cogs?"has_cogs":"no_cogs"}</Badge>
          <Badge tone={fl.has_platform_fees?"warn":"neutral"} dot={fl.has_platform_fees}>fees</Badge>
          <Badge tone={fl.has_returns?"bad":"neutral"} dot={fl.has_returns}>returns</Badge>
        </div>
      </div>
    </aside>
  );
}

/* ── Parties sidebar: an order has a buyer (account) and a recipient (who
   physically receives the goods). Usually the same; operations reads the
   recipient first, so it leads. ── */
function relationLabel(rel){
  if (rel === "GIFT") return tr("Gift order","Đơn quà tặng");
  if (rel === "CROSSBORDER") return tr("Crossborder","Đơn xuyên biên");
  if (rel === "DROPSHIP") return tr("Drop-ship","Giao hộ");
  return tr("Differs","Khác");
}
function shortLoc(r){
  return [r.district, r.province].filter(x=>x && x!=="—").join(", ");
}

function PartiesSidebar({ o, cust, onNavigate }){
  const p = o.parties;
  if (!p){ return null; }
  const r = p.recipient;
  const goCust = ()=> cust && onNavigate({page:"customer", id:cust.profile.customer_id});

  if (p.same){
    /* one person — fold the buyer account into the recipient card */
    return (
      <a className="scard scard--link scard--recipient" onClick={goCust}>
        <div className="party-head">
          <Eyebrow className="scard__eyebrow" accent>{tr("Recipient · buyer","Người nhận · người mua")}</Eyebrow>
          <Badge tone="neutral">{tr("same person","cùng một người")}</Badge>
        </div>
        <div className="mini-name">{r.name}</div>
        <div className="facts party-facts">
          <Fact k={tr("Phone","Điện thoại")} v={r.phone} mono />
          <Fact k={tr("Ship to","Giao tới")} v={shortLoc(r)} />
        </div>
        {cust &&
          <div className="mini-meta party-link-row">
            <span className="money-line__label">
              <Badge tone={valueGroupTone(cust.profile.value_group)} dot>{cust.profile.value_group}</Badge>
              <span style={{marginLeft:8}}>{tr("LTV","Vòng đời")} <span className="money-line__val" style={{fontSize:14, marginLeft:4}}>{fmtVND(cust.value.ltv)}</span></span>
            </span>
            <span className="mini-arrow mono">→</span>
          </div>}
      </a>
    );
  }

  /* two people — recipient leads (operations cares first), buyer below */
  return (
    <>
      <div className="scard scard--recipient">
        <div className="party-head">
          <Eyebrow className="scard__eyebrow" accent>{tr("Recipient","Người nhận")}</Eyebrow>
          <Badge tone="warn" dot>{tr("≠ buyer","≠ người mua")}</Badge>
        </div>
        <div className="mini-name">{r.name}</div>
        <div className="facts party-facts">
          <Fact k={tr("Phone","Điện thoại")} v={r.phone} mono />
          <Fact k={tr("Ship to","Giao tới")} v={shortLoc(r)} />
        </div>
        {p.relation &&
          <div className="badge-row"><Badge tone="accent">{relationLabel(p.relation)}</Badge></div>}
      </div>
      {cust &&
        <a className="scard scard--link" onClick={goCust}>
          <Eyebrow className="scard__eyebrow">{tr("Buyer · account","Người mua · tài khoản")}</Eyebrow>
          <div className="mini-name">{cust.profile.full_name}</div>
          <div className="badge-row">
            <Badge>{cust.profile.customer_type}</Badge>
            <Badge tone={valueGroupTone(cust.profile.value_group)} dot>{cust.profile.value_group}</Badge>
          </div>
          <div className="mini-meta">
            <span className="money-line__label">{tr("LTV","Giá trị vòng đời")} <span className="money-line__val" style={{fontSize:15, marginLeft:6}}>{fmtVND(cust.value.ltv)}</span></span>
            <span className="mini-arrow mono">→</span>
          </div>
        </a>}
    </>
  );
}

function TabSkeleton(){
  return <div className="skeleton" aria-hidden="true">
    {[0,1,2,3,4].map(i=><div className="sk-row" key={i} style={{height: i===0?22:14}} />)}
  </div>;
}

Object.assign(window, { OrderDetail, OrderSidebar, PartiesSidebar, relationLabel, shortLoc, TabSkeleton, ORDER_TABS });

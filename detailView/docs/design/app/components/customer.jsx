/* detailView — Customer Detail shell (sidebar + tabs) */

const CUSTOMER_TABS = [
  { id:"value",    en:"Value & Behavior", vi:"Giá trị & Hành vi", C: ()=>window.CustomerValueBehavior },
  { id:"timeline", en:"Status Timeline",vi:"Lịch sử TT",       C: ()=>window.CustomerStatusTimeline },
  { id:"orders",   en:"Order History",  vi:"Lịch sử đơn",      C: ()=>window.CustomerOrders },
];

function CustomerDetail({ id, onNavigate }){
  const c = window.DV_DATA.customers[id];
  const [tab, setTab] = useState("value");
  const [loading, setLoading] = useState(false);
  useEffect(()=>{ setTab("value"); window.scrollTo(0,0); }, [id]);

  if (!c) return <NotFound q={id} onNavigate={onNavigate} kind="customer" />;
  const isRetail = c.profile.customer_type === "RETAIL";

  function go(t){
    if (t === tab) return;
    setLoading(true); setTab(t);
    setTimeout(()=>setLoading(false), 220);
  }
  const Active = CUSTOMER_TABS.find(t=>t.id===tab).C();

  return (
    <main className="detail-grid page-enter" key={id}>
      <section className="detail-main">
        <div className="tabbar" role="tablist" aria-label="customer tabs">
          {CUSTOMER_TABS.map(t=>{
            const disabled = t.id==="timeline" && !isRetail;
            return (
              <button key={t.id} role="tab" aria-selected={tab===t.id} className="tab"
                disabled={disabled} title={disabled?tr("RETAIL only","Chỉ RETAIL"):undefined}
                onClick={()=>!disabled && go(t.id)}>
                {tr(t.en,t.vi)}
              </button>
            );
          })}
        </div>
        <div id="tab-panel" aria-busy={loading}>
          {loading ? <TabSkeleton /> : <Active c={c} onNavigate={onNavigate} />}
        </div>
      </section>
      <CustomerSidebar c={c} />
    </main>
  );
}

function CustomerSidebar({ c }){
  const p = c.profile, v = c.value;
  return (
    <aside className="detail-sidebar">
      {/* identity */}
      <div className="scard">
        <Eyebrow className="scard__eyebrow">{tr("Customer profile","Hồ sơ khách hàng")}</Eyebrow>
        <div className="id-code id-code--name">{p.full_name}</div>
        <div className="id-sub">{p.customer_id}</div>
        <div className="badge-row">
          <Badge>{p.customer_type}</Badge>
          <Badge tone={valueGroupTone(p.value_group)} dot>{p.value_group}</Badge>
          <Badge tone={statusTone(p.lifecycle_stage)} dot>{p.lifecycle_stage}</Badge>
        </div>
      </div>

      {/* headline KPIs */}
      <div className="scard">
        <Eyebrow className="scard__eyebrow" accent>{tr("Headline","Chỉ số chính")}</Eyebrow>
        <div className="money-line money-line--hero">
          <span className="money-line__label">{tr("Lifetime value","Giá trị vòng đời")}</span>
          <span className="money-line__val">{fmtVND(v.ltv)}</span>
        </div>
        <div className="money-line">
          <span className="money-line__label">{tr("Orders","Đơn")} · AOV</span>
          <span className="money-line__val">{v.total_orders} · {fmtVND(v.aov)}</span>
        </div>
        <div className="money-line">
          <span className="money-line__label">{tr("Recency","Gần đây")}</span>
          <span className="money-line__val">{p.recency_days}d <span className="pct">{relTime(p.recency_days)}</span></span>
        </div>
      </div>

      {/* contact & geo */}
      <div className="scard">
        <Eyebrow className="scard__eyebrow">{tr("Contact & geo","Liên hệ & khu vực")}</Eyebrow>
        <div className="facts">
          <Fact k={tr("Phone","SĐT")} v={p.phone} mono />
          <Fact k="Email" v={p.email} />
          <Fact k={tr("Address","Địa chỉ")} v={`${p.address1}, ${p.ward}, ${p.district}, ${p.province}`} />
          <Fact k={tr("Region","Khu vực")} v={p.geo_region} />
          <Fact k={tr("Loyalty","Điểm")} v={p.loyalty_point.toLocaleString("vi-VN")} mono />
          <Fact k={tr("DOB / Sex","NS / GT")} v={`${p.dob} · ${p.sex}`} />
        </div>
      </div>

      {/* dates */}
      <div className="scard">
        <Eyebrow className="scard__eyebrow">{tr("Dates","Mốc thời gian")}</Eyebrow>
        <div className="facts">
          <Fact k={tr("First","Đầu")} v={p.first_order_date} mono />
          <Fact k={tr("Last","Cuối")} v={p.last_order_date} mono />
          <Fact k={tr("Tenure","Thâm niên")} v={`${p.lifespan_days}d (${(p.lifespan_days/365).toFixed(1)}y)`} mono />
          <Fact k={tr("Created","Tạo tài khoản")} v={p.created_at} mono />
        </div>
      </div>

      <div className="note-line">
        <span className="caveat__mark">ⓘ</span>
        <span>{tr("acquisition_source unknown · profile syncs nightly (not real-time).","Nguồn gia nhập không rõ · hồ sơ đồng bộ hàng đêm (không thời gian thực).")}</span>
      </div>
    </aside>
  );
}

Object.assign(window, { CustomerDetail, CustomerSidebar, CUSTOMER_TABS });

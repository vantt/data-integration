/* detailView — Customer tab panels */

function CustomerValue({ c, onNavigate }){
  const v = c.value;
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Value metrics","Chỉ số giá trị")} sub="dim_customers · fact_orders · fact_order_economics" />
      <div className="kpi-grid">
        <Kpi hero label={tr("Lifetime value","Giá trị vòng đời")} value={fmtVND(v.ltv)}
          sub={<span className="row-flex"><Sparkline data={v.spend_trend} /> {tr("12-mo spend trend","xu hướng chi 12 tháng")}</span>} />
        <Kpi label={tr("Total orders","Tổng đơn")} value={v.total_orders} />
        <Kpi label={tr("Avg order value","Giá trị TB/đơn")} value={fmtVND(v.aov)} />
      </div>
      <div className="kpi-grid">
        <Kpi label={tr("Gross profit contributed","LN gộp đóng góp")} value={fmtVND(v.total_gross_profit)} />
        <Kpi label={tr("Total COGS","Tổng giá vốn")} value={fmtVND(v.total_cogs)} />
        <Kpi label={tr("Avg gross margin","Biên gộp TB")} value={v.avg_margin_pct.toFixed(1)+"%"}
          sub={<Badge tone="warn">~{v.cogs_coverage_pct}% {tr("COGS coverage","phủ giá vốn")}</Badge>} />
        <Kpi label={tr("Returns","Trả hàng")} value={fmtVND(v.returns_amount)} sub={`${v.returns_count} ${tr("events","sự kiện")}`} />
      </div>
      <Caveat tone="warn">{tr("Average margin reflects only orders with a matched COGS","Biên TB chỉ tính trên đơn có khớp giá vốn")} (~{v.cogs_coverage_pct}%). {tr("Treat as directional.","Xem như định hướng.")}</Caveat>
    </div>
  );
}

function CustomerBehavior({ c }){
  const b = c.behavior;
  const segs = [
    ["LIFECYCLE", b.lifecycle_stage], ["CHANNEL", b.channel_preference],
    ["PRODUCT", b.product_affinity], ["PAYMENT", b.payment_behavior],
    ["GEO", b.geo_region], ["TYPE", b.customer_type],
  ];
  return (
    <div className="tabpanel stack-5">
      <PanelHead title={tr("Behaviour · RFM & segmentation","Hành vi · RFM & phân khúc")} sub="dim_customers" />
      <div className="rfm">
        <div className="rfm__cell"><div className="rfm__glyph">R</div><div className="rfm__name">{tr("Recency","Gần đây")}</div><div className="rfm__val">{b.recency_days}d</div></div>
        <div className="rfm__cell"><div className="rfm__glyph">F</div><div className="rfm__name">{tr("Frequency","Tần suất")}</div><div className="rfm__val">{b.frequency}</div></div>
        <div className="rfm__cell"><div className="rfm__glyph">M</div><div className="rfm__name">{tr("Monetary","Giá trị")}</div><div className="rfm__val">{fmtVND(b.monetary)}</div></div>
      </div>
      <div>
        <Eyebrow style={{marginBottom:"var(--sp-3)"}}>{tr("Segmentation","Phân khúc")}</Eyebrow>
        <div className="badge-row" style={{marginTop:"var(--sp-3)"}}>
          {segs.map(([k,val],i)=>(
            <Badge key={i} tone={k==="LIFECYCLE"?statusTone(val):k==="TYPE"?"neutral":"neutral"}>
              <span style={{opacity:.6}}>{k}</span> {val}
            </Badge>
          ))}
        </div>
      </div>
      <div className="row-flex" style={{gap:"var(--sp-4)"}}>
        <Badge tone="accent">{tr("Cohort","Nhóm gia nhập")} {b.cohort_month}</Badge>
        <span className="note-line" style={{margin:0}}>{tr("Cohort = month of first order.","Nhóm = tháng đơn đầu tiên.")}</span>
      </div>
    </div>
  );
}

function CustomerStatusTimeline({ c }){
  if (c.profile.customer_type !== "RETAIL" || !c.status_timeline){
    return (
      <div className="tabpanel">
        <PanelHead title={tr("Status timeline","Lịch sử trạng thái")} sub="mart_customer_status_snapshot_monthly" />
        <Caveat tone="warn" rule>
          <b>{tr("RETAIL only.","Chỉ dành cho RETAIL.")}</b> {tr("Monthly status snapshots are computed for retail customers only — this account is","Ảnh chụp trạng thái hàng tháng chỉ tính cho khách lẻ — tài khoản này là")} <span className="mono">{c.profile.customer_type}</span>.
        </Caveat>
      </div>
    );
  }
  const strip = c.status_timeline;
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Status timeline","Lịch sử trạng thái")} sub="mart_customer_status_snapshot_monthly · 24 mo" />
      <div className="scard">
        <div className="strip">
          {strip.map((m,i)=>(
            <div key={i} className="strip-cell" data-st={m.status}
              data-tip={`${m.month} · ${m.status}${m.days_since!==null?" · "+m.days_since+"d since order":""} · ${m.value_group}`}>
              {m.status==="ACTIVE"?"A":m.status==="AT_RISK"?"R":m.status==="CHURNED"?"C":"·"}
              {m.is_new && <span className="strip-cell__new" />}
            </div>
          ))}
        </div>
        <div className="strip-axis"><span>{strip[0].month}</span><span>{strip[strip.length-1].month}</span></div>
        <div className="strip-legend">
          <span><i style={{background:"var(--moss-500)"}} />ACTIVE</span>
          <span><i style={{background:"var(--amber-500)"}} />AT_RISK</span>
          <span><i style={{background:"var(--coral-500)"}} />CHURNED</span>
          <span><i style={{background:"var(--accent)", borderRadius:"50%"}} />{tr("acquisition","gia nhập")}</span>
        </div>
      </div>
      <Caveat tone="info">{tr("Hover a month for days-since-last-order and value group. value_group trend is approximate.","Di chuột lên tháng để xem số ngày từ đơn cuối và nhóm giá trị. Xu hướng nhóm giá trị là gần đúng.")}</Caveat>
    </div>
  );
}

function CustomerOrders({ c, onNavigate }){
  return (
    <div className="tabpanel stack-4">
      <PanelHead title={tr("Order history","Lịch sử đơn")} sub="fact_orders × economics × dims" />
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr>
            <th>{tr("Code · Date","Mã · Ngày")}</th><th>{tr("Status","TT")}</th>
            <th>{tr("Channel","Kênh")}</th><th>{tr("Seller","NB")}</th>
            <th className="num-h">{tr("Total · Pay","Tổng thu · TT")}</th><th className="num-h">{tr("GP","LN gộp")}</th>
            <th className="num-h">{tr("Margin","Biên")}</th><th>{tr("Ret","Trả")}</th>
          </tr></thead>
          <tbody>
            {c.order_history.map((r,i)=>{
              const known = window.DV_DATA.orders[r.code];
              return (
                <tr key={i} className={known?"is-clickable":""} onClick={()=> known && onNavigate({page:"order", id:r.code})}
                  title={known?tr("Open order","Mở đơn"):tr("Detail not in this demo","Chi tiết không có trong demo")}>
                  <td className="num cell-strong" style={{textAlign:"left"}}>{r.code}{r.us && <Badge tone="accent" style={{marginLeft:6}}>US</Badge>}<span className="cell-sub mono">{r.date}</span></td>
                  <td><Badge tone={statusTone(r.status)}>{r.status}</Badge></td>
                  <td className="muted">{r.channel}</td>
                  <td className="muted">{r.seller}</td>
                  <td className="num cell-strong"><Money v={r.total} /><span className="cell-sub mono" style={{textAlign:"right"}}>{r.pay}</span></td>
                  <td className="num">{r.gp===null?<span className="dash">—</span>:<Money v={r.gp} />}</td>
                  <td className="num">{r.margin===null?<Badge tone="warn">n/a</Badge>:<span className="pct" style={{color: r.margin>=28?"var(--moss-500)":r.margin<24?"var(--coral-500)":"inherit"}}>{r.margin.toFixed(0)}%</span>}</td>
                  <td>{r.ret ? <Badge tone="bad">↩</Badge> : <span className="dash">—</span>}</td>
                </tr>
              );
            })}
          </tbody>
          <tfoot><tr><td colSpan={8} className="muted">{c.order_history.length} {tr("of","trên")} {c.value.total_orders} {tr("orders · newest first","đơn · mới nhất trước")}</td></tr></tfoot>
        </table>
      </div>
    </div>
  );
}

function CustomerValueBehavior({ c, onNavigate }){
  return (
    <>
      <CustomerBehavior c={c} />
      <div style={{height:"var(--sp-6)", borderTop:"1px solid var(--border)", marginTop:"var(--sp-2)"}} />
      <CustomerValue c={c} onNavigate={onNavigate} />
    </>
  );
}

Object.assign(window, { CustomerValue, CustomerBehavior, CustomerValueBehavior, CustomerStatusTimeline, CustomerOrders });

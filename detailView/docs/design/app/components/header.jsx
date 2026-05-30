/* detailView — header, search cluster, home */

/* resolve a query against the mock dataset */
function resolveSearch(mode, raw){
  const q = (raw||"").trim();
  if (!q) return { type: "none", q };
  const D = window.DV_DATA;
  if (mode === "order"){
    const key = Object.keys(D.orders).find(k => k.toLowerCase() === q.toLowerCase());
    return key ? { type: "order", id: key, q } : { type: "none", q };
  }
  // customer: id exact / phone / email / name substring
  const exact = D.customers[q.toUpperCase()];
  if (exact) return { type: "customer", id: exact.profile.customer_id, q };
  const byPhone = D.phoneIndex[D.norm(q)] || D.phoneIndex[q.toLowerCase()];
  if (byPhone && (D.norm(q).length >= 5 || q.includes("@"))) return { type: "customer", id: byPhone, q };
  const ql = q.toLowerCase();
  const hits = Object.values(D.customers).filter(c => {
    const p = c.profile;
    return p.full_name.toLowerCase().includes(ql) || p.customer_id.toLowerCase().includes(ql)
      || D.norm(p.phone).includes(D.norm(q)) || p.email.toLowerCase().includes(ql);
  });
  if (hits.length === 1) return { type: "customer", id: hits[0].profile.customer_id, q };
  if (hits.length > 1) return { type: "multi", hits, q };
  return { type: "none", q };
}

function SearchCluster({ big, onNavigate }){
  const [mode, setMode] = useState("order");
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null); // {type, ...}
  const wrapRef = useRef(null);

  useEffect(()=>{
    function onDoc(e){ if (wrapRef.current && !wrapRef.current.contains(e.target)) setResults(null); }
    document.addEventListener("mousedown", onDoc);
    return ()=>document.removeEventListener("mousedown", onDoc);
  },[]);

  function submit(e){
    e && e.preventDefault();
    const r = resolveSearch(mode, q);
    if (r.type === "order") { setResults(null); onNavigate({ page:"order", id:r.id }); }
    else if (r.type === "customer") { setResults(null); onNavigate({ page:"customer", id:r.id }); }
    else setResults(r); // multi or none
  }

  const ph = mode === "order"
    ? tr("Order code  e.g. HD00123", "Mã đơn  vd. HD00123")
    : tr("Customer ID, phone or email", "Mã KH, SĐT hoặc email");

  return (
    <form ref={wrapRef} className={"search"+(big?" search--big":"")} onSubmit={submit} role="search">
      <div className="seg" role="tablist" aria-label="search mode">
        <button type="button" role="tab" aria-selected={mode==="order"} className="seg__btn"
          onClick={()=>{setMode("order"); setResults(null);}}>{tr("Order","Đơn")}</button>
        <button type="button" role="tab" aria-selected={mode==="customer"} className="seg__btn"
          onClick={()=>{setMode("customer"); setResults(null);}}>{tr("Customer","Khách")}</button>
      </div>
      <div className="search__field">
        <input className="search__input" value={q} placeholder={ph} aria-label={ph}
          onChange={e=>setQ(e.target.value)} autoComplete="off" spellCheck="false" />
        <button type="submit" className="search__submit" aria-label="Search">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
            <circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/>
          </svg>
        </button>
      </div>
      {results && <SearchResults r={results} onNavigate={(n)=>{setResults(null); onNavigate(n);}} />}
    </form>
  );
}

function SearchResults({ r, onNavigate }){
  if (r.type === "multi"){
    return (
      <div className="search__results" id="search-results" role="listbox">
        {r.hits.map(c=>(
          <div key={c.profile.customer_id} className="result-row" role="option"
            onClick={()=>onNavigate({ page:"customer", id:c.profile.customer_id })}>
            <div>
              <span className="result-row__name">{c.profile.full_name}</span>
              <div className="result-row__meta">{c.profile.customer_id} · {c.profile.phone}</div>
            </div>
            <Badge tone={valueGroupTone(c.profile.value_group)}>{c.profile.value_group}</Badge>
          </div>
        ))}
      </div>
    );
  }
  return (
    <div className="search__results" id="search-results">
      <div className="result-empty">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
          <circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/></svg>
        {tr("No match for","Không có kết quả cho")} <span className="mono" style={{color:"var(--fg-1)"}}>“{r.q}”</span>
      </div>
    </div>
  );
}

function Header({ onNavigate, crumb, onToggleTweaks }){
  const ref = useRef(null);
  useEffect(()=>{
    function onScroll(){ if (ref.current) ref.current.setAttribute("data-scrolled", window.scrollY > 4); }
    window.addEventListener("scroll", onScroll); onScroll();
    return ()=>window.removeEventListener("scroll", onScroll);
  },[]);
  return (
    <header className="app-header" ref={ref}>
      <div className="brand" onClick={()=>onNavigate({ page:"home" })}>
        <span className="brand__dot" />
        <span className="brand__name">detail<b>View</b></span>
      </div>
      <SearchCluster onNavigate={onNavigate} />
      <div className="context-slot">
        {crumb && <span className="context-crumb">{crumb.label} <b>{crumb.value}</b></span>}
        <button className="icon-btn" aria-label="Settings" title="Tweaks" onClick={onToggleTweaks}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.3">
            <circle cx="8" cy="8" r="2.3"/><circle cx="8" cy="8" r="6"/>
            <path d="M8 .8v1.6M8 13.6v1.6M.8 8h1.6M13.6 8h1.6" strokeLinecap="round"/>
          </svg>
        </button>
      </div>
    </header>
  );
}

function Home({ onNavigate }){
  return (
    <div className="home page-enter">
      <div className="home__inner">
        <Eyebrow className="home__eyebrow" accent>{tr("Order & Customer insight","Thông tin đơn hàng & khách hàng")}</Eyebrow>
        <h1 className="home__title">{tr("The whole story of","Toàn bộ câu chuyện của")} <em>{tr("one entity","một thực thể")}</em>.</h1>
        <p className="home__sub">{tr("Look up an order or a customer to see every computed insight — financials, fulfillment, behaviour, segmentation — in a single view.","Tra cứu một đơn hàng hoặc khách hàng để xem mọi chỉ số đã tính sẵn — tài chính, vận hành, hành vi, phân khúc — trong một màn hình.")}</p>
        <div className="home__search"><SearchCluster big onNavigate={onNavigate} /></div>
        <div className="home__hints">
          <span className="home__hint" onClick={()=>onNavigate({page:"order", id:"HD00123"})}>{tr("Try order","Thử đơn")} <b>HD00123</b></span>
          <span className="home__hint" onClick={()=>onNavigate({page:"order", id:"HD00210"})}>{tr("US order","Đơn US")} <b>HD00210</b></span>
          <span className="home__hint" onClick={()=>onNavigate({page:"customer", id:"CUS-7781"})}>{tr("Customer","Khách")} <b>CUS-7781</b></span>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SearchCluster, Header, Home, resolveSearch });

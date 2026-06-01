/* detailView — app router, shared states, tweaks */

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "lang": "en",
  "theme": "dark",
  "density": "comfortable",
  "numfont": "mono",
  "accent": "amber",
  "verdictStyle": "bar",
  "verdictThin": 10,
  "verdictDemo": "auto"
}/*EDITMODE-END*/;

function NotFound({ q, onNavigate, kind }){
  return (
    <div className="state page-enter"><div className="state__inner">
      <svg width="34" height="34" viewBox="0 0 16 16" fill="none" stroke="var(--fg-tertiary)" strokeWidth="1.2" strokeLinecap="round" style={{marginBottom:"var(--sp-4)"}}>
        <circle cx="7" cy="7" r="4.5"/><path d="M10.5 10.5 14 14"/></svg>
      <div className="state__title voice"><em>{tr("No match","Không tìm thấy")}</em></div>
      <p className="state__sub">{tr("Nothing resolves for","Không có kết quả cho")} <span className="mono" style={{color:"var(--fg-1)"}}>“{q}”</span>. {tr("Check the code and try again.","Kiểm tra lại mã và thử lại.")}</p>
      <div className="state__actions">
        <button className="btn btn--secondary" onClick={()=>onNavigate({page:"home"})}>{tr("Back home","Về trang chủ")}</button>
      </div>
    </div></div>
  );
}

function ServerBusy({ onRetry }){
  return (
    <div className="state page-enter"><div className="state__inner">
      <div className="status status--warn" style={{justifyContent:"center", marginBottom:"var(--sp-4)"}}>
        <span className="mono" style={{fontSize:11}}>503 · DB BUSY</span></div>
      <div className="state__title voice"><em>{tr("Data refreshing","Dữ liệu đang làm mới")}</em></div>
      <p className="state__sub">{tr("The serving database is briefly locked for a view bootstrap. Retry in a moment.","Cơ sở dữ liệu phục vụ đang khóa tạm thời để khởi tạo view. Thử lại sau giây lát.")}</p>
      <div className="state__actions">
        <button className="btn btn--primary" onClick={onRetry}>{tr("Retry","Thử lại")}</button>
      </div>
    </div></div>
  );
}

function crumbFor(route){
  if (route.page === "order"){
    const o = window.DV_DATA.orders[route.id];
    return { label: tr("Order","Đơn"), value: o ? o.header.order_code : route.id };
  }
  if (route.page === "customer"){
    const c = window.DV_DATA.customers[route.id];
    return { label: tr("Customer","Khách"), value: c ? c.profile.full_name : route.id };
  }
  return null;
}

function parseHash(){
  const h = (location.hash || "").replace(/^#\/?/, "");
  const seg = h.split("/").filter(Boolean);
  if (seg[0] === "order" && seg[1]) return { page:"order", id:seg[1], tab: seg[2] || undefined };
  if (seg[0] === "customer" && seg[1]) return { page:"customer", id:seg[1], tab: seg[2] || undefined };
  return { page:"home" };
}

function App(){
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [route, setRoute] = useState(parseHash);
  const [busy, setBusy] = useState(false);

  // apply tweaks to <html> synchronously so tr() + CSS read fresh values this render
  const el = document.documentElement;
  el.setAttribute("data-lang", t.lang);
  el.setAttribute("data-theme", t.theme);
  el.setAttribute("data-density", t.density);
  el.setAttribute("data-numfont", t.numfont);
  el.setAttribute("data-accent", t.accent);
  el.setAttribute("data-verdict-style", t.verdictStyle);
  el.setAttribute("data-verdict-thin", t.verdictThin);
  el.setAttribute("data-verdict-demo", t.verdictDemo);

  useEffect(()=>{
    const onHash = ()=>{ setBusy(false); setRoute(parseHash()); };
    window.addEventListener("hashchange", onHash);
    return ()=>window.removeEventListener("hashchange", onHash);
  }, []);

  function navigate(r){ setBusy(false); setRoute(r); }

  let content;
  if (busy) content = <ServerBusy onRetry={()=>setBusy(false)} />;
  else if (route.page === "order") content = <OrderDetail id={route.id} initialTab={route.tab} onNavigate={navigate} />;
  else if (route.page === "customer") content = <CustomerDetail id={route.id} onNavigate={navigate} />;
  else content = <Home onNavigate={navigate} />;

  return (
    <div className="app">
      <Header onNavigate={navigate} crumb={route.page!=="home"?crumbFor(route):null}
        onToggleTweaks={()=>window.postMessage({type:"__activate_edit_mode"},"*")} />
      {content}

      <TweaksPanel title="Tweaks">
        <TweakSection label="Language" />
        <TweakRadio label="UI labels" value={t.lang}
          options={[{value:"en",label:"EN"},{value:"vi",label:"Tiếng Việt"}]}
          onChange={v=>setTweak("lang",v)} />
        <TweakSection label="Appearance" />
        <TweakRadio label="Theme" value={t.theme} options={["dark","light"]} onChange={v=>setTweak("theme",v)} />
        <TweakRadio label="Density" value={t.density} options={[{value:"comfortable",label:"comfy"},{value:"compact",label:"compact"}]} onChange={v=>setTweak("density",v)} />
        <TweakSection label="Numbers" />
        <TweakRadio label="Figure font" value={t.numfont} options={[{value:"mono",label:"Mono"},{value:"sans",label:"Sans"}]} onChange={v=>setTweak("numfont",v)} />
        <TweakSection label="Accent" />
        <TweakColor label="Accent" value={accentHex(t.accent)}
          options={[ "#e8a341", "#84b577", "#d4a548" ]}
          onChange={hex=>setTweak("accent", hexAccent(hex))} />
        <TweakSection label="Profit / loss verdict" />
        <TweakRadio label="Treatment" value={t.verdictStyle}
          options={[{value:"bar",label:"Bar"},{value:"rule",label:"Rule"},{value:"gauge",label:"Gauge"}]}
          onChange={v=>setTweak("verdictStyle",v)} />
        <TweakSlider label="Thin-margin below" value={t.verdictThin} min={0} max={30} step={1} unit="%"
          onChange={v=>setTweak("verdictThin",v)} />
        <TweakSelect label="Preview state" value={t.verdictDemo}
          options={[{value:"auto",label:"Auto (from data)"},{value:"profit",label:"Lãi"},{value:"thin",label:"Lãi mỏng"},{value:"loss",label:"Lỗ"},{value:"indeterminate",label:"Chưa xác định"}]}
          onChange={v=>setTweak("verdictDemo",v)} />
        <TweakSection label="Demo states" />
        <TweakButton label={tr("Preview 503 DB-busy","Xem trạng thái 503")} secondary onClick={()=>setBusy(true)} />
      </TweaksPanel>
    </div>
  );
}

function accentHex(a){ return a==="moss"?"#84b577":a==="honey"?"#d4a548":"#e8a341"; }
function hexAccent(h){ h=(h||"").toLowerCase(); return h==="#84b577"?"moss":h==="#d4a548"?"honey":"amber"; }

ReactDOM.createRoot(document.getElementById("root")).render(<App />);

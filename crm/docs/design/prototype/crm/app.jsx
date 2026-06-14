/* ============================================================
   App shell: header · C01 nav · C02 search · router · modals ·
   O02 quick preview · toasts · Tweaks panel.
   ============================================================ */
const { useState: aUseState, useEffect: aUseEffect, useRef: aUseRef } = React;

/* ── Tweaks config ──────────────────────────────────────── */
const THEMES = [
  { id: "dark", label: "Dark", attr: "" },
  { id: "light", label: "Sáng ấm", attr: "light" },
  { id: "finance", label: "Tài chính", attr: "finance" },
];
const ACCENTS = [
  { id: "amber", label: "Hổ phách", attr: "", sw: "#e8a341" },
  { id: "moss", label: "Rêu", attr: "moss", sw: "#84b577" },
  { id: "honey", label: "Mật ong", attr: "honey", sw: "#d4a548" },
];
const FONTS = [
  { id: "editorial", label: "Editorial", display: "'Newsreader', Georgia, serif", body: "'Geist', system-ui, sans-serif", mono: "'Geist Mono', monospace" },
  { id: "precision", label: "Precision", display: "'Fraunces', Georgia, serif", body: "'Geist', system-ui, sans-serif", mono: "'Geist Mono', monospace" },
  { id: "grotesk", label: "Grotesk", display: "'Space Grotesk', sans-serif", body: "'Geist', system-ui, sans-serif", mono: "'Geist Mono', monospace" },
  { id: "plex", label: "Plex", display: "'IBM Plex Serif', serif", body: "'IBM Plex Sans', sans-serif", mono: "'IBM Plex Mono', monospace" },
];
const DEFAULT_TWEAKS = { theme: "dark", accent: "amber", font: "editorial", density: "comfortable", numfont: "mono" };

function loadTweaks() {
  try { return { ...DEFAULT_TWEAKS, ...JSON.parse(localStorage.getItem("crm_tweaks") || "{}") }; } catch (e) { return { ...DEFAULT_TWEAKS }; }
}
function applyTweaks(tw) {
  const root = document.documentElement;
  const theme = THEMES.find((t) => t.id === tw.theme) || THEMES[0];
  const accent = ACCENTS.find((a) => a.id === tw.accent) || ACCENTS[0];
  const font = FONTS.find((f) => f.id === tw.font) || FONTS[0];
  theme.attr ? root.setAttribute("data-theme", theme.attr) : root.removeAttribute("data-theme");
  // finance theme owns indigo accent; only override when user picks moss/honey
  if (accent.attr) root.setAttribute("data-accent", accent.attr); else root.removeAttribute("data-accent");
  root.setAttribute("data-density", tw.density === "compact" ? "compact" : "default");
  root.setAttribute("data-numfont", tw.numfont === "sans" ? "sans" : "mono");
  root.style.setProperty("--font-display", font.display);
  root.style.setProperty("--font-body", font.body);
  root.style.setProperty("--font-mono", font.mono);
}

/* ── C02 Global Search ──────────────────────────────────── */
function GlobalSearch({ nav }) {
  const [q, setQ] = aUseState("");
  const [open, setOpen] = aUseState(false);
  const ref = aUseRef(null);
  aUseEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h);
  }, []);
  const results = q.trim() ? window.DB.parties.filter((p) => p.name.toLowerCase().includes(q.toLowerCase()) || p.phone.includes(q) || (p.email || "").includes(q.toLowerCase()) || p.code.toLowerCase().includes(q.toLowerCase())).slice(0, 6) : [];
  return (
    <div className="search" ref={ref}>
      <div className="search__field">
        <input className="search__input" value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
          placeholder="Tìm khách: SĐT, tên, email, code…" />
        <button className="search__submit" onClick={() => results[0] && nav({ screen: "S03", party: results[0].id })}><Icon name="search" size={15} /></button>
      </div>
      {open && q.trim() && (
        <div className="search__results">
          {results.length === 0 ? (
            <div className="result-empty"><Icon name="search" size={14} /> Không tìm thấy "<b>{q}</b>"</div>
          ) : results.map((p) => (
            <div key={p.id} className="result-row" onClick={() => { setOpen(false); setQ(""); nav({ screen: "S03", party: p.id }); }}>
              <div><div className="result-row__name">{p.name}</div><div className="result-row__meta">{p.code} · {p.group}</div></div>
              <div className="result-row__meta">{p.phone}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── C01 Sidebar Nav ────────────────────────────────────── */
const NAV = [
  { group: "Hằng ngày", items: [
    { id: "S01", icon: "worklist", label: "Worklist" },
    { id: "S02", icon: "customers", label: "Khách hàng" },
    { id: "S05", icon: "inbox", label: "Inbox", badge: "inbox" },
    { id: "S07", icon: "tasks", label: "Tasks" },
  ]},
  { group: "Tăng trưởng", items: [
    { id: "S08", icon: "segments", label: "Segments" },
    { id: "S10", icon: "campaigns", label: "Chiến dịch" },
    { id: "S12", icon: "ads", label: "Ads" },
  ]},
  { group: "Quản trị", items: [
    { id: "S04", icon: "dedup", label: "Dedup", badge: "dedup" },
    { id: "S13", icon: "settings", label: "Cài đặt" },
  ]},
];
const SCREEN_OF_TAB = { S03: "S02", S06: "S05", S09: "S08", S11: "S10" };
function Sidebar({ route, nav }) {
  const inbox = window.DB.conversations.filter((c) => c.unread > 0).reduce((s, c) => s + c.unread, 0);
  const dedup = window.DB.dedup.filter((d) => d.status === "pending").length;
  const cur = SCREEN_OF_TAB[route.screen] || route.screen;
  return (
    <nav className="crm-nav" aria-label="Điều hướng">
      {NAV.map((g) => (
        <div key={g.group} className="crm-nav__group">
          <div className="caption crm-nav__eyebrow">{g.group}</div>
          {g.items.map((it) => {
            const sel = cur === it.id;
            const badge = it.badge === "inbox" ? inbox : it.badge === "dedup" ? dedup : null;
            return (
              <button key={it.id} className="crm-nav__item" aria-current={sel ? "page" : undefined} onClick={() => nav({ screen: it.id })}>
                <span className="crm-nav__icon"><Icon name={it.icon} size={17} /></span>
                <span className="crm-nav__label">{it.label}</span>
                {badge ? <span className={"crm-nav__badge" + (it.badge === "inbox" ? " crm-nav__badge--warn" : "")}>{badge}</span> : null}
              </button>
            );
          })}
        </div>
      ))}
      <div className="crm-nav__foot">
        <div className="flex-wrap" style={{ gap: 8 }}>
          <Avatar user={window.DB.ME} size={26} />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 12.5, color: "var(--fg-1)" }}>{window.DB.userById(window.DB.ME).short}</div>
            <div className="crm-nav__sync">sales · ICT</div>
          </div>
        </div>
        <div className="crm-nav__statusline" style={{ marginTop: 8 }}><span className="status status--ready"><span className="mono" style={{ fontSize: 10, letterSpacing: "0.04em" }}>SERVING · SYNCED</span></span></div>
        <div className="crm-nav__sync">Lô đêm · 03:10 ICT</div>
      </div>
    </nav>
  );
}

/* ── O02 Quick Preview ──────────────────────────────────── */
function QuickPreview({ partyId, rect, close, nav }) {
  const p = window.DB.partyById(partyId);
  if (!p) return null;
  const top = Math.min(rect.bottom + 8, window.innerHeight - 280);
  const left = Math.min(rect.left, window.innerWidth - 340);
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 180 }} onMouseDown={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="qp-pop" style={{ position: "fixed", top, left }}>
        <div className="qp-head">
          <div><div className="name" style={{ fontSize: 16 }}>{p.name}</div><div className="mono" style={{ fontSize: 11, color: "var(--fg-muted)", marginTop: 4 }}>{p.phone} · {p.group} · {p.status}</div></div>
          <button className="icon-btn icon-btn--sm" onClick={close}><Icon name="close" size={13} /></button>
        </div>
        <div className="qp-body">
          <div className="fact"><span className="fact__k">Mua gần</span><span className="fact__v mono">{fmtDateOnly(p.last_order)}</span></div>
          <div className="fact"><span className="fact__k">Affinity</span><span className="fact__v">{p.insight.affinity}</span></div>
          <div className="fact"><span className="fact__k">Action</span><span className="fact__v">{p.actions.length ? p.actions.map((a) => window.ACTION_META[a.type].label).join(", ") : "—"}</span></div>
        </div>
        <div className="qp-foot"><button className="btn btn--primary" style={{ width: "100%", padding: "9px 14px" }} onClick={() => { close(); nav({ screen: "S03", party: p.id }); }}>Mở hồ sơ đầy đủ <Icon name="chevron" size={13} /></button></div>
      </div>
    </div>
  );
}

/* ── Tweaks panel ───────────────────────────────────────── */
function TweaksPanel({ tweaks, setTweaks }) {
  const [open, setOpen] = aUseState(false);
  const set = (k, v) => setTweaks((t) => ({ ...t, [k]: v }));
  return (
    <>
      <button className="tweaks-fab" onClick={() => setOpen(!open)} aria-label="Tweaks">{open ? <Icon name="close" size={18} /> : <Icon name="settings" size={18} />}</button>
      {open && (
        <div className="tweaks-panel">
          <div className="tweaks-panel__head"><span className="tweaks-panel__title">Tweaks</span><button className="icon-btn icon-btn--sm" onClick={() => setOpen(false)}><Icon name="close" size={13} /></button></div>
          <div className="tweaks-sec">
            <div className="tweaks-sec__label">Bảng màu</div>
            <div className="tweaks-opts">{THEMES.map((t) => <button key={t.id} className={"twk" + (tweaks.theme === t.id ? " twk--on" : "")} onClick={() => set("theme", t.id)}>{t.label}</button>)}</div>
          </div>
          <div className="tweaks-sec">
            <div className="tweaks-sec__label">Màu nhấn</div>
            <div className="tweaks-opts">{ACCENTS.map((a) => <button key={a.id} className={"twk" + (tweaks.accent === a.id ? " twk--on" : "")} onClick={() => set("accent", a.id)}><span className="twk-sw"><span className="twk-sw__dot" style={{ background: a.sw }} />{a.label}</span></button>)}</div>
            {tweaks.theme === "finance" && <div className="field__hint" style={{ marginTop: 8 }}>Theme Tài chính dùng Indigo khi để mặc định Hổ phách.</div>}
          </div>
          <div className="tweaks-sec">
            <div className="tweaks-sec__label">Bộ chữ</div>
            <div className="tweaks-opts">{FONTS.map((f) => <button key={f.id} className={"twk" + (tweaks.font === f.id ? " twk--on" : "")} onClick={() => set("font", f.id)} style={{ fontFamily: f.display }}>{f.label}</button>)}</div>
          </div>
          <div className="tweaks-sec">
            <div className="tweaks-sec__label">Mật độ</div>
            <div className="tweaks-opts">
              <button className={"twk" + (tweaks.density === "comfortable" ? " twk--on" : "")} onClick={() => set("density", "comfortable")}>Thoáng</button>
              <button className={"twk" + (tweaks.density === "compact" ? " twk--on" : "")} onClick={() => set("density", "compact")}>Gọn</button>
            </div>
          </div>
          <div className="tweaks-sec">
            <div className="tweaks-sec__label">Font số liệu</div>
            <div className="tweaks-opts">
              <button className={"twk" + (tweaks.numfont === "mono" ? " twk--on" : "")} onClick={() => set("numfont", "mono")}>Mono</button>
              <button className={"twk" + (tweaks.numfont === "sans" ? " twk--on" : "")} onClick={() => set("numfont", "sans")}>Sans</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ── Root App ───────────────────────────────────────────── */
const SCREEN_TITLE = {
  S01: "Worklist", S02: "Khách hàng", S03: "Hồ sơ 360", S04: "Dedup", S05: "Inbox", S06: "Hội thoại",
  S07: "Tasks", S08: "Segments", S09: "Segment Builder", S10: "Chiến dịch", S11: "Chiến dịch", S12: "Ads", S13: "Cài đặt",
};
function loadRoute() {
  try { const r = JSON.parse(localStorage.getItem("crm_route") || "null"); return r && r.screen ? r : { screen: "S01" }; } catch (e) { return { screen: "S01" }; }
}
function App() {
  const [route, setRoute] = aUseState(loadRoute);
  const [modals, setModals] = aUseState([]);
  const [toasts, setToasts] = aUseState([]);
  const [preview, setPreview] = aUseState(null);
  const [tweaks, setTweaks] = aUseState(loadTweaks);
  const scrollRef = aUseRef(null);

  aUseEffect(() => { applyTweaks(tweaks); localStorage.setItem("crm_tweaks", JSON.stringify(tweaks)); }, [tweaks]);
  aUseEffect(() => { localStorage.setItem("crm_route", JSON.stringify(route)); if (scrollRef.current) scrollRef.current.scrollTop = 0; window.scrollTo(0, 0); }, [route]);

  const nav = (r) => { setRoute(r); setModals([]); setPreview(null); };
  const openModal = (type, props) => setModals((m) => [...m, { type, props: props || {} }]);
  const closeModal = () => setModals((m) => m.slice(0, -1));
  const toast = (msg, kind) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, msg, kind: kind || "success" }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3000);
  };
  const openPreview = (partyId, rect) => setPreview({ partyId, rect });

  const screenProps = { route, nav, openModal, toast, openPreview };
  const SCREENS = {
    S01: window.S01_Worklist, S02: window.S02_CustomerList, S03: window.S03_Customer360, S04: window.S04_Dedup,
    S05: window.S05_Inbox, S06: window.S06_Conversation, S07: window.S07_Tasks, S08: window.S08_Segments,
    S09: window.S09_Builder, S10: window.S10_Campaigns, S11: window.S11_Campaign, S12: window.S12_Ads, S13: window.S13_Settings,
  };
  const ScreenComp = SCREENS[route.screen] || window.S01_Worklist;

  return (
    <div className="app">
      <header className="app-header" data-scrolled="false">
        <div className="brand" onClick={() => nav({ screen: "S01" })}>
          <span className="brand__dot" />
          <span className="brand__name">retail<b>CRM</b></span>
        </div>
        <GlobalSearch nav={nav} />
        <div className="context-slot">
          <span className="context-crumb"><b>{SCREEN_TITLE[route.screen]}</b></span>
          <button className="icon-btn" aria-label="Tài khoản"><Icon name="user" size={15} /></button>
        </div>
      </header>

      <div className="app-body">
        <Sidebar route={route} nav={nav} />
        <main className="app-content" ref={scrollRef}>
          <ScreenComp {...screenProps} />
        </main>
      </div>

      {modals.map((m, i) => {
        const Comp = window.MODALS[m.type];
        if (!Comp) return null;
        return <Comp key={i} ctx={m.props} close={closeModal} toast={toast} nav={nav} openModal={openModal} />;
      })}

      {preview && <QuickPreview partyId={preview.partyId} rect={preview.rect} close={() => setPreview(null)} nav={nav} />}
      <ToastStack toasts={toasts} />
      <TweaksPanel tweaks={tweaks} setTweaks={setTweaks} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);

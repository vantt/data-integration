/* ============================================================
   App shell: header · C01 registry nav · C02 search · router ·
   modals · O02 quick preview · toasts · Theme panel.
   ============================================================ */
const { useState: aUseState, useEffect: aUseEffect, useRef: aUseRef } = React;

/* ── Theme config ───────────────────────────────────────── */
/* Color palettes = base surface theme (ink ramp) + chosen accent.
   Applied by toggling [data-theme]/[data-accent] on <html> and
   overriding --font-* vars. Persisted to localStorage. */
const THEMES = [
{ id: "dark", label: "Precision", attr: "", sw: "#15151a" },
{ id: "slate", label: "Than chì", attr: "slate", sw: "#12161d" },
{ id: "light", label: "Sáng ấm", attr: "light", sw: "#faf7f0" },
{ id: "finance", label: "Tài chính", attr: "finance", sw: "#eef0fb" }];

const ACCENTS = [
{ id: "amber", label: "Hổ phách", attr: "", sw: "#e8a341" },
{ id: "moss", label: "Rêu", attr: "moss", sw: "#84b577" },
{ id: "honey", label: "Mật ong", attr: "honey", sw: "#d4a548" },
{ id: "indigo", label: "Chàm", attr: "indigo", sw: "#7c83f0" },
{ id: "teal", label: "Ngọc", attr: "teal", sw: "#4bb3a7" },
{ id: "coral", label: "San hô", attr: "coral", sw: "#e0746c" }];

const FONTS = [
{ id: "editorial", label: "Editorial", display: "'Newsreader', Georgia, serif", body: "'Geist', system-ui, sans-serif", mono: "'Geist Mono', monospace" },
{ id: "precision", label: "Precision", display: "'Fraunces', Georgia, serif", body: "'Geist', system-ui, sans-serif", mono: "'Geist Mono', monospace" },
{ id: "grotesk", label: "Grotesk", display: "'Space Grotesk', sans-serif", body: "'Geist', system-ui, sans-serif", mono: "'Geist Mono', monospace" },
{ id: "plex", label: "Plex", display: "'IBM Plex Serif', serif", body: "'IBM Plex Sans', sans-serif", mono: "'IBM Plex Mono', monospace" },
{ id: "source", label: "Source", display: "'Source Sans 3', sans-serif", body: "'Source Sans 3', system-ui, sans-serif", mono: "'JetBrains Mono', monospace" }];

const DEFAULT_TWEAKS = { theme: "dark", accent: "amber", font: "editorial", density: "comfortable", numfont: "mono" };

function loadTweaks() {
  try {return { ...DEFAULT_TWEAKS, ...JSON.parse(localStorage.getItem("crm_tweaks") || "{}") };} catch (e) {return { ...DEFAULT_TWEAKS };}
}
function applyTweaks(tw) {
  const root = document.documentElement;
  const theme = THEMES.find((t) => t.id === tw.theme) || THEMES[0];
  const accent = ACCENTS.find((a) => a.id === tw.accent) || ACCENTS[0];
  const font = FONTS.find((f) => f.id === tw.font) || FONTS[0];
  theme.attr ? root.setAttribute("data-theme", theme.attr) : root.removeAttribute("data-theme");
  // finance theme owns indigo accent; only override when user picks a non-default accent
  if (accent.attr) root.setAttribute("data-accent", accent.attr);else root.removeAttribute("data-accent");
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
    const h = (e) => {if (ref.current && !ref.current.contains(e.target)) setOpen(false);};
    document.addEventListener("mousedown", h);return () => document.removeEventListener("mousedown", h);
  }, []);
  const results = q.trim() ? window.DB.parties.filter((p) => p.name.toLowerCase().includes(q.toLowerCase()) || p.phone.includes(q) || (p.email || "").includes(q.toLowerCase()) || p.code.toLowerCase().includes(q.toLowerCase())).slice(0, 6) : [];
  return (
    <div className="search" ref={ref}>
      <div className="search__field">
        <input className="search__input" value={q} onChange={(e) => {setQ(e.target.value);setOpen(true);}} onFocus={() => setOpen(true)}
        placeholder="Tìm khách: SĐT, tên, email, code…" />
        <button className="search__submit" onClick={() => results[0] && nav({ screen: "S03", party: results[0].id })}><Icon name="search" size={15} /></button>
      </div>
      {open && q.trim() &&
      <div className="search__results">
          {results.length === 0 ?
        <div className="result-empty"><Icon name="search" size={14} /> Không tìm thấy "<b>{q}</b>"</div> :
        results.map((p) =>
        <div key={p.id} className="result-row" onClick={() => {setOpen(false);setQ("");nav({ screen: "S03", party: p.id });}}>
              <div><div className="result-row__name">{p.name}</div><div className="result-row__meta">{p.code} · {p.group}</div></div>
              <div className="result-row__meta">{p.phone}</div>
            </div>
        )}
        </div>
      }
    </div>);

}

/* ── C01 Registry Sidebar ───────────────────────────────────
   (split into two: the product C01 sidebar + the review harness below) */

/* ── C01 Sidebar Nav (PRODUCT component) ─────────────────────
   The real in-app left nav users see on every screen. A product
   surface (registry C01) — NOT the review harness. Carries only
   the everyday destinations, curated and grouped. */
const NAV = [
{ group: "Hằng ngày", items: [
  { id: "S01", icon: "worklist", label: "Worklist" },
  { id: "S02", icon: "customers", label: "Khách hàng" },
  { id: "S05", icon: "inbox", label: "Inbox", badge: "inbox" },
  { id: "S07", icon: "tasks", label: "Tasks" }]
},
{ group: "Tăng trưởng", items: [
  { id: "S08", icon: "segments", label: "Segments" },
  { id: "S10", icon: "campaigns", label: "Chiến dịch" },
  { id: "S12", icon: "ads", label: "Ads" }]
},
{ group: "Quản trị", items: [
  { id: "S04", icon: "dedup", label: "Dedup", badge: "dedup" },
  { id: "S13", icon: "settings", label: "Cài đặt" }]
}];

const SCREEN_OF_TAB = { S03: "S02", S06: "S05", S09: "S08", S11: "S10" };
function Sidebar({ route, nav }) {
  const inbox = window.DB.conversations.filter((c) => c.unread > 0).reduce((s, c) => s + c.unread, 0);
  const dedup = window.DB.dedup.filter((d) => d.status === "pending").length;
  const cur = SCREEN_OF_TAB[route.screen] || route.screen;
  return (
    <nav className="crm-nav" aria-label="Điều hướng">
      {NAV.map((g) =>
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
              </button>);

        })}
        </div>
      )}
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
    </nav>);

}

/* ── Surface Harness (REVIEW chrome — separate from product) ──
   An access rail that frames the product. Generated from
   window.REG (mirrors surface-registry.yaml): every screen /
   panel / modal / overlay / component is a row; clicking jumps
   straight to that surface on its correct host. */
function regActive(id, route, openId) {
  const s = window.REG.SURF[id];
  if (!s) return false;
  if (s.type === "screen") return route.screen === id;
  if (s.type === "panel") return route.screen === "S03" && (route.tab || "P01") === id;
  if (s.type === "modal" || s.type === "overlay") return openId === id;
  return false;
}
function RegRow({ id, route, openId, onGo, badge }) {
  const s = window.REG.SURF[id];
  const active = regActive(id, route, openId);
  const isScreen = s.type === "screen";
  return (
    <button className="crm-nav__item reg-row" aria-current={active ? "page" : undefined} onClick={() => onGo(id)} title={s.name}>
      {isScreen ?
      <span className="crm-nav__icon"><Icon name={s.icon} size={17} /></span> :
      <span className="reg-id">{id}</span>}
      <span className="crm-nav__label">{s.vi || s.name}</span>
      {badge != null && badge > 0 ?
      <span className={"crm-nav__badge" + (id === "S05" ? " crm-nav__badge--warn" : "")}>{badge}</span> :
      isScreen ? <span className="reg-tag">{id}</span> : null}
    </button>);

}
function HarnessRail({ route, openId, onGo, collapsed, setCollapsed }) {
  const [q, setQ] = aUseState("");
  const inbox = window.DB.conversations.filter((c) => c.unread > 0).reduce((s, c) => s + c.unread, 0);
  const dedup = window.DB.dedup.filter((d) => d.status === "pending").length;
  const ql = q.trim().toLowerCase();
  const match = (id) => {
    if (!ql) return true;
    const s = window.REG.SURF[id];
    return id.toLowerCase().includes(ql) || (s.vi || "").toLowerCase().includes(ql) || s.name.toLowerCase().includes(ql);
  };
  const badgeOf = (id) => id === "S05" ? inbox : id === "S04" ? dedup : null;
  const rows = (ids) => ids.filter(match);

  if (collapsed) {
    return (
      <aside className="harness-rail harness-rail--collapsed" aria-label="Surface harness">
        <button className="harness-expand" onClick={() => setCollapsed(false)} title="Mở harness">
          <span className="harness-dot" />
          <span className="harness-expand__label">SURFACE HARNESS</span>
          <Icon name="chevron" size={13} />
        </button>
      </aside>);

  }
  return (
    <aside className="harness-rail" aria-label="Surface harness">
      <div className="harness-head">
        <div className="harness-head__id">
          <span className="harness-dot" />
          <div>
            <div className="harness-head__title">Surface harness</div>
            <div className="harness-head__sub">surface-registry.yaml · {Object.keys(window.REG.SURF).length}</div>
          </div>
        </div>
        <button className="icon-btn icon-btn--sm" onClick={() => setCollapsed(true)} title="Thu gọn harness"><Icon name="back" size={13} /></button>
      </div>
      <div className="reg-search">
        <Icon name="search" size={13} />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Lọc surface… (id, tên)" aria-label="Lọc surface" />
        {q && <button className="reg-search__x" onClick={() => setQ("")} aria-label="Xóa">✕</button>}
      </div>

      <div className="reg-groups">
        {window.REG.GROUPS.map((g) => {
          const total = window.REG.count(g);
          // collect visible rows
          let body,visible = 0;
          if (g.subs) {
            const subsVis = g.subs.map((sub) => ({ label: sub.label, ids: rows(sub.items) })).filter((sub) => sub.ids.length);
            visible = subsVis.reduce((s, x) => s + x.ids.length, 0);
            body = subsVis.map((sub) =>
            <div key={sub.label} className="reg-sub">
                <div className="reg-sub__label">{sub.label}</div>
                {sub.ids.map((id) => <RegRow key={id} id={id} route={route} openId={openId} onGo={onGo} badge={badgeOf(id)} />)}
              </div>
            );
          } else {
            const ids = rows(g.items);
            visible = ids.length;
            body = ids.map((id) => <RegRow key={id} id={id} route={route} openId={openId} onGo={onGo} badge={badgeOf(id)} />);
          }
          // empty taxonomy bucket (onboarding / mobile): show only when not filtering
          const isEmptyBucket = total === 0;
          if (ql && visible === 0) return null;
          return (
            <div key={g.key} className="crm-nav__group reg-group">
              <div className="caption crm-nav__eyebrow reg-eyebrow">
                <span>{g.label}</span>
                <span className="reg-count">{total || "0"}</span>
              </div>
              {isEmptyBucket ?
              <div className="reg-empty">Chưa có surface trong registry</div> :
              body}
            </div>);

        })}
      </div>

      <div className="harness-foot">
        <span className="harness-foot__tag">HARNESS</span>
        <span className="crm-nav__sync">truy cập trực tiếp mọi surface · click = nhảy tới host</span>
      </div>
    </aside>);

}

/* ── O02 Quick Preview ──────────────────────────────────── */
function QuickPreview({ partyId, rect, close, nav }) {
  const p = window.DB.partyById(partyId);
  if (!p) return null;
  const top = Math.min(rect.bottom + 8, window.innerHeight - 280);
  const left = Math.min(rect.left, window.innerWidth - 340);
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 180 }} onMouseDown={(e) => {if (e.target === e.currentTarget) close();}}>
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
        <div className="qp-foot"><button className="btn btn--primary" style={{ width: "100%", padding: "9px 14px" }} onClick={() => {close();nav({ screen: "S03", party: p.id });}}>Mở hồ sơ đầy đủ <Icon name="chevron" size={13} /></button></div>
      </div>
    </div>);

}

/* ── Theme panel (header palette icon) ──────────────────── */
function ThemePanel({ tweaks, setTweaks, open, setOpen }) {
  const ref = aUseRef(null);
  const set = (k, v) => setTweaks((t) => ({ ...t, [k]: v }));
  aUseEffect(() => {
    if (!open) return;
    const h = (e) => {if (ref.current && !ref.current.contains(e.target) && !e.target.closest(".theme-fab")) setOpen(false);};
    const k = (e) => {if (e.key === "Escape") setOpen(false);};
    document.addEventListener("mousedown", h);document.addEventListener("keydown", k);
    return () => {document.removeEventListener("mousedown", h);document.removeEventListener("keydown", k);};
  }, [open]);
  if (!open) return null;
  return (
    <div className="theme-panel" ref={ref} role="dialog" aria-label="Theme">
      <div className="tweaks-panel__head">
        <div><span className="tweaks-panel__title">Theme</span><div className="theme-panel__sub">Màu &amp; bộ chữ · lưu cục bộ</div></div>
        <button className="icon-btn icon-btn--sm" onClick={() => setOpen(false)}><Icon name="close" size={13} /></button>
      </div>

      <div className="tweaks-sec">
        <div className="tweaks-sec__label">Bảng màu nền</div>
        <div className="theme-swatches">
          {THEMES.map((t) =>
          <button key={t.id} className={"theme-sw" + (tweaks.theme === t.id ? " theme-sw--on" : "")} onClick={() => set("theme", t.id)}>
              <span className="theme-sw__chip" style={{ background: t.sw }} />
              <span className="theme-sw__name">{t.label}</span>
            </button>
          )}
        </div>
      </div>

      <div className="tweaks-sec">
        <div className="tweaks-sec__label">Màu nhấn</div>
        <div className="theme-accents">
          {ACCENTS.map((a) =>
          <button key={a.id} className={"theme-acc" + (tweaks.accent === a.id ? " theme-acc--on" : "")} onClick={() => set("accent", a.id)} title={a.label}>
              <span className="theme-acc__dot" style={{ background: a.sw }} />
              <span className="theme-acc__name">{a.label}</span>
            </button>
          )}
        </div>
        {tweaks.theme === "finance" && <div className="field__hint" style={{ marginTop: 8 }}>Theme Tài chính dùng Chàm khi để mặc định Hổ phách.</div>}
      </div>

      <div className="tweaks-sec">
        <div className="tweaks-sec__label">Bộ chữ</div>
        <div className="tweaks-opts">{FONTS.map((f) => <button key={f.id} className={"twk" + (tweaks.font === f.id ? " twk--on" : "")} onClick={() => set("font", f.id)} style={{ fontFamily: f.display }}>{f.label}</button>)}</div>
      </div>

      <div className="tweaks-sec tweaks-sec--row">
        <div>
          <div className="tweaks-sec__label">Mật độ</div>
          <div className="tweaks-opts">
            <button className={"twk" + (tweaks.density === "comfortable" ? " twk--on" : "")} onClick={() => set("density", "comfortable")}>Thoáng</button>
            <button className={"twk" + (tweaks.density === "compact" ? " twk--on" : "")} onClick={() => set("density", "compact")}>Gọn</button>
          </div>
        </div>
        <div>
          <div className="tweaks-sec__label">Font số</div>
          <div className="tweaks-opts">
            <button className={"twk" + (tweaks.numfont === "mono" ? " twk--on" : "")} onClick={() => set("numfont", "mono")}>Mono</button>
            <button className={"twk" + (tweaks.numfont === "sans" ? " twk--on" : "")} onClick={() => set("numfont", "sans")}>Sans</button>
          </div>
        </div>
      </div>
    </div>);

}

/* ── Clean view: surface order + helpers ─────────────────── */
/* Flattened ordered list of every registry surface that has a
   launch spec — drives the floating ← / → mini-nav so a reviewer
   can flip through all surfaces and screenshot each one chrome-free. */
const SURFACE_ORDER = function () {
  const ids = [];
  (window.REG.GROUPS || []).forEach((g) => {
    if (g.subs) g.subs.forEach((sub) => (sub.items || []).forEach((id) => ids.push(id)));else
    (g.items || []).forEach((id) => ids.push(id));
  });
  return ids.filter((id) => window.REG.launch[id]);
}();
function currentSurfaceIdx(route, openId) {
  for (let i = 0; i < SURFACE_ORDER.length; i++) {
    if (regActive(SURFACE_ORDER[i], route, openId)) return i;
  }
  const byScreen = SURFACE_ORDER.indexOf(route.screen);
  return byScreen >= 0 ? byScreen : 0;
}
function loadClean() {
  try {
    const q = new URLSearchParams(location.search).get("clean");
    if (q === "1" || q === "true") return true;
    if (q === "0" || q === "false") return false;
    return localStorage.getItem("crm_clean") === "1";
  } catch (e) {return false;}
}

/* ── Clean-view floating mini-nav ─────────────────────────── */
/* Dim, auto-hides until hovered. ← / → flip surfaces, Esc exits,
   `h` hides the cluster entirely. Excluded from print via CSS. */
function CleanNav({ sid, idx, total, onPrev, onNext, onExit, hidden }) {
  const s = window.REG.SURF[sid] || {};
  return (
    <>
      {/* Always-visible exit button — top-right corner */}
      <button className="clean-exit-btn" onClick={onExit} title="Thoát clean view (Esc)" aria-label="Thoát clean view">
        <svg width="11" height="11" viewBox="0 0 11 11" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
          <line x1="1" y1="1" x2="10" y2="10" /><line x1="10" y1="1" x2="1" y2="10" />
        </svg>
        Thoát
      </button>
      {/* Floating surface nav — dim, reveals on hover */}
      {!hidden &&
      <div className="clean-nav" role="navigation" aria-label="Clean view">
          <button className="clean-nav__btn" onClick={onPrev} title="Surface trước (←)" aria-label="Surface trước">←</button>
          <div className="clean-nav__label">
            <span className="clean-nav__sid">{sid}</span>
            <span className="clean-nav__name">{s.vi || s.name || "\u2014"}</span>
            <span className="clean-nav__count">{idx + 1}/{total}</span>
          </div>
          <button className="clean-nav__btn" onClick={onNext} title="Surface sau (→)" aria-label="Surface sau">→</button>
        </div>
      }
    </>);

}

/* ── Root App ───────────────────────────────────────────── */
const SCREEN_TITLE = {
  S01: "Worklist", S02: "Khách hàng", S03: "Hồ sơ 360", S04: "Dedup", S05: "Inbox", S06: "Hội thoại",
  S07: "Tasks", S08: "Segments", S09: "Segment Builder", S10: "Chiến dịch", S11: "Chiến dịch", S12: "Ads", S13: "Cài đặt", S14: "Chế độ gọi"
};
function loadRoute() {
  try {const r = JSON.parse(localStorage.getItem("crm_route") || "null");return r && r.screen ? r : { screen: "S01" };} catch (e) {return { screen: "S01" };}
}
function App() {
  const [route, setRoute] = aUseState(loadRoute);
  const [modals, setModals] = aUseState([]);
  const [toasts, setToasts] = aUseState([]);
  const [preview, setPreview] = aUseState(null);
  const [tweaks, setTweaks] = aUseState(loadTweaks);
  const [themeOpen, setThemeOpen] = aUseState(false);
  const [harnessCollapsed, setHarnessCollapsed] = aUseState(() => {try {return localStorage.getItem("crm_harness") === "0";} catch (e) {return false;}});
  const [clean, setClean] = aUseState(loadClean);
  const [cleanIdx, setCleanIdx] = aUseState(() => currentSurfaceIdx(loadRoute(), null));
  const [cleanNavHidden, setCleanNavHidden] = aUseState(false);
  const scrollRef = aUseRef(null);

  aUseEffect(() => {try {localStorage.setItem("crm_harness", harnessCollapsed ? "0" : "1");} catch (e) {}}, [harnessCollapsed]);

  // persist clean mode; close Theme panel whenever clean turns on
  aUseEffect(() => {
    try {localStorage.setItem("crm_clean", clean ? "1" : "0");} catch (e) {}
    if (clean) setThemeOpen(false);
  }, [clean]);

  aUseEffect(() => {applyTweaks(tweaks);localStorage.setItem("crm_tweaks", JSON.stringify(tweaks));}, [tweaks]);
  aUseEffect(() => {localStorage.setItem("crm_route", JSON.stringify(route));if (scrollRef.current) scrollRef.current.scrollTop = 0;window.scrollTo(0, 0);}, [route]);

  const nav = (r) => {setRoute(r);setModals([]);setPreview(null);};
  const openModal = (type, props) => setModals((m) => [...m, { type, props: props || {} }]);
  const closeModal = () => setModals((m) => m.slice(0, -1));
  const toast = (msg, kind) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, msg, kind: kind || "success" }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3200);
  };
  const openPreview = (partyId, rect) => setPreview({ partyId, rect });

  // navigate to a host screen and immediately open a modal there
  const navOpen = (r, type, ctx) => {setRoute(r);setPreview(null);setModals([{ type, props: ctx || {} }]);};
  const navPreview = (r, partyId) => {
    setRoute(r);setModals([]);
    setPreview({ partyId, rect: { bottom: 156, top: 132, left: 372, right: 612 } });
  };

  // sidebar "go to surface"
  const go = (id) => {
    const L = window.REG.launch[id];
    if (!L) return;
    if (L.kind === "screen" || L.kind === "panel") nav(L.route);else
    if (L.kind === "comp") {nav(L.route);const s = window.REG.SURF[id];toast(`${id} · ${s.name} — trên màn ${L.where}`, "info");} else
    if (L.kind === "modal") navOpen(L.route, L.type, L.ctx ? L.ctx() : {});else
    if (L.kind === "preview") navPreview(L.route, L.party);
  };

  // clean view: step through the flat surface list with ← / →
  const stepSurface = (delta) => {
    const N = SURFACE_ORDER.length;
    if (!N) return;
    const ni = (cleanIdx + delta + N) % N;
    setCleanIdx(ni);
    go(SURFACE_ORDER[ni]);
  };

  // clean-view keyboard: ←/→ flip surface, Esc exit, h hide mini-nav
  aUseEffect(() => {
    if (!clean) return;
    const isField = (el) => el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable);
    const onKey = (e) => {
      if (e.key === "Escape") {setClean(false);return;}
      if (e.metaKey || e.ctrlKey || e.altKey || isField(e.target)) return;
      if (e.key === "ArrowRight") {e.preventDefault();stepSurface(1);} else
      if (e.key === "ArrowLeft") {e.preventDefault();stepSurface(-1);} else
      if (e.key === "h" || e.key === "H") {e.preventDefault();setCleanNavHidden((v) => !v);}
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [clean, cleanIdx]);

  const screenProps = { route, nav, openModal, toast, openPreview };
  const SCREENS = {
    S01: window.S01_Worklist, S02: window.S02_CustomerList, S03: window.S03_Customer360, S04: window.S04_Dedup,
    S05: window.S05_Inbox, S06: window.S06_Conversation, S07: window.S07_Tasks, S08: window.S08_Segments,
    S09: window.S09_Builder, S10: window.S10_Campaigns, S11: window.S11_Campaign, S12: window.S12_Ads, S13: window.S13_Settings,
    S14: window.S14_CallMode
  };
  const ScreenComp = SCREENS[route.screen] || window.S01_Worklist;
  const screenKey = [route.screen, route.party, route.tab, route.conversation, route.campaign, route.segment].filter(Boolean).join("·");
  const openId = modals.length ? modals[modals.length - 1].type : preview ? "O02" : null;
  const enterClean = () => {setCleanIdx(currentSurfaceIdx(route, openId));setClean(true);};

  return (
    <div className={"shell" + (harnessCollapsed ? " shell--collapsed" : "")} data-clean={clean ? "" : undefined}>
      <HarnessRail route={route} openId={openId} onGo={go} collapsed={harnessCollapsed} setCollapsed={setHarnessCollapsed} />
      <div className="app">
        <header className="app-header" data-scrolled="false">
          <div className="brand" onClick={() => nav({ screen: "S01" })}>
            <span className="brand__dot" />
            <span className="brand__name">retail<b>CRM</b></span>
          </div>
          <GlobalSearch nav={nav} />
          <div className="context-slot">
            <span className="context-crumb"><b>{SCREEN_TITLE[route.screen]}</b></span>
            <button className="clean-toggle" onClick={enterClean} aria-label="Clean view" title="Clean view — ẩn giàn giáo · ?clean=1"><span className="clean-toggle__dot" />Clean view</button>
            <button className={"theme-fab icon-btn" + (themeOpen ? " icon-btn--on" : "")} onClick={() => setThemeOpen((o) => !o)} aria-label="Theme" title="Theme — màu & bộ chữ"><Icon name="palette" size={16} /></button>
            <button className="icon-btn" aria-label="Tài khoản"><Icon name="user" size={15} /></button>
          </div>
        </header>

        <div className="app-body">
          {route.screen !== "S14" && <Sidebar route={route} nav={nav} />}
          <main className="app-content" ref={scrollRef}>
            <ScreenComp key={screenKey} {...screenProps} />
          </main>
        </div>
      </div>

      {modals.map((m, i) => {
        const Comp = window.MODALS[m.type];
        if (!Comp) return null;
        return <Comp key={i} ctx={m.props} close={closeModal} toast={toast} nav={nav} openModal={openModal} />;
      })}

      {preview && <QuickPreview partyId={preview.partyId} rect={preview.rect} close={() => setPreview(null)} nav={nav} />}
      <ToastStack toasts={toasts} />
      <ThemePanel tweaks={tweaks} setTweaks={setTweaks} open={themeOpen} setOpen={setThemeOpen} />
      {clean && <CleanNav sid={SURFACE_ORDER[cleanIdx]} idx={cleanIdx} total={SURFACE_ORDER.length} onPrev={() => stepSurface(-1)} onNext={() => stepSurface(1)} onExit={() => setClean(false)} hidden={cleanNavHidden} />}
    </div>);

}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
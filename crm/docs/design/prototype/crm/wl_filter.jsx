/* ============================================================
   S01 Worklist — Filter bar (C05) · sticky two-row layout
   "Compact when clean, expressive when filtered."

   Row 1 (always): search · Ưu tiên · 3 mode toggles · "Lọc nâng cao"
   Row 2 (toggles open): Loại · Phân khúc · Hạng KH · Sản phẩm

   9 filter dimensions (spec contract):
     priority · type · strategic_tier · value_group · product
     q · min_value · hide_contacted · has_script
   Strictly tokens (var(--*)). No emoji (Precision rule) — hand
   glyphs via <Icon>. Filters are wired for demo feel in S01.
   ============================================================ */
const { useState: fUseState, useEffect: fUseEffect, useRef: fUseRef } = React;

/* ── Defaults + catalogs ────────────────────────────────── */
const WLF_DEFAULTS = {
  priority: "all", type: "", strategic_tier: "", value_group: "",
  product: "", q: "", min_value: false, hide_contacted: false, has_script: false,
};

const WLF_SELECTS = [
  { key: "priority", label: "Ưu tiên", group: "pt", options: [
    { v: "all", l: "Tất cả" }, { v: "high", l: "Cao" }, { v: "urgent", l: "Khẩn" } ] },
  { key: "type", label: "Loại", group: "pt", options: [
    { v: "", l: "Tất cả" }, { v: "CALL_NOW", l: "Gọi ngay" }, { v: "WIN_BACK", l: "Kéo lại" },
    { v: "REORDER_NUDGE", l: "Nhắc mua lại" }, { v: "UPSELL", l: "Upsell" },
    { v: "CROSS_SELL", l: "Bán chéo" }, { v: "LOYALTY_REWARD", l: "Tri ân" } ] },
  { key: "strategic_tier", label: "Phân khúc", group: "ph", options: [
    { v: "", l: "Tất cả" }, { v: "growth", l: "Tăng trưởng" }, { v: "retain", l: "Giữ chân" },
    { v: "reactivate", l: "Tái kích hoạt" }, { v: "develop", l: "Phát triển" },
    { v: "protect", l: "Bảo vệ" }, { v: "potential", l: "Tiềm năng" }, { v: "at_risk", l: "Nguy cơ rời" } ] },
  { key: "value_group", label: "Hạng KH", group: "ph", options: [
    { v: "", l: "Tất cả" }, { v: "VIP", l: "VIP" }, { v: "GOLD", l: "GOLD" },
    { v: "SILVER", l: "SILVER" }, { v: "BRONZE", l: "BRONZE" } ] },
  { key: "product", label: "Sản phẩm", group: "sp", options: [
    { v: "", l: "Tất cả" }, { v: "p1", l: "Sữa rửa mặt" }, { v: "p2", l: "Serum HA" },
    { v: "p3", l: "Kem chống nắng" }, { v: "p4", l: "Toner" }, { v: "p5", l: "Mặt nạ" },
    { v: "p6", l: "Kem dưỡng" }, { v: "p7", l: "Tẩy trang" }, { v: "p8", l: "Combo skincare" } ] },
];
const WLF_TOGGLES = [
  { key: "min_value", label: "Giá trị cao", icon: "money" },
  { key: "hide_contacted", label: "Ẩn đã liên hệ", icon: "check" },
  { key: "has_script", label: "Có kịch bản", icon: "worklist" },
];
const WLF_SEL = (key) => WLF_SELECTS.find((s) => s.key === key);

/* active chips (selects + toggles; q has its own box → not chipped) */
function wlfChips(filters) {
  const out = [];
  WLF_SELECTS.forEach((s) => {
    const v = filters[s.key];
    if (v && v !== "all" && v !== "") {
      const o = s.options.find((o) => o.v === v);
      out.push({ key: s.key, text: o ? o.l : v });
    }
  });
  WLF_TOGGLES.forEach((t) => { if (filters[t.key]) out.push({ key: t.key, text: t.label, icon: t.icon }); });
  return out;
}
function wlfCount(filters) {
  let n = wlfChips(filters).length;
  if (filters.q && filters.q.trim()) n++;
  return n;
}

/* close-on-outside-click hook */
function useWlfDismiss(open, setOpen) {
  const ref = fUseRef(null);
  fUseEffect(() => {
    if (!open) return;
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const k = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", h); document.addEventListener("keydown", k);
    return () => { document.removeEventListener("mousedown", h); document.removeEventListener("keydown", k); };
  }, [open, setOpen]);
  return ref;
}

/* ── Shared primitives ──────────────────────────────────── */
function WlfSearch({ filters, set, grow }) {
  return (
    <div className={"toolbar__search wlf-search" + (grow ? " wlf-search--grow" : "")}>
      <Icon name="search" size={15} />
      <input value={filters.q} placeholder="Tìm tên, SĐT, mã KH…"
        onChange={(e) => set({ q: e.target.value })} />
      {filters.q && <button className="toolbar__clear" onClick={() => set({ q: "" })} aria-label="Xóa tìm kiếm">✕</button>}
    </div>
  );
}
function WlfSelect({ s, filters, set, block }) {
  const v = filters[s.key] || (s.key === "priority" ? "all" : "");
  return (
    <div className={"fsel" + (block ? " fsel--block" : "")}>
      <div className="fsel__label caption">{s.label}</div>
      <div className="fsel__field">
        <select value={v} onChange={(e) => set({ [s.key]: e.target.value })}>
          {s.options.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
        </select>
        <span className="fsel__chev"><Icon name="chevdown" size={12} /></span>
      </div>
    </div>
  );
}
function WlfToggle({ t, filters, set }) {
  const on = !!filters[t.key];
  return (
    <button type="button" className={"wlf-toggle" + (on ? " wlf-toggle--on" : "")}
      aria-pressed={on} onClick={() => set({ [t.key]: !on })}>
      <Icon name={t.icon} size={13} /> {t.label}
    </button>
  );
}
function WlfClear({ filters, clear }) {
  if (wlfCount(filters) === 0) return null;
  return <button className="wlf-clear" onClick={clear}>Xóa filter</button>;
}

/* ── Sticky two-row layout ──────────────────────────────── */
function WlfTwoRow({ filters, set, clear }) {
  const secondaryKeys = ["type", "strategic_tier", "value_group", "product"];
  const secN = secondaryKeys.filter((k) => filters[k] && filters[k] !== "").length;
  const [open, setOpen] = fUseState(secN > 0);
  return (
    <div className="wlf wlf-tworow">
      <div className="wlf-bar wlf-row1">
        <WlfSearch filters={filters} set={set} />
        <WlfSelect s={WLF_SEL("priority")} filters={filters} set={set} />
        <div className="wlf-row1__toggles">
          {WLF_TOGGLES.map((t) => <WlfToggle key={t.key} t={t} filters={filters} set={set} />)}
        </div>
        <span className="wlf-spacer" />
        <button type="button" className={"wlf-advbtn" + (open ? " wlf-advbtn--on" : "")}
          aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          <Icon name="filter" size={13} /> Lọc nâng cao
          {secN > 0 && <span className="wlf-count">{secN}</span>}
          <span className="wlf-trigger__chev" data-open={open}><Icon name="chevdown" size={12} /></span>
        </button>
        <WlfClear filters={filters} clear={clear} />
      </div>
      {open && (
        <div className="wlf-bar wlf-row2">
          {secondaryKeys.map((k) => <WlfSelect key={k} s={WLF_SEL(k)} filters={filters} set={set} />)}
          <span className="wlf-spacer" />
          {secN > 0 && <button className="wlf-clear" onClick={() => set(Object.fromEntries(secondaryKeys.map((k) => [k, ""])))}>Bỏ lọc nâng cao</button>}
        </div>
      )}
    </div>
  );
}

/* ── Host ────────────────────────────────────────────────── */
function WLFilterBar({ filters, setFilters }) {
  const set = (patch) => setFilters((f) => ({ ...f, ...patch }));
  const clear = () => setFilters({ ...WLF_DEFAULTS });
  return <WlfTwoRow filters={filters} set={set} clear={clear} />;
}

Object.assign(window, { WLFilterBar, WLF_DEFAULTS, wlfChips, wlfCount });

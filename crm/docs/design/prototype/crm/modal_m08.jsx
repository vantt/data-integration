/* ============================================================
   M08 — Ghi nhận tiếp xúc (Unified Contact Logging) — REDESIGN
   One linear form. Hình thức → kênh cụ thể → kết quả → nội dung
   → (tùy chọn) lưu thành ghi chú → thời gian/đơn.
   No tabs. Precision DS classes only. Conditional sections via state.
   Exposes M08 on window; overrides window.MODALS.M08 if present.
   ============================================================ */
(function () {
  const { useState, useMemo } = React;

  /* ── current ICT (UTC+7) as a datetime-local value string ── */
  function ictNowStr(plusMin) {
    const d = new Date(Date.now() + 7 * 3600000 + (plusMin || 0) * 60000);
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}T${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`;
  }
  function fmtIdentity(v, t) {
    if ((t === "phone" || t === "phone_secondary" || t === "zalo") && /^(\+?84|0)\d+$/.test(v.replace(/\s/g, ""))) {
      const local = v.replace(/^\+?84/, "0").replace(/\s/g, "");
      return local.replace(/(\d{4})(\d{3})(\d{0,3}).*/, "$1 $2 $3").trim();
    }
    return v;
  }

  /* ── channel-glyph set (hand-drawn, 1.3 stroke — Precision) ── */
  function ChIcon({ name, size = 15 }) {
    const p = { fill: "none", stroke: "currentColor", strokeWidth: 1.3, strokeLinecap: "round", strokeLinejoin: "round" };
    const s = (c) => <svg width={size} height={size} viewBox="0 0 16 16" {...p}>{c}</svg>;
    switch (name) {
      case "phone": return s(<path d="M5.2 2.8 6.6 5 5.4 6.4a8 8 0 0 0 4.2 4.2L11 9.4l2.2 1.4c.4.3.5.8.2 1.2-1 1.4-2.8 1.8-5 .8A12 12 0 0 1 3.2 7C2.2 4.8 2.6 3 4 2c.4-.3.9-.2 1.2.2z" />);
      case "chat": return s(<><path d="M2.5 4.2A1.5 1.5 0 0 1 4 2.7h8a1.5 1.5 0 0 1 1.5 1.5v4.6A1.5 1.5 0 0 1 12 10.3H6.2L3.3 12.8V10.3H4a1.5 1.5 0 0 1-1.5-1.5z" /><path d="M5.3 5.6h5.4M5.3 7.6h3.2" /></>);
      case "social": return s(<><circle cx="8" cy="8" r="5.5" /><path d="M9.6 5.2H8.5c-.7 0-1 .4-1 1v1.1m-1 0h2.6M7.5 7.3v3.5" /></>);
      case "mail": return s(<><rect x="2.3" y="3.5" width="11.4" height="9" rx="1.4" /><path d="M2.6 4.3 8 8.4l5.4-4.1" /></>);
      case "pin": return s(<><path d="M8 14s4.3-4.1 4.3-7.2A4.3 4.3 0 0 0 8 2.5a4.3 4.3 0 0 0-4.3 4.3C3.7 9.9 8 14 8 14z" /><circle cx="8" cy="6.7" r="1.5" /></>);
      case "dots": return s(<><circle cx="4" cy="8" r=".9" /><circle cx="8" cy="8" r=".9" /><circle cx="12" cy="8" r=".9" /></>);
      default: return null;
    }
  }

  /* ── custom icon-select for HÌNH THỨC ────────────────────── */
  function M8HinhThucSelect({ value, onChange }) {
    const [open, setOpen] = useState(false);
    const ref = React.useRef(null);
    React.useEffect(() => {
      if (!open) return;
      const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
      document.addEventListener('mousedown', h);
      return () => document.removeEventListener('mousedown', h);
    }, [open]);
    const sel = HINH_THUC.find((h) => h.v === value) || HINH_THUC[0];
    return (
      <div className="m8-htsel" ref={ref}>
        <button type="button" className="m8-htsel__btn" onClick={() => setOpen((o) => !o)} aria-haspopup="listbox">
          <ChIcon name={sel.icon} size={14} />
          <span>{sel.l}</span>
          <span className="inp-sel__chev" style={{ marginLeft: 'auto' }}>▾</span>
        </button>
        {open && (
          <div className="m8-htsel__drop" role="listbox">
            {HINH_THUC.map((h) => (
              <button type="button" key={h.v} role="option" aria-selected={value === h.v}
                className={'m8-htsel__opt' + (value === h.v ? ' m8-htsel__opt--on' : '')}
                onClick={() => { onChange(h.v); setOpen(false); }}>
                <ChIcon name={h.icon} size={14} />
                <span>{h.l}</span>
                {value === h.v && <Icon name="check" size={12} style={{ marginLeft: 'auto' }} />}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  /* ── config ─────────────────────────────────────────────── */
  const HINH_THUC = [
    { v: "call", l: "Cuộc gọi", icon: "phone" },
    { v: "zalo", l: "Zalo", icon: "chat" },
    { v: "fb", l: "Facebook", icon: "social" },
    { v: "email", l: "Email", icon: "mail" },
    { v: "visit", l: "Viếng thăm", icon: "pin" },
    { v: "other", l: "Khác", icon: "dots" },
  ];
  const CH_TYPES = { call: ["phone", "phone_secondary"], zalo: ["zalo"], fb: ["facebook", "psid"], email: ["email"] };
  const CH_HEAD = { call: "SỐ ĐIỆN THOẠI", zalo: "TÀI KHOẢN ZALO", fb: "TÀI KHOẢN FACEBOOK", email: "ĐỊA CHỈ EMAIL" };
  const CH_LABEL = { call: "số điện thoại", zalo: "tài khoản Zalo", fb: "tài khoản Facebook", email: "email" };
  const CH_PLACE = { call: "Nhập số khác…", zalo: "Nhập số/tên Zalo khác…", fb: "Nhập tên/ID Facebook…", email: "Nhập email khác…" };
  const OUTCOME_SET = {
    call: [{ v: "answered", l: "Đã nghe" }, { v: "no_answer", l: "Không bắt" }, { v: "callback", l: "Hẹn lại" }, { v: "refused", l: "Từ chối" }],
    chat: [{ v: "replied", l: "Đã phản hồi" }, { v: "pending", l: "Chưa phản hồi" }, { v: "no_reply", l: "Không phản hồi" }],
    visit: [{ v: "met", l: "Gặp được" }, { v: "not_met", l: "Không gặp được" }],
  };
  const NOTE_TYPES = [
    { v: "outcome", l: "Kết quả" }, { v: "general", l: "Chung" }, { v: "preference", l: "Sở thích" },
    { v: "warning", l: "Cảnh báo" }, { v: "internal", l: "Nội bộ" },
  ];
  const outcomeGroup = (ht) => (ht === "call" ? "call" : ht === "visit" ? "visit" : "chat");
  const defaultNoteType = (ht) => (ht === "email" ? "general" : "outcome");
  const activityType = (ht) => ({ call: "call", zalo: "chat", fb: "chat", email: "email", visit: "visit", other: "other" }[ht]);

  function bodyPlaceholder(ht, oc) {
    if (ht === "call") return oc === "answered" ? "Nội dung trao đổi với khách…" : oc === "callback" ? "Lý do hẹn lại, nội dung cần trao đổi…" : "Ghi chú thêm (không bắt buộc)";
    if (ht === "visit") return oc === "met" ? "Kết quả buổi ghé thăm…" : "Ghi chú thêm (không bắt buộc)";
    if (ht === "other") return "Nội dung tiếp xúc…";
    return oc === "replied" ? "Nội dung phản hồi của khách…" : "Ghi chú thêm (không bắt buộc)";
  }
  const bodyRequired = (ht, oc) => (ht === "call" && oc === "answered") || (ht === "visit" && oc === "met");

  /* ── demo identities keyed by party id (fallback when ctx has none) ── */
  const DEMO_IDENTITIES = {
    p_001: [
      { identity_id: "id_a1", identity_type: "phone", identity_value: "+84901234567", is_primary: true, contact_status: "active" },
      { identity_id: "id_a2", identity_type: "phone_secondary", identity_value: "+84908765432", is_primary: false, contact_status: "active" },
      { identity_id: "id_a3", identity_type: "phone_secondary", identity_value: "+84905000111", is_primary: false, contact_status: "inactive" },
      { identity_id: "id_a4", identity_type: "zalo", identity_value: "+84901234567", is_primary: true, contact_status: "active" },
      { identity_id: "id_a5", identity_type: "facebook", identity_value: "An Nguyễn", is_primary: true, contact_status: "active" },
      { identity_id: "id_a6", identity_type: "email", identity_value: "an.nguyen@gmail.com", is_primary: true, contact_status: "active" },
    ],
  };
  function resolveIdentities(ctx) {
    if (ctx.identities) return ctx.identities;
    if (DEMO_IDENTITIES[ctx.party]) return DEMO_IDENTITIES[ctx.party];
    const p = window.DB && window.DB.partyById && window.DB.partyById(ctx.party);
    const out = [];
    if (p && p.phone) out.push({ identity_id: "ph", identity_type: "phone", identity_value: p.phone, is_primary: true, contact_status: "active" });
    if (p && p.email) out.push({ identity_id: "em", identity_type: "email", identity_value: p.email, is_primary: true, contact_status: "active" });
    return out;
  }

  /* ── small helpers using shared atoms ───────────────────── */
  const Btn = ({ kind = "secondary", onClick, disabled, children }) =>
    <button className={"btn btn--" + kind} onClick={onClick} disabled={disabled}>{children}</button>;
  const CancelBtn = window.CancelBtn || (({ onClick }) => <button className="btn btn--ghost" onClick={onClick} style={{ padding: "10px 14px" }}>Hủy</button>);

  function SectionLabel({ children, req }) {
    return <span className="field__label">{children}{req && <span className="field__req"> *</span>}</span>;
  }

  /* ── channel picker (Step 2) ────────────────────────────── */
  function ChannelPicker({ ht, identities, sel, setSel, customVal, setCustomVal }) {
    const matches = identities.filter((i) => CH_TYPES[ht].includes(i.identity_type));
    const [showCustom, setShowCustom] = useState(false);
    const usingCustom = sel === "__custom";

    const chip = (i) => (
      <div key={i.identity_id} className={"m8-chan" + (sel === i.identity_id ? " m8-chan--on" : "") + (i.contact_status === "inactive" ? " m8-chan--off" : "")}
        onClick={() => { setSel(i.identity_id); setShowCustom(false); }}>
        <span className="radio-pill__dot" />
        <span className="m8-chan__val mono">{fmtIdentity(i.identity_value, i.identity_type)}</span>
        {i.is_primary && <span className="m8-chan__tag">chính</span>}
        {i.contact_status === "inactive" && <span className="m8-chan__tag m8-chan__tag--off">ngưng dùng</span>}
      </div>
    );

    const customRow = (
      <div className={"m8-chan m8-chan--custom" + (usingCustom ? " m8-chan--on" : "")}>
        <div className="m8-chan__head" onClick={() => { setSel("__custom"); setShowCustom(true); }}>
          <span className="radio-pill__dot" />
          <span className="m8-chan__val">Nhập {CH_LABEL[ht]} khác…</span>
        </div>
        {usingCustom && <input className="inp inp--mono" autoFocus value={customVal} onChange={(e) => setCustomVal(e.target.value)} placeholder={CH_PLACE[ht]} style={{ marginTop: 8 }} />}
      </div>
    );

    if (matches.length === 0) {
      return (
        <label className="field">
          <SectionLabel>{CH_HEAD[ht]}</SectionLabel>
          <div className="caveat caveat--info" style={{ marginBottom: 2 }}>Không có {CH_LABEL[ht]} trong hồ sơ — nhập thủ công hoặc bỏ qua.</div>
          <input className="inp inp--mono" value={customVal} onChange={(e) => { setCustomVal(e.target.value); setSel("__custom"); }} placeholder={CH_PLACE[ht]} />
        </label>
      );
    }
    if (matches.length === 1 && !showCustom) {
      const only = matches[0];
      return (
        <label className="field">
          <SectionLabel>{CH_HEAD[ht]}</SectionLabel>
          <div className={"m8-chan m8-chan--solo" + (sel === only.identity_id ? " m8-chan--on" : "")} onClick={() => setSel(only.identity_id)}>
            <span className="radio-pill__dot" />
            <span className="m8-chan__val mono">{fmtIdentity(only.identity_value, only.identity_type)}</span>

          </div>
          <button className="ghost-link" type="button" onClick={() => { setShowCustom(true); setSel("__custom"); }} style={{ marginTop: 2 }}>Dùng {CH_LABEL[ht]} khác</button>
        </label>
      );
    }
    return (
      <label className="field">
        <SectionLabel>{CH_HEAD[ht]}</SectionLabel>
        <div className="m8-chanset">
          {matches.map(chip)}
          {customRow}
        </div>
      </label>
    );
  }

  /* ── note-options box (Step 5) ──────────────────────────── */
  function NoteOptions({ noteType, setNoteType, pinned, setPinned, visibility, setVisibility }) {
    return (
      <div className="m8-notebox">
        <div className="field-row">
          <label className="field">
            <SectionLabel>LOẠI GHI CHÚ</SectionLabel>
            <Select value={noteType} onChange={(e) => setNoteType(e.target.value)}>
              {NOTE_TYPES.map((n) => <option key={n.v} value={n.v}>{n.l}</option>)}
            </Select>
          </label>
          <label className="field">
            <SectionLabel>HIỂN THỊ</SectionLabel>
            <Select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
              <option value="team">Team</option>
              <option value="private">Riêng tư</option>
            </Select>
          </label>
        </div>
        <label className="field">
          <SectionLabel>GHIM</SectionLabel>
          <div className="radioset">
            <label className={"radio-pill" + (pinned === "0" ? " radio-pill--on" : "")} onClick={() => setPinned("0")}><span className="radio-pill__dot" />Không ghim</label>
            <label className={"radio-pill" + (pinned === "1" ? " radio-pill--on" : "")} onClick={() => setPinned("1")}><span className="radio-pill__dot" />Ghim</label>
          </div>
        </label>
      </div>
    );
  }

  /* ── MAIN ───────────────────────────────────────────────── */
  function M08({ ctx, close, toast }) {
    ctx = ctx || {};
    const editNote = ctx.mode === "edit_note" || ctx.mode === "edit";
    const party = (window.DB && window.DB.partyById && window.DB.partyById(ctx.party)) || null;
    const partyName = ctx.party_name || (party && party.name) || "Khách hàng";
    const identities = useMemo(() => resolveIdentities(ctx), [ctx.party]);
    const prefNotes = ctx.contact_pref_notes || (party && party.contact_pref_notes) || [];

    const [ht, setHt] = useState(ctx.hinh_thuc || "call");
    const [sel, setSel] = useState(null);
    const [customVal, setCustomVal] = useState("");
    const [outcome, setOutcome] = useState(null);
    const [body, setBody] = useState(editNote ? (ctx.note_body || "") : "");
    const [callbackAt, setCallbackAt] = useState(ictNowStr(120));
    const [makeTask, setMakeTask] = useState(true);
    const [occurredAt, setOccurredAt] = useState(ictNowStr(0));
    const [orderCode, setOrderCode] = useState("");
    const [saveNote, setSaveNote] = useState(false);
    const [noteType, setNoteType] = useState(editNote ? (ctx.note_type_val || "outcome") : "outcome");
    const [pinned, setPinned] = useState(editNote ? (ctx.note_pinned ? "1" : "0") : "0");
    const [visibility, setVisibility] = useState(editNote ? (ctx.note_visibility || "team") : "team");

    // auto-select primary identity whenever hình thức changes
    const matches = identities.filter((i) => CH_TYPES[ht] && CH_TYPES[ht].includes(i.identity_type));
    React.useEffect(() => {
      if (editNote) return;
      const active = matches.filter((i) => i.contact_status !== "inactive");
      const primary = active.find((i) => i.is_primary) || active[0];
      setSel(primary ? primary.identity_id : (matches.length === 0 ? "__custom" : null));
      setCustomVal("");
      setOutcome(null);
      setNoteType(defaultNoteType(ht));
    }, [ht]);

    const hasChannel = ht !== "visit" && ht !== "other";
    const hasOutcome = ht !== "other";
    const showCallback = ht === "call" && outcome === "callback";
    const reqBody = bodyRequired(ht, outcome);
    const outcomes = OUTCOME_SET[outcomeGroup(ht)] || [];

    const canSave = editNote
      ? !!body.trim()
      : (hasOutcome ? !!outcome : true) && (!reqBody || !!body.trim());

    const submit = () => {
      if (editNote) { toast("Đã cập nhật ghi chú"); close(); return; }
      const made = []; made.push("hoạt động");
      if (showCallback && makeTask) made.push("task nhắc");
      if (saveNote && body.trim()) made.push("ghi chú hồ sơ");
      toast("Đã ghi nhận " + made.join(" · "));
      close();
    };

    /* ── EDIT NOTE: reduced form ── */
    if (editNote) {
      return (
        <Modal title="Sửa ghi chú" sub={partyName} onClose={close} width={500}
          actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!canSave} onClick={submit}>Lưu ghi chú</Btn></>}>
          <label className="field">
            <SectionLabel req>NỘI DUNG</SectionLabel>
            <textarea className="inp inp--area" value={body} onChange={(e) => setBody(e.target.value)} autoFocus placeholder="Nội dung ghi chú…" />
          </label>
          <NoteOptions noteType={noteType} setNoteType={setNoteType} pinned={pinned} setPinned={setPinned} visibility={visibility} setVisibility={setVisibility} />
        </Modal>
      );
    }

    return (
      <Modal title="Ghi nhận tiếp xúc" sub={partyName} onClose={close} width={520}
        actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!canSave} onClick={submit}>Lưu hoạt động</Btn></>}>

        {prefNotes.length > 0 && (
          <div className="caveat caveat--warn">
            <span className="caveat__mark">⚠</span>
            <span><b>Lưu ý liên hệ:</b> {prefNotes.map((n) => (typeof n === "string" ? n : n.body)).join(" · ")}</span>
          </div>
        )}

        {/* Step 1 — Hình thức */}
        <div className="field">
          <SectionLabel req>HÌNH THỨC</SectionLabel>
          <M8HinhThucSelect value={ht} onChange={setHt} />
        </div>

        {/* Step 2 — Kênh cụ thể */}
        {hasChannel && (
          <ChannelPicker ht={ht} identities={identities} sel={sel} setSel={setSel} customVal={customVal} setCustomVal={setCustomVal} />
        )}

        {/* Step 3 — Kết quả */}
        {hasOutcome && (
          <label className="field">
            <SectionLabel req>KẾT QUẢ</SectionLabel>
            <div className="radioset">
              {outcomes.map((o) => (
                <label key={o.v} className={"radio-pill" + (outcome === o.v ? " radio-pill--on" : "")} onClick={() => setOutcome(o.v)}>
                  <span className="radio-pill__dot" />{o.l}
                </label>
              ))}
            </div>
          </label>
        )}

        {/* Step 3b — Hẹn lại */}
        {showCallback && (
          <div className="m8-notebox">
            <label className="field">
              <SectionLabel>HẸN GỌI LẠI LÚC</SectionLabel>
              <input type="datetime-local" className="inp inp--mono" value={callbackAt} onChange={(e) => setCallbackAt(e.target.value)} />
            </label>
            <label className="chk-row" onClick={() => setMakeTask(!makeTask)} style={{ marginTop: 10 }}>
              <span className={"chk-box" + (makeTask ? " chk-box--on" : "")}>{makeTask && <Icon name="check" size={12} />}</span>
              <span className="chk-row__text">Tạo task nhắc tự động</span>
            </label>
          </div>
        )}

        {/* Step 4 — Nội dung */}
        <label className="field">
          <SectionLabel req={reqBody}>NỘI DUNG</SectionLabel>
          <textarea className="inp inp--area" value={body} onChange={(e) => setBody(e.target.value)} placeholder={bodyPlaceholder(ht, outcome)} />
        </label>

        {/* Step 5 — Lưu thành ghi chú */}
        <div>
          <label className="chk-row" onClick={() => setSaveNote(!saveNote)}>
            <span className={"chk-box" + (saveNote ? " chk-box--on" : "")}>{saveNote && <Icon name="check" size={12} />}</span>
            <span className="chk-row__text">Lưu thành ghi chú hồ sơ <span className="m8-dim">— thông tin lâu dài, tách khỏi timeline</span></span>
          </label>
          {saveNote && <NoteOptions noteType={noteType} setNoteType={setNoteType} pinned={pinned} setPinned={setPinned} visibility={visibility} setVisibility={setVisibility} />}
        </div>

        <div className="m8-rule" />

        {/* Step 6 — Thời gian & đơn */}
        <div className="field-row">
          <label className="field">
            <SectionLabel>THỜI GIAN</SectionLabel>
            <input type="datetime-local" className="inp inp--mono" value={occurredAt} onChange={(e) => setOccurredAt(e.target.value)} />
          </label>
          <label className="field">
            <SectionLabel>ĐƠN LIÊN QUAN</SectionLabel>
            <input className="inp inp--mono" value={orderCode} onChange={(e) => setOrderCode(e.target.value)} placeholder="ORD-… (tùy chọn)" />
          </label>
        </div>
      </Modal>
    );
  }

  window.M08 = M08;
  if (window.MODALS) window.MODALS.M08 = M08;
})();

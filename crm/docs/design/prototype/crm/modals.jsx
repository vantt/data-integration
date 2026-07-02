/* ============================================================
   Modals (M01–M14) + Overlays (O01, O02) + Toast.
   Each modal: props {ctx, close, toast, nav}. Faithful to spec.
   ============================================================ */
const { useState: mUseState, useEffect: mUseEffect } = React;

function Btn({ kind = "secondary", onClick, disabled, children }) {
  return <button className={"btn btn--" + kind} onClick={onClick} disabled={disabled}>{children}</button>;
}
function CancelBtn({ onClick }) { return <button className="btn btn--ghost" onClick={onClick} style={{ padding: "10px 14px" }}>Hủy</button>; }

/* ── M01 Merge Confirm ──────────────────────────────────── */
function M01({ ctx, close, toast }) {
  const [ok, setOk] = mUseState(false);
  const c = ctx.candidate;
  return (
    <Modal title="Xác nhận gộp khách" sub={`Merge ${c.b.name} → ${c.a.name} (giữ lại)`} onClose={close} width={500}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!ok} onClick={() => { toast(`Đã gộp ${c.b.name} vào ${c.a.name}`); close(); }}><Icon name="merge" size={14} /> Xác nhận Merge</Btn></>}>
      <div className="dedup-compare">
        <div className="dedup-card dedup-card--survive">
          <span className="dedup-card__tag"><Bdg tone="accent">GIỮ LẠI · A</Bdg></span>
          <div className="name" style={{ fontSize: 17 }}>{c.a.name}</div>
          <div className="mono" style={{ fontSize: 12, color: "var(--fg-muted)", marginTop: 6 }}>{c.a.phone}</div>
          <div className="facts" style={{ marginTop: 12 }}>
            <div className="fact"><span className="fact__k">Sapo</span><span className="fact__v mono">{c.a.sapo}</span></div>
            <div className="fact"><span className="fact__k">Đơn</span><span className="fact__v mono">{c.a.orders}</span></div>
          </div>
        </div>
        <div className="dedup-card">
          <span className="dedup-card__tag"><Bdg>GỘP VÀO · B</Bdg></span>
          <div className="name" style={{ fontSize: 17 }}>{c.b.name}</div>
          <div className="mono" style={{ fontSize: 12, color: "var(--fg-muted)", marginTop: 6 }}>{c.b.phone}</div>
          <div className="facts" style={{ marginTop: 12 }}>
            <div className="fact"><span className="fact__k">Sapo</span><span className="fact__v mono">{c.b.sapo}</span></div>
            <div className="fact"><span className="fact__k">Đơn</span><span className="fact__v mono">{c.b.orders}</span></div>
          </div>
        </div>
      </div>
      <div className="caveat caveat--info" style={{ flexDirection: "column", alignItems: "stretch", gap: 6 }}>
        <span>Sẽ chuyển: <b>{c.b.orders} đơn</b>, <b>{c.b.activities} activity</b>, <b>{c.b.tasks} task</b> sang Party A.</span>
        <span style={{ color: "var(--honey-500)" }}>⚠ Party B sẽ bị ẩn (is_merged=true).</span>
        <span style={{ color: "var(--moss-500)" }}>✓ Snapshot undo được lưu tự động (party_merge_log).</span>
      </div>
      <label className="chk-row" onClick={() => setOk(!ok)}>
        <span className={"chk-box" + (ok ? " chk-box--on" : "")}>{ok && <Icon name="check" size={12} />}</span>
        <span className="chk-row__text">Tôi xác nhận muốn gộp 2 khách này.</span>
      </label>
    </Modal>
  );
}

/* ── M02 Create Party ───────────────────────────────────── */
function M02({ ctx, close, toast, nav }) {
  const [name, setName] = mUseState(ctx.prefillName || "");
  const [phone, setPhone] = mUseState("");
  const norm = phone ? "+84" + phone.replace(/^0/, "").replace(/\D/g, "") : "";
  const valid = name.trim() && phone.replace(/\D/g, "").length >= 9;
  return (
    <Modal title="Tạo khách hàng mới" onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!valid} onClick={() => { toast(`Đã tạo khách "${name}"`); close(); nav && nav({ screen: "S03", party: "p_001" }); }}>Tạo khách</Btn></>}>
      <Field label="Tên hiển thị" required><TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="Nguyễn Văn A" autoFocus /></Field>
      <Field label="Số điện thoại" required hint={norm ? null : "Nhập 0xxx hoặc +84xxx"}>
        <TextInput className="inp inp--mono" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="0901234567" />
      </Field>
      {norm && <div className="phone-prev"><Icon name="check" size={12} /> Chuẩn hóa E.164: {norm}</div>}
      <Field label="Email"><TextInput type="email" placeholder="(tùy chọn)" /></Field>
      <Field label="Ghi chú nhanh"><TextInput placeholder="(tùy chọn)" /></Field>
      <div className="modal__note"><Icon name="warn" size={14} /><span>Nếu SĐT đã tồn tại, hệ thống sẽ cảnh báo trùng (ERR-DUPLICATE-IDENTITY).</span></div>
    </Modal>
  );
}

/* ── M03 Tag Management ─────────────────────────────────── */
function M03({ ctx, close, toast, openModal }) {
  const party = window.DB.partyById(ctx.party);
  const [tagIds, setTagIds] = mUseState(party ? [...party.tags] : []);
  const [q, setQ] = mUseState("");
  const avail = window.DB.tags.filter((t) => !tagIds.includes(t.id) && t.label.toLowerCase().includes(q.toLowerCase()));
  return (
    <Modal title="Quản lý tag" sub={`Tag cho: ${party ? party.name : ""}`} onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" onClick={() => { toast("Đã lưu tag"); close(); }}>Lưu</Btn></>}>
      <Field label="Đang có"><TagChips tagIds={tagIds} editable onRemove={(id) => setTagIds(tagIds.filter((x) => x !== id))} /></Field>
      <Field label="Thêm tag">
        <TextInput value={q} onChange={(e) => setQ(e.target.value)} placeholder="🔍 Tìm hoặc tạo tag mới..." />
      </Field>
      <div className="flex-wrap">
        {avail.map((t) => (
          <button key={t.id} className="fchip" onClick={() => setTagIds([...tagIds, t.id])}><Icon name="plus" size={11} /> {t.label}</button>
        ))}
        {avail.length === 0 && <span className="muted" style={{ fontSize: 13 }}>Không có tag khớp.</span>}
      </div>
      <button className="ghost-link" onClick={() => openModal("M14", {})}><Icon name="plus" size={12} /> Tạo tag mới</button>
    </Modal>
  );
}

/* ── M04 Assign Owner ───────────────────────────────────── */
function M04({ ctx, close, toast }) {
  const party = window.DB.partyById(ctx.party);
  const [sel, setSel] = mUseState(party ? party.owner : null);
  const candidates = window.DB.users.filter((u) => ["sales", "care", "manager"].includes(u.role));
  return (
    <Modal title="Gán phụ trách" sub={party ? party.name : ""} onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!sel} onClick={() => { toast("Đã gán phụ trách"); close(); }}>Lưu</Btn></>}>
      <Field label="Phụ trách hiện tại">
        <div style={{ fontSize: 14, color: "var(--fg-1)" }}>{party && party.owner ? window.DB.userById(party.owner).short : "Chưa gán"}</div>
      </Field>
      <Field label="Chọn NV mới">
        <div className="radioset" style={{ flexDirection: "column" }}>
          {candidates.map((u) => (
            <label key={u.id} className={"radio-pill" + (sel === u.id ? " radio-pill--on" : "")} onClick={() => setSel(u.id)} style={{ justifyContent: "flex-start" }}>
              <span className="radio-pill__dot" /><Avatar user={u} size={22} /> {u.name}{party && party.owner === u.id && <span className="muted" style={{ fontSize: 11 }}>(hiện tại)</span>}
            </label>
          ))}
        </div>
      </Field>
    </Modal>
  );
}

/* ── M05 Create / Edit Task ─────────────────────────────── */
const M05_KIND_LABEL = { contact: "Liên hệ", internal: "Nội bộ", generic: "Chung" };
function M05({ ctx, close, toast }) {
  const editing = !!ctx.task;
  const t = editing ? window.DB.tasks.find((x) => x.id === ctx.task) : null;
  const prefill = ctx.prefill_title || (ctx.action ? ctx.action.rationale : (t ? t.title : ""));
  const [title, setTitle] = mUseState(prefill);
  const [due, setDue] = mUseState(t ? "2026-06-20" : "2026-06-15");
  const [prio, setPrio] = mUseState(t ? t.priority : "P2");
  const party = window.DB.partyById(ctx.party || (t && t.party));
  const past = new Date(due) < new Date("2026-06-14");

  // task_kind — auto-prefill; hide the field when the machine is CERTAIN,
  // show the selector only when ambiguous (manual + party). No render-time
  // fallback: derivation mirrors the data migration.
  const src = ctx.source || (t && t.source);
  let derivedKind = "generic", certain = true, why = "không gắn khách";
  if (ctx.action || src === "action_queue" || src === "action_queue_claim") { derivedKind = "contact"; why = "từ action_queue outreach"; }
  else if (src === "verify_account" || src === "internal") { derivedKind = "internal"; why = "nguồn nội bộ"; }
  else if (!party) { derivedKind = "generic"; why = "không gắn khách"; }
  else { derivedKind = (t && t.task_kind) || "contact"; certain = false; }
  const [kind, setKind] = mUseState(derivedKind);

  return (
    <Modal title={editing ? "Sửa task" : "Tạo task mới"} sub={ctx.source === "action_queue" ? "Prefill từ action_queue" : null} onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!title.trim()} onClick={() => { toast(editing ? "Đã cập nhật task" : "Đã tạo task"); close(); }}>Lưu task</Btn></>}>
      <Field label="Tiêu đề" required><TextInput value={title} onChange={(e) => setTitle(e.target.value)} autoFocus /></Field>
      <Field label="Khách hàng"><Select value={party ? party.id : ""} onChange={() => {}}>
        <option value="">— (không gắn)</option>
        {window.DB.parties.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
      </Select></Field>
      {certain ? (
        <div className="m05-kind-auto"><span className="m05-kind-auto__k">Loại việc</span> <b>{M05_KIND_LABEL[derivedKind]}</b> <span className="m05-kind-auto__why">· tự nhận ({why}) — ẩn field</span></div>
      ) : (
        <Field label="Loại việc" hint="Máy đoán từ ngữ cảnh — chỉnh nếu chưa đúng"><Select value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="contact">Liên hệ — launch phiên gọi</option>
          <option value="internal">Nội bộ — checklist + tool</option>
          <option value="generic">Chung — không có block khách</option>
        </Select></Field>
      )}
      <div className="field-row">
        <Field label="Due date" required error={past ? "⚠ Quá khứ — vẫn cho phép lưu" : null}><TextInput type="date" value={due} onChange={(e) => setDue(e.target.value)} className="inp inp--mono" /></Field>
        <Field label="Giờ"><TextInput type="time" defaultValue="10:00" className="inp inp--mono" /></Field>
      </div>
      <div className="field-row">
        <Field label="Priority"><Select value={prio} onChange={(e) => setPrio(e.target.value)}>
          <option value="P1">P1 — Khẩn</option><option value="P2">P2 — Cao</option><option value="P3">P3 — Thường</option><option value="P4">P4 — Thấp</option>
        </Select></Field>
        <Field label="Giao cho"><Select value={window.DB.ME} onChange={() => {}}>
          {window.DB.users.filter((u) => u.role !== "admin").map((u) => <option key={u.id} value={u.id}>{u.short}</option>)}
        </Select></Field>
      </div>
      <Field label="Ghi chú"><TextArea defaultValue={t ? t.note : ""} placeholder="(tùy chọn)" /></Field>
    </Modal>
  );
}

/* ── M06 Custom Fields Edit ─────────────────────────────── */
function M06({ ctx, close, toast }) {
  const party = window.DB.partyById(ctx.party);
  const cust = party ? party.custom : {};
  return (
    <Modal title="Chỉnh sửa thông tin bổ sung" sub={party ? party.name : ""} onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" onClick={() => { toast("Đã lưu thông tin bổ sung"); close(); }}>Lưu</Btn></>}>
      {window.DB.fieldDefs.map((fd) => (
        <Field key={fd.id} label={fd.label} required={fd.required}>
          {fd.type === "bool" ? (
            <div className="radioset">
              <label className={"radio-pill" + (cust[fd.name] === true ? " radio-pill--on" : "")}><span className="radio-pill__dot" />Có</label>
              <label className={"radio-pill" + (cust[fd.name] !== true ? " radio-pill--on" : "")}><span className="radio-pill__dot" />Không</label>
            </div>
          ) : fd.type === "select" ? (
            <Select value={cust[fd.name] || ""} onChange={() => {}}>
              <option value="">—</option>{fd.options.map((o) => <option key={o} value={o}>{o}</option>)}
            </Select>
          ) : fd.type === "date" ? (
            <TextInput type="date" defaultValue={cust[fd.name] || ""} className="inp inp--mono" />
          ) : (
            <TextInput defaultValue={cust[fd.name] || ""} placeholder="—" />
          )}
        </Field>
      ))}
    </Modal>
  );
}

/* ── M07 Create / Edit Campaign ─────────────────────────── */
function M07({ ctx, close, toast }) {
  const editing = !!ctx.campaign;
  const c = editing ? window.DB.campaignById(ctx.campaign) : null;
  const [segId, setSegId] = mUseState(c ? c.segment : (ctx.prefillSegment || "seg_2"));
  const seg = window.DB.segById(segId);
  const [name, setName] = mUseState(c ? c.name : "");
  return (
    <Modal title={editing ? "Sửa chiến dịch" : "Tạo chiến dịch mới"} onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!name.trim() || !segId} onClick={() => { toast(editing ? "Đã cập nhật chiến dịch" : "Đã tạo & kích hoạt chiến dịch"); close(); }}>{editing ? "Lưu" : "Tạo & Kích hoạt"}</Btn></>}>
      <Field label="Tên chiến dịch" required><TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="React-Jul-2026" autoFocus /></Field>
      <div className="field-row">
        <Field label="Mục tiêu" required><Select value={c ? c.objective : "reactivation"} onChange={() => {}}>
          <option value="reactivation">Reactivation</option><option value="winback">Win-back</option><option value="upsell">Upsell</option><option value="crosssell">Cross-sell</option>
        </Select></Field>
        <Field label="Kênh" required><Select value={c ? c.channel : "messenger"} onChange={() => {}}>
          <option value="messenger">Messenger</option><option value="call">Call</option><option value="email">Email</option>
        </Select></Field>
      </div>
      <Field label="Segment" required>
        <Select value={segId} onChange={(e) => setSegId(e.target.value)}>
          {window.DB.segments.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </Select>
      </Field>
      {seg && <div className="caveat caveat--rule caveat--info">→ <b style={{ color: "var(--fg)" }}>{seg.members} khách</b>{seg.excluded > 0 && <span style={{ color: "var(--honey-500)" }}>&nbsp;({seg.excluded} bị loại do consent — R1)</span>}</div>}
      <Field label="Ngày bắt đầu" required><TextInput type="date" defaultValue="2026-07-01" className="inp inp--mono" /></Field>
    </Modal>
  );
}

/* ── M08 Log Activity ───────────────────────────────────── */
const ACT_TYPES = [{ v: "call", l: "Cuộc gọi" }, { v: "note", l: "Ghi chú" }, { v: "email", l: "Email" }, { v: "visit", l: "Ghé thăm" }, { v: "chat", l: "Chat" }, { v: "other", l: "Khác" }];
function M08({ ctx, close, toast }) {
  const noteOnly = ctx.mode === "note_only" || ctx.mode === "edit";
  const party = window.DB.partyById(ctx.party);
  const [type, setType] = mUseState("call");
  const [content, setContent] = mUseState("");
  return (
    <Modal title={noteOnly ? "Ghi chú" : "Ghi log hoạt động"} sub={party ? party.name : null} onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!content.trim()} onClick={() => { toast(noteOnly ? "Đã lưu ghi chú" : "Đã ghi log hoạt động"); close(); }}>Lưu</Btn></>}>
      {!noteOnly && (
        <Field label="Loại" required>
          <div className="radioset">
            {ACT_TYPES.map((t) => <label key={t.v} className={"radio-pill" + (type === t.v ? " radio-pill--on" : "")} onClick={() => setType(t.v)}><span className="radio-pill__dot" />{t.l}</label>)}
          </div>
        </Field>
      )}
      <Field label={noteOnly ? "Nội dung ghi chú" : "Kết quả / Nội dung"} required>
        <TextArea value={content} onChange={(e) => setContent(e.target.value)} placeholder="Khách xác nhận sẽ đặt tuần tới. Gợi ý SP X, Y." autoFocus />
      </Field>
      {!noteOnly && <>
        <Field label="Đơn liên quan" hint="(tùy chọn — soft ref)"><TextInput className="inp inp--mono" defaultValue={ctx.prefillOrder || ""} placeholder="ORD-20060812" /></Field>
        <Field label="Thời gian (ICT)"><TextInput className="inp inp--mono" defaultValue="2026-06-14 10:32" /></Field>
      </>}
    </Modal>
  );
}

/* ── M09 Assign Conversation ────────────────────────────── */
function M09({ ctx, close, toast }) {
  const conv = window.DB.convById(ctx.conversation);
  const [sel, setSel] = mUseState(conv ? conv.assignee : null);
  const careUsers = window.DB.users.filter((u) => ["care", "sales"].includes(u.role));
  return (
    <Modal title="Gán NV xử lý" sub={conv ? conv.psid : ""} onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!sel} onClick={() => { toast("Đã gán NV xử lý"); close(); }}>Gán</Btn></>}>
      <Field label="NV hiện tại"><div style={{ fontSize: 14, color: "var(--fg-1)" }}>{conv && conv.assignee ? window.DB.userById(conv.assignee).short : "Chưa gán"}</div></Field>
      <Field label="Gán cho">
        <div className="radioset" style={{ flexDirection: "column" }}>
          {careUsers.map((u) => (
            <label key={u.id} className={"radio-pill" + (sel === u.id ? " radio-pill--on" : "")} onClick={() => setSel(u.id)} style={{ justifyContent: "flex-start" }}>
              <span className="radio-pill__dot" /><Avatar user={u} size={22} /> {u.name}
            </label>
          ))}
        </div>
      </Field>
    </Modal>
  );
}

/* ── M10 Close Conversation ─────────────────────────────── */
function M10({ ctx, close, toast }) {
  const conv = window.DB.convById(ctx.conversation);
  const linked = conv && conv.party;
  const [log, setLog] = mUseState(!!linked);
  const [txt, setTxt] = mUseState("");
  return (
    <Modal title="Đóng hội thoại" sub={linked ? window.DB.partyById(conv.party).name : conv && conv.psid} onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" onClick={() => { toast("Đã đóng hội thoại"); close(); }}>Đóng hội thoại</Btn></>}>
      <Field label="Kết quả xử lý"><TextArea value={txt} onChange={(e) => setTxt(e.target.value)} placeholder="Đã giải quyết thắc mắc về đơn hàng" autoFocus /></Field>
      {linked && (
        <label className="chk-row" onClick={() => setLog(!log)}>
          <span className={"chk-box" + (log ? " chk-box--on" : "")}>{log && <Icon name="check" size={12} />}</span>
          <span className="chk-row__text">Ghi vào activity timeline của khách (type=chat).</span>
        </label>
      )}
    </Modal>
  );
}

/* ── M11 Link Party to Conversation ─────────────────────── */
function M11({ ctx, close, toast, openModal }) {
  const conv = window.DB.convById(ctx.conversation);
  const [q, setQ] = mUseState("");
  const [sel, setSel] = mUseState(null);
  const results = q.trim() ? window.DB.parties.filter((p) => p.name.toLowerCase().includes(q.toLowerCase()) || p.phone.includes(q)) : window.DB.parties.slice(0, 4);
  return (
    <Modal title="Gắn khách vào hội thoại" sub={`Tìm khách cho: ${conv ? conv.psid : ""}`} onClose={close} width={520}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!sel} onClick={() => { toast("Đã gắn khách vào hội thoại"); close(); }}>Gắn khách đã chọn</Btn></>}>
      <Field><TextInput value={q} onChange={(e) => setQ(e.target.value)} placeholder="🔍 Tìm theo SĐT, tên, email..." autoFocus /></Field>
      <div className="cand-list" style={{ maxHeight: 240, overflowY: "auto" }}>
        {results.map((p) => (
          <div key={p.id} className={"cand-row" + (sel === p.id ? " cand-row--active" : "")} onClick={() => setSel(p.id)}>
            <div className="row-between">
              <span style={{ fontSize: 14, color: "var(--fg)" }}>{p.name}</span>
              <GroupBadge group={p.group} />
            </div>
            <div className="mono" style={{ fontSize: 12, color: "var(--fg-muted)" }}>{p.phone} · {p.status}</div>
          </div>
        ))}
        {results.length === 0 && <div className="state" style={{ minHeight: 120 }}><div className="state__inner"><div className="state__sub">Không tìm thấy khách.</div></div></div>}
      </div>
      <button className="ghost-link" onClick={() => openModal("M02", { prefillName: q })}><Icon name="plus" size={12} /> Tạo khách mới</button>
    </Modal>
  );
}

/* ── M12 Record Conversion ──────────────────────────────── */
function M12({ ctx, close, toast }) {
  const target = ctx.target;
  const party = window.DB.partyById(target.party);
  const [code, setCode] = mUseState("");
  const [manual, setManual] = mUseState(false);
  const found = code.startsWith("ORD-") && code.length >= 10;
  return (
    <Modal title="Ghi nhận chuyển đổi" sub={party ? party.name : ""} onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!found && !manual} onClick={() => { toast("Đã ghi nhận chuyển đổi"); close(); }}>Ghi nhận</Btn></>}>
      <Field label="Chiến dịch"><div style={{ fontSize: 14, color: "var(--fg-1)" }}>{ctx.campaignName || "Win-back Q3"}</div></Field>
      <Field label="Mã đơn hàng" required error={code && !found ? "Không tìm thấy trong wh_order_hdr" : null}>
        <TextInput className="inp inp--mono" value={code} onChange={(e) => setCode(e.target.value)} placeholder="ORD-20060901" disabled={manual} />
      </Field>
      {found && <div className="phone-prev"><Icon name="check" size={12} /> Doanh thu: {fmtVND(3200000)} (từ wh_order_hdr)</div>}
      <label className="chk-row" onClick={() => setManual(!manual)}>
        <span className={"chk-box" + (manual ? " chk-box--on" : "")}>{manual && <Icon name="check" size={12} />}</span>
        <span className="chk-row__text">Đơn chưa có trong warehouse — ghi nhận thủ công.</span>
      </label>
      {manual && <Field label="Doanh thu ước tính"><TextInput className="inp inp--mono" placeholder="2.000.000" /></Field>}
    </Modal>
  );
}

/* ── M13 Custom Field Definition ────────────────────────── */
function M13({ ctx, close, toast }) {
  const [type, setType] = mUseState("bool");
  const [name, setName] = mUseState("");
  const [label, setLabel] = mUseState("");
  return (
    <Modal title="Định nghĩa custom field" onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!name.trim() || !label.trim()} onClick={() => { toast("Đã lưu custom field"); close(); }}>Lưu</Btn></>}>
      <Field label="Field name (slug)" required><TextInput className="inp inp--mono" value={name} onChange={(e) => setName(e.target.value.replace(/\s+/g, "_").toLowerCase())} placeholder="da_nhay_cam" autoFocus /></Field>
      <Field label="Nhãn hiển thị" required><TextInput value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Da nhạy cảm" /></Field>
      <Field label="Loại dữ liệu" required>
        <Select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="text">Text</option><option value="number">Number</option><option value="date">Date</option>
          <option value="bool">Boolean (Có/Không)</option><option value="select">Select</option><option value="multiselect">Multi-select</option>
        </Select>
      </Field>
      <Field label="Bắt buộc">
        <div className="radioset"><label className="radio-pill"><span className="radio-pill__dot" />Có</label><label className="radio-pill radio-pill--on"><span className="radio-pill__dot" />Không</label></div>
      </Field>
      {(type === "select" || type === "multiselect") && (
        <Field label="Tùy chọn"><button className="fchip"><Icon name="plus" size={11} /> Thêm tùy chọn</button></Field>
      )}
    </Modal>
  );
}

/* ── M14 Create Tag ─────────────────────────────────────── */
function M14({ ctx, close, toast }) {
  const [name, setName] = mUseState("");
  const [label, setLabel] = mUseState("");
  const [tone, setTone] = mUseState("default");
  const tones = [{ v: "moss", l: "Xanh" }, { v: "coral", l: "Đỏ" }, { v: "amber", l: "Vàng" }, { v: "default", l: "Trung tính" }];
  return (
    <Modal title="Tạo tag mới" onClose={close}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!name.trim() || !label.trim()} onClick={() => { toast(`Đã tạo tag "${label}"`); close(); }}>Tạo tag</Btn></>}>
      <Field label="Tag name (slug)" required><TextInput className="inp inp--mono" value={name} onChange={(e) => setName(e.target.value.replace(/\s+/g, "-").toLowerCase())} placeholder="vip-repeat" autoFocus /></Field>
      <Field label="Nhãn hiển thị" required><TextInput value={label} onChange={(e) => setLabel(e.target.value)} placeholder="VIP Repeat" /></Field>
      <Field label="Category"><TextInput placeholder="customer-segment" /></Field>
      <Field label="Màu (tùy chọn)">
        <div className="radioset">{tones.map((t) => <label key={t.v} className={"radio-pill" + (tone === t.v ? " radio-pill--on" : "")} onClick={() => setTone(t.v)}><span className="radio-pill__dot" />{t.l}</label>)}</div>
      </Field>
    </Modal>
  );
}

/* ── O01 Confirm overlay ────────────────────────────────── */
function O01({ ctx, close, toast }) {
  const map = {
    delete_note: { title: "Xóa ghi chú này?", sub: "Hành động không thể hoàn tác." },
    delete_field: { title: "Xóa custom field?", sub: "Giá trị field này sẽ ẩn khỏi mọi hồ sơ." },
  };
  const m = map[ctx.confirm_type] || { title: "Xác nhận?", sub: "" };
  return (
    <Modal title={m.title} onClose={close} width={400}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" onClick={() => { toast("Đã xóa"); close(); }}><Icon name="trash" size={14} /> Xóa</Btn></>}>
      <div className="modal__note" style={{ fontSize: 14 }}><Icon name="warn" size={16} /><span>{m.sub}</span></div>
    </Modal>
  );
}

/* ── Toast stack ────────────────────────────────────────── */
function ToastStack({ toasts }) {
  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <div key={t.id} className="toast"><span className={"toast__dot" + (t.kind === "info" ? " toast__dot--info" : "")} />{t.msg}</div>
      ))}
    </div>
  );
}

const MODALS = { M01, M02, M03, M04, M05, M06, M07, M08, M09, M10, M11, M12, M13, M14, O01 };
Object.assign(window, { MODALS, ToastStack });

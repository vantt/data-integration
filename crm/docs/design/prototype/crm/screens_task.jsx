/* ============================================================
   Screen: S15 — Task Detail   (route /tasks/{task_id})
   Task = cam kết bền vững (nhiều ngày / nhiều cuộc gọi). S15 sở hữu
   VÒNG ĐỜI task và định tuyến thực thi theo task_kind:
     contact  → provenance + khách + "Vào phiên gọi" (launch S14, phiên
                customer-grained dùng chung — KHÔNG nhúng cockpit riêng)
     internal → facts khách tối thiểu + checklist + tool CTAs
     generic  → mô tả + checklist + links + ghi chú (không có block khách)
   task_kind đọc thẳng từ crm_task (đã backfill bằng migration) — KHÔNG
   suy lại lúc render. Lifecycle: open → doing → done → cancelled.
   ============================================================ */
const { useState: tUseState, useEffect: tUseEffect } = React;

const KIND_META = {
  contact: { label: "Liên hệ", tone: "amber", icon: "phone" },
  internal: { label: "Nội bộ", tone: "moss", icon: "settings" },
  generic: { label: "Chung", tone: "default", icon: "doc" },
};
const T_STATUS = {
  open: { label: "Đang mở", cls: "" },
  doing: { label: "Đang làm", cls: "warn" },
  done: { label: "Hoàn thành", cls: "good" },
  cancelled: { label: "Đã huỷ", cls: "bad" },
};
const LIFECYCLE = ["open", "doing", "done"];

function taskOverdue(t) {
  if (t.status === "done" || t.status === "cancelled") return null;
  const p = window.ictParts(t.due);
  // demo "now" = 14/06/2026 ICT
  const dueNum = +(p.yyyy + p.mm + p.dd);
  const nowNum = 20260614;
  if (dueNum < nowNum) {
    const days = Math.max(1, Math.round((new Date("2026-06-14") - new Date(p.yyyy + "-" + p.mm + "-" + p.dd)) / 864e5));
    return days;
  }
  return null;
}

/* channel a contact attempt happened on */
function attemptIcon(ch) { return ch === "zalo" || ch === "chat" ? "inbox" : ch === "email" ? "doc" : "phone"; }

/* ── Value of a task (for provenance) ───────────────────── */
function taskValue(task, party) {
  if (!party) return 0;
  if (task.claim_action_ids) {
    return task.claim_action_ids.reduce((s, id) => {
      const a = party.actions.find((x) => x.action_id === id);
      return s + (a ? a.value : 0);
    }, 0);
  }
  const a = party.actions.find((x) => x.action_id === task.source_ref);
  return a ? a.value : 0;
}
function taskReason(task, party) {
  if (!party) return null;
  const a = party.actions.find((x) => x.action_id === task.source_ref);
  return a ? a.rationale : null;
}

/* ── Lifecycle stepper ──────────────────────────────────── */
function LifecycleRail({ status }) {
  if (status === "cancelled") {
    return (
      <div className="s15-life s15-life--cancelled">
        {LIFECYCLE.map((s, i) => (
          <React.Fragment key={s}>
            {i > 0 && <span className="s15-life__bar" />}
            <span className="s15-step s15-step--muted">{T_STATUS[s].label}</span>
          </React.Fragment>
        ))}
        <span className="s15-life__bar" />
        <span className="s15-step s15-step--cancel">✕ Đã huỷ</span>
      </div>
    );
  }
  const curIdx = LIFECYCLE.indexOf(status);
  return (
    <div className="s15-life">
      {LIFECYCLE.map((s, i) => {
        const state = i < curIdx ? "past" : i === curIdx ? "cur" : "future";
        return (
          <React.Fragment key={s}>
            {i > 0 && <span className={"s15-life__bar" + (i <= curIdx ? " s15-life__bar--on" : "")} />}
            <span className={"s15-step s15-step--" + state}>
              <span className="s15-step__dot">{state === "past" ? <Icon name="check" size={11} /> : null}</span>
              {T_STATUS[s].label}
            </span>
          </React.Fragment>
        );
      })}
    </div>
  );
}

/* ── Checklist (client-side toggles) ────────────────────── */
function Checklist({ items, onToggle, readOnly }) {
  const done = items.filter((i) => i.done).length;
  return (
    <div className="s15-block">
      <div className="s15-block__head">
        <span className="s15-block__label"><Icon name="check" size={12} /> Checklist</span>
        <span className="s15-block__count mono">{done}/{items.length}</span>
      </div>
      <div className="s15-checklist">
        {items.map((it, i) => (
          <button key={i} className={"s15-checkitem" + (it.done ? " s15-checkitem--on" : "")} onClick={() => !readOnly && onToggle(i)} disabled={readOnly}>
            <span className={"s15-checkbox" + (it.done ? " s15-checkbox--on" : "")}>{it.done && <Icon name="check" size={12} />}</span>
            <span className="s15-checkitem__text">{it.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── Activity log (merge task.log + attempts) ───────────── */
function TaskActivityLog({ task }) {
  const entries = [];
  (task.log || []).forEach((l) => entries.push(l));
  entries.sort((a, b) => (a.at < b.at ? 1 : -1));
  return (
    <div className="s15-section">
      <div className="s15-section__head"><Icon name="clock" size={13} /> Nhật ký hoạt động</div>
      {entries.length === 0 ? (
        <div className="s15-log-empty">Chưa có hoạt động nào gắn task này. Log qua M08 sẽ mang <span className="mono">task_id</span> và hiện ở đây.</div>
      ) : (
        <div className="s15-timeline">
          {entries.map((e, i) => (
            <div key={i} className="s15-tl-row">
              <span className={"s15-tl-dot s15-tl-dot--" + (e.kind || "note")} />
              <div className="s15-tl-main">
                <div className="s15-tl-top">
                  <span className="s15-tl-kind">{e.kind === "outcome" ? "Kết quả" : e.kind === "attempt" ? "Thử liên lạc" : e.kind === "system" ? "Hệ thống" : "Ghi chú"}</span>
                  <span className="s15-tl-time mono">{window.fmtDateTime(e.at)} ICT</span>
                  {e.user && <span className="s15-tl-user">· {window.DB.userById(e.user)?.short}</span>}
                </div>
                <div className="s15-tl-text">{e.text}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── BODY: contact ──────────────────────────────────────── */
function BodyContact({ task, party, nav, toast }) {
  const val = taskValue(task, party);
  const reason = taskReason(task, party);
  const isClaim = !!task.claim_action_ids;
  const claimActions = isClaim ? task.claim_action_ids.map((id) => party.actions.find((a) => a.action_id === id)).filter(Boolean) : [];
  const otherContactTasks = window.DB.contactTasksForParty(party.id).filter((t) => t.id !== task.id);
  const prefChannel = party.zalo ? "Zalo" : "Gọi điện";

  const joinCall = () => nav({ screen: "S14", party: party.id, taskCtx: task.id });

  return (
    <>
      {/* PROVENANCE */}
      <div className="s15-section">
        <div className="s15-section__head"><Icon name="bolt" size={13} /> Xuất xứ &amp; lý do</div>
        <div className="s15-prov">
          <div className="s15-prov__row">
            <span className="s15-prov__k">Nguồn</span>
            <span className="s15-prov__v">
              {task.source === "action_queue_claim" ? "action_queue (gộp claim)" : task.source === "action_queue" ? "action_queue" : "thủ công"}
              {task.source_ref && <span className="mono s15-prov__ref"> · {task.source_ref}</span>}
              {isClaim && <span className="mono s15-prov__ref"> · {task.claim_action_ids.join(" + ")}</span>}
            </span>
          </div>
          {reason && <div className="s15-prov__row"><span className="s15-prov__k">Lý do</span><span className="s15-prov__v s15-prov__v--em">"{reason}"</span></div>}
          {val > 0 && <div className="s15-prov__row"><span className="s15-prov__k">Giá trị ước tính</span><span className="s15-prov__v mono s15-prov__v--val">{window.fmtVND(val)}</span></div>}
        </div>

        {isClaim && (
          <div className="s15-claim">
            <div className="s15-claim__label">{claimActions.length} action được gộp — xử lý tất cả trong một phiên gọi</div>
            {claimActions.map((a) => {
              const m = window.ACTION_META[a.type] || { label: a.type, tone: "default" };
              return (
                <div key={a.action_id} className="s15-claim__row">
                  <Chip tone={m.tone}>{m.label}</Chip>
                  <span className="s15-claim__why">{a.rationale}</span>
                  {a.value > 0 && <span className="s15-claim__val mono">{window.fmtVNDShort(a.value)}</span>}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* KHÁCH HÀNG + launch */}
      <div className="s15-section">
        <div className="s15-section__head"><Icon name="user" size={13} /> Khách hàng</div>
        <div className="s15-cust">
          <span className="s15-cust__avatar">{party.name.trim().split(/\s+/).slice(-1)[0].slice(0, 1).toUpperCase()}</span>
          <div className="s15-cust__main">
            <div className="s15-cust__row">
              <span className="s15-cust__name">{party.name}</span>
              <GroupBadge group={party.group} />
              <StatusBadge status={party.status} />
            </div>
            <div className="s15-cust__meta mono">
              <span><Icon name="phone" size={12} /> {party.phone}</span>
              <span className="s15-cust__sep">·</span>
              <span>Kênh ưu tiên: {prefChannel}</span>
            </div>
          </div>
          <button className="btn btn--ghost" onClick={() => nav({ screen: "S03", party: party.id })} style={{ padding: "8px 12px" }}>360 <Icon name="chevron" size={12} /></button>
        </div>

        <div className="s15-launch">
          <button className="btn btn--primary s15-launch__btn" onClick={joinCall}>
            <Icon name="phone" size={15} /> Vào phiên gọi
          </button>
          <div className="s15-launch__note">
            Mở phiên gọi <b>chung của khách</b> — xử lý cùng {otherContactTasks.length > 0 ? <b>{otherContactTasks.length} việc liên hệ khác</b> : "các việc khác"} trong một phiên. Task này được ghim làm lý do chính; outcome sẽ đồng bộ lại <span className="mono">task.status</span>.
          </div>
        </div>
      </div>

      {/* LỊCH SỬ THỬ LIÊN LẠC */}
      <div className="s15-section">
        <div className="s15-section__head"><Icon name="clock" size={13} /> Lịch sử thử liên lạc</div>
        {(task.attempts || []).length === 0 ? (
          <div className="s15-log-empty">Chưa có lần thử liên lạc nào cho task này.</div>
        ) : (
          <div className="s15-attempts">
            {task.attempts.map((a, i) => (
              <div key={i} className="s15-attempt">
                <span className="s15-attempt__icon"><Icon name={attemptIcon(a.channel)} size={13} /></span>
                <span className="s15-attempt__time mono">{window.fmtDateTime(a.at)}</span>
                <span className="s15-attempt__ch">{a.channel === "zalo" ? "Zalo" : a.channel === "email" ? "Email" : "Cuộc gọi"}</span>
                <span className="s15-attempt__result">{a.result}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

/* ── BODY: internal ─────────────────────────────────────── */
function BodyInternal({ task, party, nav, openModal, checklist, onToggle, readOnly }) {
  return (
    <>
      {party && (
        <div className="s15-section">
          <div className="s15-section__head"><Icon name="user" size={13} /> Facts khách (tối thiểu)</div>
          <div className="s15-cust">
            <span className="s15-cust__avatar">{party.name.trim().split(/\s+/).slice(-1)[0].slice(0, 1).toUpperCase()}</span>
            <div className="s15-cust__main">
              <div className="s15-cust__row">
                <span className="s15-cust__name">{party.name}</span>
                <GroupBadge group={party.group} />
              </div>
              <div className="s15-cust__meta mono">
                <span><Icon name="phone" size={12} /> {party.phone}</span>
                <span className="s15-cust__sep">·</span>
                <span>LTV {window.fmtVNDShort(party.insight.monetary)}</span>
              </div>
            </div>
          </div>
          <div className="s15-tools">
            <button className="btn btn--secondary" style={{ padding: "8px 12px" }} onClick={() => nav({ screen: "S03", party: party.id })}><Icon name="external" size={13} /> Xem 360</button>
            <button className="btn btn--secondary" style={{ padding: "8px 12px" }} onClick={() => openModal("M06", { party: party.id })}><Icon name="edit" size={13} /> Sửa thông tin</button>
            <button className="btn btn--secondary" style={{ padding: "8px 12px" }} onClick={() => openModal("M03", { party: party.id })}><Icon name="tag" size={13} /> Thêm tag</button>
          </div>
        </div>
      )}

      {task.description && (
        <div className="s15-section">
          <div className="s15-section__head"><Icon name="doc" size={13} /> Mô tả</div>
          <p className="s15-desc">{task.description}</p>
        </div>
      )}

      {checklist.length > 0 && <div className="s15-section"><Checklist items={checklist} onToggle={onToggle} readOnly={readOnly} /></div>}

      <div className="s15-section">
        <div className="s15-section__head"><Icon name="edit" size={13} /> Ghi chú nội bộ</div>
        <textarea className="inp inp--area s15-notes" placeholder="Ghi chú xử lý…" defaultValue={task.note} disabled={readOnly} />
      </div>
    </>
  );
}

/* ── BODY: generic ──────────────────────────────────────── */
function BodyGeneric({ task, checklist, onToggle, readOnly }) {
  return (
    <>
      {task.description && (
        <div className="s15-section">
          <div className="s15-section__head"><Icon name="doc" size={13} /> Mô tả</div>
          <p className="s15-desc">{task.description}</p>
        </div>
      )}
      {checklist.length > 0 && <div className="s15-section"><Checklist items={checklist} onToggle={onToggle} readOnly={readOnly} /></div>}
      {(task.links || []).length > 0 && (
        <div className="s15-section">
          <div className="s15-section__head"><Icon name="link" size={13} /> Links</div>
          <div className="s15-links">
            {task.links.map((l, i) => (
              <a key={i} className="s15-link" href={l.url} target="_blank" rel="noreferrer">
                <Icon name="external" size={13} /> <span>{l.label}</span>
              </a>
            ))}
          </div>
        </div>
      )}
      <div className="s15-section">
        <div className="s15-section__head"><Icon name="edit" size={13} /> Ghi chú</div>
        <textarea className="inp inp--area s15-notes" placeholder="Ghi chú…" defaultValue={task.note} disabled={readOnly} />
      </div>
    </>
  );
}

/* ── S15 — Task Detail ──────────────────────────────────── */
function S15_TaskDetail({ route, nav, openModal, toast }) {
  const taskId = route.task || window.DB.tasks[0].id;
  const task = window.DB.taskById(taskId);

  const [loading, setLoading] = tUseState(true);
  const [status, setStatus] = tUseState(task ? task.status : "open");
  const [checklist, setChecklist] = tUseState(task && task.checklist ? task.checklist.map((c) => ({ ...c })) : []);
  const [closeNote, setCloseNote] = tUseState("");

  tUseEffect(() => {
    setLoading(true);
    setStatus(task ? task.status : "open");
    setChecklist(task && task.checklist ? task.checklist.map((c) => ({ ...c })) : []);
    setCloseNote("");
    const t = setTimeout(() => setLoading(false), 340);
    return () => clearTimeout(t);
  }, [taskId]);

  const back = () => nav({ screen: "S07" });

  if (loading) {
    return (
      <div className="crm-page page-enter">
        <div className="s15-skel s15-skel--head" />
        <div className="s15-skel" style={{ height: 56 }} />
        <div className="s15-skel" style={{ height: 220 }} />
      </div>
    );
  }

  if (!task) {
    return (
      <div className="crm-page page-enter">
        <EmptyState icon="tasks" title="Không tìm thấy task" sub="Task không tồn tại hoặc đã bị xoá." cta={<button className="btn btn--secondary" onClick={back}>Về bảng Tasks</button>} />
      </div>
    );
  }

  const party = task.party ? window.DB.partyById(task.party) : null;
  const kind = KIND_META[task.task_kind] || KIND_META.generic;
  const overdue = taskOverdue(task);
  const st = T_STATUS[status];
  const readOnly = status === "done" || status === "cancelled";

  const setDoing = () => { task.status = "doing"; setStatus("doing"); toast("Task → đang làm", "info"); };
  const cancel = () => { task.status = "cancelled"; setStatus("cancelled"); toast("Đã huỷ task", "info"); };
  const reopen = () => { task.status = "open"; setStatus("open"); toast("Đã mở lại task", "info"); };
  const complete = () => {
    task.status = "done"; setStatus("done");
    openModal("M08", { party: task.party, task_id: task.id, mode: "log" });
    toast("Ghi log & hoàn thành task", "success");
  };
  const toggleCheck = (i) => setChecklist((cl) => cl.map((c, idx) => idx === i ? { ...c, done: !c.done } : c));

  return (
    <div className="crm-page page-enter s15-page">
      {/* HEADER */}
      <div className="s15-head">
        <button className="c360-back" onClick={back}><Icon name="back" size={14} /> Tasks</button>
        <div className="s15-head__main">
          <div className="s15-head__titlerow">
            <h1 className="s15-title">{task.title}</h1>
            <span className={"s15-kind s15-kind--" + kind.tone}><Icon name={kind.icon} size={11} /> {kind.label}</span>
            <span className={"prio prio--" + task.priority}>{task.priority}</span>
            {overdue && <span className="s15-overdue"><Icon name="warn" size={11} /> Quá hạn {overdue} ngày</span>}
          </div>
          <div className="s15-head__meta">
            <Bdg tone={st.cls} dot>{st.label}</Bdg>
            <span className="s15-meta__item"><Icon name="clock" size={12} /> Đến hạn: <b>{window.fmtDate(task.due)}</b></span>
            <span className="s15-meta__item"><Avatar user={task.assignee} size={20} /> {window.DB.userById(task.assignee)?.short}</span>
            {party && <button className="s15-meta__party" onClick={() => nav({ screen: "S03", party: party.id })}>{party.name} <Icon name="external" size={11} /></button>}
          </div>
        </div>
      </div>

      {/* status banners */}
      {status === "done" && <div className="s15-banner s15-banner--done"><Icon name="check" size={14} /> Task đã hoàn thành — chỉ đọc. Nhật ký vẫn hiển thị bên dưới.</div>}
      {status === "cancelled" && <div className="s15-banner s15-banner--cancel"><Icon name="close" size={14} /> Task đã huỷ. <button className="s15-banner__link" onClick={reopen}>Mở lại</button></div>}

      {/* LIFECYCLE */}
      <div className="s15-lifebar">
        <LifecycleRail status={status} />
        {!readOnly && (
          <div className="s15-life__acts">
            {status === "open" && <button className="btn btn--secondary" style={{ padding: "8px 12px" }} onClick={setDoing}><Icon name="bolt" size={13} /> Bắt đầu</button>}
            <button className="btn btn--ghost" style={{ padding: "8px 12px" }} onClick={() => openModal("M05", { task: task.id })}><Icon name="edit" size={13} /> Sửa</button>
            <button className="btn btn--ghost" style={{ padding: "8px 12px" }} onClick={() => openModal("O03", { task: task.id })}><Icon name="clock" size={13} /> Hoãn</button>
            <button className="btn btn--ghost s15-cancel" style={{ padding: "8px 12px" }} onClick={cancel}><Icon name="close" size={13} /> Huỷ</button>
          </div>
        )}
      </div>

      {/* BODY by task_kind */}
      <div className="s15-body">
        {task.task_kind === "contact" && party && <BodyContact task={task} party={party} nav={nav} toast={toast} />}
        {task.task_kind === "internal" && <BodyInternal task={task} party={party} nav={nav} openModal={openModal} checklist={checklist} onToggle={toggleCheck} readOnly={readOnly} />}
        {task.task_kind === "generic" && <BodyGeneric task={task} checklist={checklist} onToggle={toggleCheck} readOnly={readOnly} />}

        <TaskActivityLog task={task} />
      </div>

      {/* CLOSE BAR (sticky) */}
      {!readOnly && (
        <div className="s15-closebar">
          <input className="s15-closebar__note" value={closeNote} onChange={(e) => setCloseNote(e.target.value)} placeholder="Ghi chú nhanh khi đóng task…" />
          <button className="btn btn--primary" onClick={complete}><Icon name="check" size={14} /> Ghi log &amp; hoàn thành</button>
        </div>
      )}
    </div>
  );
}

/* ── O03 — Postpone Task Overlay (modal--sm) ────────────── */
function O03_Postpone({ ctx, close, toast }) {
  const task = window.DB.taskById(ctx.task);
  const p = task ? window.ictParts(task.due) : { yyyy: "2026", mm: "06", dd: "20" };
  const [date, setDate] = tUseState(task ? `${p.yyyy}-${p.mm}-${p.dd}` : "2026-06-20");
  const [time, setTime] = tUseState("10:00");
  return (
    <Modal title="Hoãn task" sub={task ? task.title : null} onClose={close} width={380}
      actions={<><CancelBtn onClick={close} /><Btn kind="primary" disabled={!date} onClick={() => {
        if (task) { task.due = new Date(`${date}T${time}:00+07:00`).toISOString(); if (task.status === "doing") task.status = "open"; }
        toast("Đã hoãn task đến " + date, "info"); close();
      }}>Xác nhận</Btn></>}>
      <div className="field-row">
        <Field label="Hoãn đến ngày" required><TextInput type="date" value={date} onChange={(e) => setDate(e.target.value)} className="inp inp--mono" /></Field>
        <Field label="Giờ"><TextInput type="time" value={time} onChange={(e) => setTime(e.target.value)} className="inp inp--mono" /></Field>
      </div>
      <div className="modal__note"><Icon name="clock" size={13} /> Nếu task đang <b>doing</b> sẽ reset về <b>open</b>. Nhật ký tự ghi mục "hoãn" (không mở M08).</div>
    </Modal>
  );
}

window.S15_TaskDetail = S15_TaskDetail;
if (window.MODALS) window.MODALS.O03 = O03_Postpone;

/* ============================================================
   Screen: S14 — Call Mode / Strategy Cockpit  (v2 contract)
   Operating console for a Sales Rep DURING a call. Three phases:
   TRƯỚC gọi (ai / vì sao / cảnh giác) → TRONG khi nói (talk-track /
   điểm nói / xử lý từ chối) → SAU cúp máy (log outcome / hẹn lại).

   Spatial split (contract §Layout):
     LEFT  main = "NÓI GÌ" (hot path, tick khi nói)
     RIGHT rail = "VÌ SAO & BỐI CẢNH" (đọc trước khi quay số):
                  reason-to-call queue · snapshot · collect còn thiếu
   Reads cache.wh_approach_script (R2 — no recompute, show refreshed_at).
   recommended=false → STOP state (R14). Ticks/collect are client-side
   only (contract §9 INVARIANT). No C01 sidebar (shell hides it).
   ============================================================ */
const { useState: cUseState, useEffect: cUseEffect, useMemo: cUseMemo } = React;

/* mask a phone like +84983xxxxx35 → 0983****35 */
function maskPhone(raw) {
  if (!raw) return "—";
  const local = raw.replace(/^\+?84/, "0").replace(/\D/g, "");
  if (local.length < 6) return local;
  return local.slice(0, 4) + "****" + local.slice(-2);
}

const CONF_META = {
  high: { label: "cao", tone: "good" },
  medium: { label: "vừa", tone: "warn" },
  low: { label: "thấp", tone: "bad" }
};

/* ── Alert-row derivation (contract §alert_row / impl §6) ──
   Issues to discover, as short chips. Grounded in cache/CRM fields:
   customer_status · cancel_risk · discount_sens · phone2 invalid ·
   consent (R1) · low confidence. */
function deriveAlerts(party, script) {
  const ins = party.insight || {};
  const out = [];
  if (party.status === "at_risk")
  out.push({ label: `sắp churn ${ins.recency_days}d`, tone: "warn" });else
  if (party.status === "churned")
  out.push({ label: `đã churn ${ins.recency_days}d`, tone: "bad" });
  if (party.cancel_risk != null && party.cancel_risk >= 0.25)
  out.push({ label: `hủy đơn ${Math.round(party.cancel_risk * 100)}%`, tone: "warn" });
  if (ins.discount_sens === "HIGH")
  out.push({ label: "nhạy giảm giá cao", tone: "warn" });
  if (party.phone2 && party.phone2_status === "invalid")
  out.push({ label: "SĐT phụ lỗi", tone: "bad" });
  if (script && script.confidence === "low")
  out.push({ label: "độ tin thấp", tone: "warn" });
  // consent chip always present — R1 (warn-only, never blocks call/zalo)
  out.push(party.consent ?
  { label: "consent: OK", tone: "good" } :
  { label: "chưa có consent (R1)", tone: "bad" });
  return out;
}

/* ── Collect derivation (contract §collect / impl §5) ──
   "Missing" contact/profile the rep can grab mid-call. Channel/date
   rows save inline (client swap → ✓ đã lưu, ST-CALL-COLLECT-DONE);
   invalid SĐT / địa chỉ route to an edit modal. */
function deriveCollect(party) {
  const rows = [];
  if (!party.zalo)
  rows.push({ key: "zalo", label: "Zalo", kind: "channel", ph: "Số / username Zalo" });
  if (!(party.custom && party.custom.facebook))
  rows.push({ key: "facebook", label: "Facebook", kind: "channel", ph: "Link / tên FB" });
  if (!party.email)
  rows.push({ key: "email", label: "Email", kind: "channel", ph: "email@..." });
  if (!(party.custom && party.custom.ngay_sinh))
  rows.push({ key: "birthday", label: "Sinh nhật", kind: "date", ph: "dd/mm/yyyy" });
  if (party.phone2 && party.phone2_status === "invalid")
  rows.push({ key: "fix_phone", label: "SĐT phụ lỗi", kind: "fix", sub: maskPhone(party.phone2) });
  return rows;
}

/* ── Region heading strip ───────────────────────────────── */
function S14Head({ children, right, icon }) {
  return (
    <div className="s14-rhead">
      <span className="s14-rhead__label">{icon && <span className="s14-rhead__ico"><Icon name={icon} size={12} /></span>}{children}</span>
      {right && <span className="s14-rhead__right">{right}</span>}
    </div>);

}

/* ── Objection card (expand/collapse) ───────────────────── */
function ObjectionCard({ obj, open, onToggle }) {
  return (
    <div className={"s14-obj" + (open ? " s14-obj--open" : "")}>
      <button className="s14-obj__q" onClick={onToggle} aria-expanded={open}>
        <span className="s14-obj__chev"><Icon name="chevron" size={13} /></span>
        <span className="s14-obj__qtext">"{obj.q}"</span>
        <span className="s14-obj__hint">{open ? "thu gọn" : "xem câu trả lời"}</span>
      </button>
      {open && <div className="s14-obj__a">{obj.a}</div>}
    </div>);

}

/* ── Reason-to-call model (RIGHT rail · read-context) ─────
   Cockpit is CUSTOMER-grained: one session resolves MANY reasons.
   Reasons unify (a) action-queue items and (b) open/doing CONTACT-TASKS
   for this party. An item backed by a contact-task carries `task` — its
   outcome updates task.status (one source of truth, synced with S15).
   PRIMARY = ripest call trigger (or the task pinned when launched from
   S15); SECONDARY = "tranh thủ nếu thuận". Tick = client-side. */
function buildReasons(party, taskCtx) {
  const contactTasks = window.DB.contactTasksForParty(party.id);
  const taskForAction = (aid) => contactTasks.find((t) => t.source_ref === aid || (t.claim_action_ids || []).includes(aid)) || null;
  const items = [];
  (party.actions || []).forEach((a) => {
    items.push({ key: a.action_id, kind: "action", type: a.type, rationale: a.rationale, value: a.value, task: taskForAction(a.action_id) });
  });
  // manual contact-tasks not tied to any action in the queue
  contactTasks.forEach((t) => {
    const tied = (t.source_ref && (party.actions || []).some((a) => a.action_id === t.source_ref)) || (t.claim_action_ids || []).length > 0;
    if (!tied) items.push({ key: t.id, kind: "task", type: "TASK", rationale: t.title, value: 0, task: t });
  });
  let primaryKey = null;
  if (taskCtx) {
    const hit = items.find((it) => it.task && it.task.id === taskCtx.id);
    primaryKey = hit ? hit.key : items[0] && items[0].key;
  } else {
    primaryKey = items[0] && items[0].key;
  }
  items.forEach((it) => { it.primary = it.key === primaryKey; });
  items.sort((a, b) => (b.primary - a.primary) || (b.value - a.value));
  return items;
}

function ReasonCard({ reason, primary, said, onSaid, onSchedule, onAsync }) {
  const m = reason.kind === "task" ? { label: "TASK", tone: "default" } : (window.ACTION_META[reason.type] || { label: reason.type, tone: "default" });
  return (
    <div className={"s14-reason" + (said ? " s14-reason--said" : "") + (primary ? " s14-reason--primary" : "")}>
      <label className="s14-reason__check" title={said ? "Đánh dấu chưa nói" : "Đánh dấu đã nói"}>
        <input type="checkbox" checked={said} onChange={onSaid} />
        <span className="s14-said__box">{said && <Icon name="check" size={11} />}</span>
      </label>
      <div className="s14-reason__main">
        <div className="s14-reason__top">
          <Chip tone={m.tone}>{m.label}</Chip>
          {reason.value > 0 &&
          <span className="s14-reason__val">
              <span className="s14-reason__val-k">GT</span>
              {window.fmtVNDShort(reason.value)}
            </span>
          }
          {reason.task && <span className="s14-reason__task mono" title="Backed by contact-task — outcome cập nhật task.status">↳ {reason.task.id}</span>}
        </div>
        <div className="s14-reason__rationale">{reason.rationale}</div>
        <div className="s14-reason__acts">
          <button className="s14-reason__act" onClick={onSchedule}><Icon name="clock" size={11} /> Đặt lịch</button>
          {!primary && <button className="s14-reason__act" onClick={onAsync}><Icon name="inbox" size={11} /> Gửi Zalo</button>}
        </div>
      </div>
    </div>);

}

/* ── Collect row (inline add / fix) ─────────────────────── */
function CollectRow({ row, done, value, onChange, onSave, onFix }) {
  if (done) {
    return (
      <div className="s14-crow s14-crow--done">
        <span className="s14-crow__label">{row.label}</span>
        <span className="s14-crow__saved"><Icon name="check" size={12} /> đã lưu{value ? ` · ${value}` : ""}</span>
      </div>);

  }
  if (row.kind === "fix") {
    return (
      <div className="s14-crow s14-crow--fix">
        <span className="s14-crow__label">{row.label}</span>
        <span className="s14-crow__sub mono">{row.sub}</span>
        <button className="s14-crow__btn" onClick={onFix}>Sửa</button>
      </div>);

  }
  return (
    <div className="s14-crow">
      <span className="s14-crow__label">{row.label}</span>
      <input
        className="s14-crow__inp"
        value={value || ""}
        placeholder={row.ph}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {if (e.key === "Enter" && (value || "").trim()) onSave();}} />
      
      <button className="s14-crow__add" disabled={!(value || "").trim()} onClick={onSave} aria-label={"Lưu " + row.label}>
        <Icon name="plus" size={13} />
      </button>
    </div>);

}

/* ── Loading skeleton ───────────────────────────────────── */
function S14Skeleton() {
  return (
    <div className="s14-body">
      <div className="s14-main">
        <div className="s14-card s14-skel" style={{ height: 60 }} />
        <div className="s14-card s14-skel" style={{ height: 120 }} />
        <div className="s14-card s14-skel" style={{ height: 150 }} />
      </div>
      <div className="s14-rail">
        <div className="s14-card s14-skel" style={{ height: 110 }} />
        <div className="s14-card s14-skel" style={{ height: 90 }} />
        <div className="s14-card s14-skel" style={{ height: 110 }} />
      </div>
    </div>);

}

/* ── S14 — Call Mode Cockpit ────────────────────────────── */
function S14_CallMode({ route, nav, openModal, toast }) {
  const queue = window.DB.callQueue;
  const partyId = route.party || queue[0];
  const idx = Math.max(0, queue.indexOf(partyId));
  const party = window.DB.partyById(partyId);
  const script = window.DB.scriptByParty(partyId);
  // task context (launched from S15): pin that task's reason as PRIMARY,
  // swap chrome to "Quay lại task". Session stays 1-per-CUSTOMER, not per-task.
  const taskCtx = route.taskCtx ? window.DB.taskById(route.taskCtx) : null;

  // ST-LOADING: brief skeleton on each party change (simulate cache fetch)
  const [loading, setLoading] = cUseState(true);
  cUseEffect(() => {
    setLoading(true);
    const t = setTimeout(() => setLoading(false), 420);
    return () => clearTimeout(t);
  }, [partyId]);

  // interactive state (all client-side — contract §9 INVARIANT)
  const [channel, setChannel] = cUseState("primary"); // primary | fallback
  const [doneTP, setDoneTP] = cUseState([]);
  const [saidReason, setSaidReason] = cUseState([]);
  const [openObj, setOpenObj] = cUseState(null);
  const [objQ, setObjQ] = cUseState("");
  const [copied, setCopied] = cUseState(false);
  const [note, setNote] = cUseState("");
  const [collectVals, setCollectVals] = cUseState({});
  const [collectDone, setCollectDone] = cUseState({});

  cUseEffect(() => {// reset per party
    setChannel("primary");setDoneTP([]);setSaidReason([]);setOpenObj(null);
    setObjQ("");setCopied(false);setNote("");setCollectVals({});setCollectDone({});
  }, [partyId]);

  const nextParty = queue[(idx + 1) % queue.length];
  const goNext = () => nav({ screen: "S14", party: nextParty });
  const backWorklist = () => nav({ screen: "S01" });
  const backToTask = () => taskCtx && nav({ screen: "S15", task: taskCtx.id });

  const topbar = (label) =>
  <div className="s14-topbar">
      {taskCtx ?
      <button className="s14-back" onClick={backToTask}><Icon name="back" size={14} /> Quay lại task</button> :
      <button className="s14-back" onClick={backWorklist}><Icon name="back" size={14} /> Worklist</button>}
      <div className="s14-topbar__mid">
        <span className="s14-mode-dot" />
        <span className="s14-mode-label">Chế độ gọi{taskCtx ? " · từ task" : ""}</span>
      </div>
      <div className="s14-topbar__end">
        {taskCtx ?
        <span className="s14-queue mono">phiên khách · 1 task ghim</span> :
        <>
            <span className="s14-queue mono">#{idx + 1}/{queue.length}</span>
            {queue.length > 1 &&
          <button className="s14-nextlink" onClick={goNext}>Khách kế <Icon name="chevron" size={12} /></button>
          }
          </>}
      </div>
    </div>;


  if (loading) {
    return <div className="s14-screen">{topbar()}<S14Skeleton /></div>;
  }

  // ST-CALL-NO-SCRIPT
  if (!party || !script) {
    return (
      <div className="s14-screen">
        {topbar()}
        <div className="s14-wrap">
          <EmptyState icon="doc" title="Chưa có kịch bản tiếp cận"
          sub={party ? `Chưa có row cache.wh_approach_script cho ${party.name}. Lô sinh kịch bản đêm chưa phủ khách này.` : "Không tìm thấy khách trong hàng đợi."}
          cta={<div className="flex-wrap" style={{ gap: 8, justifyContent: "center" }}>
              <button className="btn btn--secondary" onClick={backWorklist}>Quay lại Worklist</button>
              {party && <button className="btn btn--ghost" onClick={() => nav({ screen: "S03", party: party.id })}>Xem hồ sơ 360</button>}
            </div>} />
        </div>
      </div>);

  }

  const ap = script.approach;
  const ins = party.insight || {};
  const stale = window.hoursSince(script.refreshed_at) > 24;
  const lowConf = script.confidence === "low";
  const conf = CONF_META[script.confidence] || CONF_META.medium;
  const isStop = script.recommended === false;

  const opening = channel === "primary" ? ap.opening_message : ap.fallback_message;
  const chanLabel = channel === "primary" ? "Gọi điện" : "Zalo";

  const copyOpening = () => {
    const done = () => {setCopied(true);toast("Đã copy lời mở đầu", "success");setTimeout(() => setCopied(false), 1500);};
    try {navigator.clipboard.writeText(opening).then(done, done);} catch (e) {done();}
  };
  const toggleTP = (i) => setDoneTP((d) => d.includes(i) ? d.filter((x) => x !== i) : [...d, i]);
  const toggleReason = (id) => setSaidReason((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);

  const objections = (ap.objection_handling || []).filter((o) =>
  !objQ.trim() || (o.q + " " + o.a).toLowerCase().includes(objQ.toLowerCase()));

  const reasons = buildReasons(party, taskCtx);
  const primaryReason = reasons.find((r) => r.primary) || null;
  const secondaryReasons = reasons.filter((r) => !r.primary);

  // Bulk task sync (contract §outcome_bar): primary's task + any "đã nói"
  // reasons that are backed by a contact-task. Outcome writes task.status.
  const syncTasks = () => {
    const said = new Set(saidReason);
    const set = [];
    reasons.forEach((r) => { if (r.task && (r.primary || said.has(r.key)) && !set.includes(r.task)) set.push(r.task); });
    return set;
  };

  const logOutcome = (kind, label) => {
    const synced = syncTasks();
    const newStatus = kind === "answered" || kind === "purchased" ? "done" : kind === "callback" ? "doing" : null;
    if (newStatus) synced.forEach((t) => { t.status = newStatus; });
    openModal("M08", { party: party.id, task_ids: synced.map((t) => t.id), hinh_thuc: "call", source: "call_cockpit", outcome_hint: kind, note });
    const extra = synced.length && newStatus ? ` · đồng bộ ${synced.length} task → ${newStatus}` : "";
    toast(`Ghi nhận: ${label}${extra}`, "info");
  };

  const scheduleReason = (r) => openModal("M05", { party: party.id, source: "action_queue", source_ref: r.kind === "action" ? r.key : null, prefill_title: r.rationale });
  const resolveAsync = (r) => {
    setSaidReason((s) => s.includes(r.key) ? s : [...s, r.key]);
    if (r.task) r.task.status = "doing";
    toast("Đã gửi Zalo — ghi nhận thử liên lạc" + (r.task ? " · task → doing" : ""), "info");
  };

  const alerts = deriveAlerts(party, script);
  const collectRows = deriveCollect(party);
  const gaps = script.data_gaps || [];

  const saveCollect = (row) => {
    setCollectDone((d) => ({ ...d, [row.key]: true }));
    toast(`Đã lưu ${row.label}`, "success"); // ST-CALL-COLLECT-DONE (no panel re-render)
  };
  const fixContact = () => {
    openModal("M06", { party: party.id }); // M15 tab=contacts equivalent in this build
    toast("Mở sửa thông tin liên hệ", "info");
  };
  const createTask = () => {
    openModal("M05", { party: party.id, source: "call_cockpit" });
    toast("Mở tạo task cho khách", "info");
  };

  // ── IDENTITY BAR (contract §identity_bar) ──────────────
  const identity =
  <div className="s14-idbar">
      <span className="s14-idbar__avatar">{party.name.trim().split(/\s+/).slice(-1)[0].slice(0, 1).toUpperCase()}</span>
      <div className="s14-idbar__main">
        <div className="s14-idbar__row">
          <span className="s14-idbar__name">{party.name}</span>
          <GroupBadge group={party.group} />
          <StatusBadge status={party.status} />
          {script.region !== "—" && <span className="s14-idbar__region">· {script.region}</span>}
        </div>
        <div className="s14-idbar__phone mono"><Icon name="phone" size={13} /> {maskPhone(party.phone)}</div>
      </div>
      <div className="s14-idbar__act">
        <button className="btn btn--primary" onClick={() => openModal("M08", { party: party.id, hinh_thuc: "call", mode: "contact_attempt", channel: "phone" })}><Icon name="phone" size={14} /> Gọi</button>
        <button className="btn btn--secondary" onClick={() => openModal("M08", { party: party.id, hinh_thuc: "chat", mode: "contact_attempt", channel: "zalo" })}><Icon name="inbox" size={14} /> Zalo</button>
        <button className="btn btn--ghost" onClick={createTask}><Icon name="plus" size={14} /> Tạo task</button>
        <button className="btn btn--ghost" onClick={() => nav({ screen: "S03", party: party.id })}>360 <Icon name="chevron" size={12} /></button>
      </div>
    </div>;


  // ── ALERT ROW (contract §alert_row) ────────────────────
  const alertRow =
  <div className="s14-alertrow">
      <span className="s14-alertrow__label"><Icon name="warn" size={13} /> Cần lưu ý</span>
      <div className="s14-alertrow__chips">
        {alerts.map((a, i) => <span key={i} className={"s14-achip s14-achip--" + a.tone}>{a.label}</span>)}
      </div>
    </div>;


  // ── TRUST FOOTER ───────────────────────────────────────
  const trust =
  <div className="s14-trust">
      <span className="s14-trust__item">Độ tin: <b className={"s14-conf s14-conf--" + conf.tone}>{conf.label}</b></span>
      <span className="s14-trust__sep">·</span>
      <span className={"s14-trust__item" + (stale ? " s14-trust__item--stale" : "")} title={window.fmtDateTime(script.refreshed_at) + " ICT"}>
        {stale && <Icon name="warn" size={12} />} script {window.fmtDateTime(script.refreshed_at)} ICT {stale && "(quá 24h)"}
      </span>
      <span className="s14-trust__sep">·</span>
      <span className="s14-trust__caveat"><Icon name="warn" size={12} /> AI gợi ý — dùng phán đoán của bạn</span>
    </div>;


  return (
    <div className={"s14-screen" + (isStop ? " s14-screen--stop" : "")}>
      {topbar()}
      <div className="s14-frame">
        {identity}
        {alertRow}

        {isStop ? (
        /* ── ST-CALL-STOP (R14) — replaces LEFT+RIGHT ── */
        <div className="s14-stopwrap">
            <div className="s14-stop">
              <div className="s14-stop__head">
                <span className="s14-stop__sign"><Icon name="warn" size={20} /></span>
                <div>
                  <div className="s14-stop__title">KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH</div>
                  <div className="s14-stop__sub mono">recommended = false · R14 AI Approach-Script Gate</div>
                </div>
              </div>
              <div className="s14-stop__reason">
                <div className="s14-stop__reason-k">Lý do</div>
                {script.reason_if_not_recommended}
              </div>
              {gaps.length > 0 &&
            <div className="s14-stop__gaps">
                  {gaps.map((g, i) => <span key={i} className="s14-gap">{g}</span>)}
                </div>
            }
              <div className="s14-stop__act">
                <button className="btn btn--primary" onClick={() => openModal("M05", { party: party.id, source: "verify_account", prefill_title: "Xác minh loại tài khoản (nghi B2B)" })}>
                  <Icon name="plus" size={14} /> Tạo task xác minh tài khoản
                </button>
                <button className="btn btn--ghost" onClick={() => nav({ screen: "S03", party: party.id })}>Xem hồ sơ 360</button>
              </div>
            </div>
            {trust}
          </div>) :

        <>
            <div className="s14-body">
              {/* ═══ LEFT — NÓI GÌ (hot path) ═══ */}
              <div className="s14-main">
                {/* TALK TRACK */}
                <div className="s14-block">
                  <S14Head icon="doc" right={
                <div className="s14-chan">
                      <button className={"s14-chan__btn" + (channel === "primary" ? " s14-chan__btn--on" : "")} onClick={() => setChannel("primary")}>
                        <Icon name="phone" size={12} /> Gọi
                      </button>
                      <button className={"s14-chan__btn" + (channel === "fallback" ? " s14-chan__btn--on" : "")} onClick={() => setChannel("fallback")}>
                        <Icon name="inbox" size={12} /> Zalo
                      </button>
                    </div>
                }>Lời thoại · {chanLabel}</S14Head>

                  {lowConf && <div className="s14-lowconf"><Icon name="warn" size={13} /> Độ tin thấp — kiểm chứng khi nói chuyện, đừng cam kết chắc.</div>}

                  <div className={"s14-track" + (copied ? " s14-track--flash" : "") + (lowConf ? " s14-track--dim" : "")}>
                    <p className="s14-track__text">"{opening}"</p>
                    <button className="s14-copy" onClick={copyOpening} title="Copy lời mở đầu">
                      <Icon name={copied ? "check" : "copy"} size={14} /> {copied ? "Đã copy" : "Copy"}
                    </button>
                  </div>
                  {script.timing && <div className="s14-timing"><Icon name="clock" size={13} /> {script.timing}</div>}
                </div>

                {/* TALKING POINTS */}
                <div className="s14-block">
                  <S14Head icon="check" right={<span className="s14-count mono">{doneTP.length}/{ap.talking_points.length}</span>}>Điểm nói · tick khi đã nói</S14Head>
                  <div className="s14-tplist">
                    {ap.talking_points.map((tp, i) => {
                    const on = doneTP.includes(i);
                    return (
                      <button key={i} className={"s14-tp" + (on ? " s14-tp--on" : "")} onClick={() => toggleTP(i)}>
                          <span className={"s14-tp__box" + (on ? " s14-tp__box--on" : "")}>{on && <Icon name="check" size={12} />}</span>
                          <span className="s14-tp__text">{tp}</span>
                        </button>);

                  })}
                  </div>
                  {ap.cross_sell && ap.cross_sell.length > 0 &&
                <div className="s14-cross">
                      <span className="s14-cross__label">Gợi thêm</span>
                      {ap.cross_sell.map((c, i) => <span key={i} className="s14-cross__chip">{c}</span>)}
                    </div>
                }
                </div>

                {/* OBJECTION HANDLING */}
                <div className="s14-block">
                  <S14Head icon="search" right={
                <div className="s14-objsearch">
                      <Icon name="search" size={12} />
                      <input value={objQ} onChange={(e) => setObjQ(e.target.value)} placeholder="khách vừa nói gì?" aria-label="Tìm tình huống" />
                      {objQ && <button className="s14-objsearch__x" onClick={() => setObjQ("")} aria-label="Xóa">✕</button>}
                    </div>
                }>Xử lý từ chối</S14Head>
                  <div className="s14-objlist">
                    {objections.length === 0 ?
                  <div className="s14-obj-empty">Không có tình huống khớp "{objQ}".</div> :
                  objections.map((o, i) =>
                  <ObjectionCard key={i} obj={o} open={openObj === o.q} onToggle={() => setOpenObj(openObj === o.q ? null : o.q)} />
                  )}
                  </div>
                </div>

                {/* GUARDRAILS */}
                <div className="s14-guard">
                  <span className="s14-guard__sign"><Icon name="warn" size={14} /></span>
                  <div className="s14-guard__wrap">
                    <span className="s14-guard__label">Guardrails</span>
                    <div className="s14-guard__list">
                      {ap.do_not.map((d, i) => <span key={i} className="s14-guard__item">{d}</span>)}
                    </div>
                  </div>
                </div>
              </div>{/* .s14-main */}

              {/* ═══ RIGHT — VÌ SAO & BỐI CẢNH (rail) ═══ */}
              <aside className="s14-rail">
                {/* VÌ SAO GỌI (reason_to_call) */}
                <div className="s14-railcard">
                  <div className="s14-railcard__head">
                    <span className="s14-railcard__title">Vì sao gọi</span>
                    <span className="s14-railcard__hint">đọc trước khi quay số</span>
                  </div>
                  <div className="s14-railcard__lead">{script.opportunity}</div>
                  {reasons.length === 0 ?
                /* ST-CALL-NO-ACTIONS */
                <div className="s14-railcaveat">Không có đề xuất từ action queue — dùng kịch bản làm cơ sở cuộc gọi.</div> :

                <>
                    {primaryReason &&
                  <div className="s14-reasongrp">
                        <div className="s14-reason-sub s14-reason-sub--primary"><span className="s14-reason-sub__star">★</span> Ưu tiên — call trigger{taskCtx ? " · ghim từ task" : ""}</div>
                        <div className="s14-reasonlist">
                          <ReasonCard reason={primaryReason} primary said={saidReason.includes(primaryReason.key)}
                    onSaid={() => toggleReason(primaryReason.key)} onSchedule={() => scheduleReason(primaryReason)} onAsync={() => resolveAsync(primaryReason)} />
                        </div>
                      </div>
                  }
                    {secondaryReasons.length > 0 &&
                  <div className="s14-reasongrp">
                        <div className="s14-reason-sub">Tranh thủ nếu thuận</div>
                        <div className="s14-reasonlist">
                          {secondaryReasons.map((r) =>
                    <ReasonCard key={r.key} reason={r} said={saidReason.includes(r.key)}
                      onSaid={() => toggleReason(r.key)} onSchedule={() => scheduleReason(r)} onAsync={() => resolveAsync(r)} />
                    )}
                        </div>
                      </div>
                  }
                  </>
                }
                </div>

                {/* SNAPSHOT */}
                <div className="s14-railcard">
                  <div className="s14-railcard__head">
                    <span className="s14-railcard__title">Snapshot</span>
                    <span className="s14-railcard__hint mono">R2 · chỉ đọc cache</span>
                  </div>
                  <div className="s14-snap">
                    <div className="s14-snap__cell"><span className="s14-snap__k">LTV</span><span className="s14-snap__v mono">{window.fmtVNDShort(ins.monetary)}</span></div>
                    <div className="s14-snap__cell"><span className="s14-snap__k">Số đơn</span><span className="s14-snap__v mono">{ins.frequency}</span></div>
                    <div className="s14-snap__cell"><span className="s14-snap__k">Chu kỳ</span><span className="s14-snap__v mono">{ins.cycle_days ? ins.cycle_days + "d" : "—"}</span></div>
                    <div className="s14-snap__cell"><span className="s14-snap__k">Gần nhất</span><span className="s14-snap__v mono">{ins.recency_days}d</span></div>
                  </div>
                  <div className="s14-snap__read"><span className="s14-snap__read-k">Chân dung</span> {script.profile_read}</div>
                  {ins.refreshed_at &&
                <div className="s14-snap__fresh"><FreshnessBadge plain table="wh_customer_insight" at={ins.refreshed_at} /></div>
                }
                </div>

                {/* THU THẬP CÒN THIẾU (collect) */}
                <div className="s14-railcard">
                  <div className="s14-railcard__head">
                    <span className="s14-railcard__title">Thu thập còn thiếu</span>
                    <span className="s14-railcard__hint">lưu ngay khi khách đọc</span>
                  </div>
                  {collectRows.length === 0 && gaps.length === 0 ?
                <div className="s14-railcaveat">Hồ sơ đã đủ thông tin liên hệ cơ bản.</div> :

                <div className="s14-collect">
                      {collectRows.map((r) =>
                  <CollectRow key={r.key} row={r}
                  done={!!collectDone[r.key]} value={collectVals[r.key]}
                  onChange={(v) => setCollectVals((s) => ({ ...s, [r.key]: v }))}
                  onSave={() => saveCollect(r)} onFix={fixContact} />
                  )}
                      <button className="s14-collect__addr" onClick={() => {openModal("M06", { party: party.id });}}>
                        <Icon name="edit" size={12} /> Cập nhật địa chỉ / thông tin khác
                      </button>
                      {gaps.length > 0 &&
                  <div className="s14-collect__gaps">
                          <span className="s14-collect__gaps-k">AI lưu ý thiếu</span>
                          {gaps.map((g, i) => <span key={i} className="s14-collect__gap">{g}</span>)}
                        </div>
                  }
                    </div>
                }
                </div>
              </aside>{/* .s14-rail */}
            </div>{/* .s14-body */}

            {trust}
          </>
        }
      </div>{/* .s14-frame */}

      {/* OUTCOME BAR (sticky) — contract §outcome_bar */}
      {!isStop &&
      <div className="s14-outcome">
          <div className="s14-outcome__inner">
            <textarea className="s14-outcome__note" rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Ghi chú tạm khi gọi…" aria-label="Ghi chú cuộc gọi" />
            <div className="s14-outcome__btns">
              <button className="s14-oc s14-oc--good" onClick={() => logOutcome("answered", "Gọi được")}><Icon name="check" size={14} /> Gọi được</button>
              <button className="s14-oc s14-oc--miss" onClick={() => logOutcome("no_answer", "Không nghe")}><Icon name="close" size={14} /> Không nghe</button>
              <button className="s14-oc s14-oc--later" onClick={() => logOutcome("callback", "Hẹn lại")}><Icon name="clock" size={14} /> Hẹn lại</button>
              <button className="s14-oc s14-oc--buy" onClick={() => logOutcome("purchased", "Đã mua")}><Icon name="money" size={14} /> Đã mua</button>
            </div>
            {taskCtx ?
            <button className="btn btn--primary s14-next" onClick={backToTask}><Icon name="back" size={13} /> Quay lại task</button> :
            <button className="btn btn--primary s14-next" onClick={goNext}>Khách kế <Icon name="chevron" size={13} /></button>}
          </div>
        </div>
      }
    </div>);

}

window.S14_CallMode = S14_CallMode;
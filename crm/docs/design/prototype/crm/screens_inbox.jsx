/* ============================================================
   S05 Inbox · S06 Conversation Detail · S07 Tasks Board
   ============================================================ */
const { useState: iUseState } = React;

/* ── S05 Inbox ──────────────────────────────────────────── */
function S05_Inbox({ nav, openModal }) {
  const [status, setStatus] = iUseState("all");
  const [assignee, setAssignee] = iUseState("all");
  const [selId, setSelId] = iUseState(null);

  let convs = window.DB.conversations.slice().sort((a, b) => (a.last_at < b.last_at ? 1 : -1));
  if (status !== "all") convs = convs.filter((c) => c.status === status);
  if (assignee === "me") convs = convs.filter((c) => c.assignee === window.DB.ME || c.assignee === "u_cskb");
  const sel = convs.find((c) => c.id === selId);

  return (
    <div className="crm-page page-enter">
      <PageHead eyebrow="Inbox · M5" title="Hội thoại Messenger"
        sub="R12 · read-only v1 · SSE cập nhật real-time"
        aside={<button className="btn btn--secondary" onClick={() => setAssignee(assignee === "me" ? "all" : "me")}>{assignee === "me" ? "Tất cả NV" : "Gán cho tôi"}</button>} />

      <FilterBar
        filters={[
          { field: "status", label: "Trạng thái", options: [{ value: "all", label: "Tất cả" }, { value: "open", label: "Open" }, { value: "pending", label: "Pending" }, { value: "closed", label: "Closed" }] },
          { field: "assignee", label: "Người xử lý", options: [{ value: "all", label: "Tất cả" }, { value: "me", label: "Của tôi" }] },
        ]}
        values={{ status, assignee }} onChange={(f, v) => (f === "status" ? setStatus(v) : setAssignee(v))}
        onClear={() => { setStatus("all"); setAssignee("all"); }} />

      <div className="inbox-grid">
        {convs.length === 0 ? (
          <div className="conv-list"><EmptyState icon="inbox" title="Không có hội thoại" sub="Không có hội thoại trong bộ lọc hiện tại." /></div>
        ) : (
          <div className="conv-list">
            {convs.map((c) => {
              const linked = c.party ? window.DB.partyById(c.party) : null;
              return (
                <div key={c.id} className={"conv-row" + (selId === c.id ? " conv-row--active" : "")} onClick={() => setSelId(c.id)}>
                  <span className={"conv-row__unread" + (c.unread === 0 ? " conv-row__unread--none" : "")} />
                  <div className="conv-row__main">
                    <div className="conv-row__name">
                      {linked ? <b>{linked.name}</b> : <span className="psid-mono">{c.psid}</span>}
                      {linked ? <Bdg tone="good">✓ Đã link</Bdg> : <Bdg tone="warn" dot>Chưa link khách</Bdg>}
                    </div>
                    <div className="conv-row__prev">"{c.preview}"</div>
                    <div className="flex-wrap" style={{ gap: 6 }}>
                      {c.status === "open" && <Bdg tone="good" dot>open</Bdg>}
                      {c.status === "pending" && <Bdg tone="warn" dot>pending</Bdg>}
                      {c.status === "closed" && <Bdg dot>closed</Bdg>}
                      <span className="muted" style={{ fontSize: 11 }}>{c.assignee ? window.DB.userById(c.assignee).short : "Chưa gán"}</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
                    <span className="conv-row__time">{relTime(c.last_at)}</span>
                    {c.unread > 0 && <span className="crm-nav__badge crm-nav__badge--warn">{c.unread}</span>}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="preview-pane">
          {!sel ? (
            <EmptyState icon="inbox" title="Chọn một hội thoại" sub="Chọn hội thoại bên trái để xem trước nội dung." />
          ) : (
            <div style={{ padding: "var(--sp-5)", display: "flex", flexDirection: "column", gap: "var(--sp-4)", height: "100%" }}>
              <div className="row-between">
                <div>
                  <div className="name" style={{ fontSize: 18 }}>{sel.party ? window.DB.partyById(sel.party).name : sel.psid}</div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--fg-tertiary)", marginTop: 4 }}>{sel.psid} · {sel.channel}</div>
                </div>
                {sel.party ? <Bdg tone="good">✓ Đã link</Bdg> : <Bdg tone="warn" dot>Chưa link khách</Bdg>}
              </div>
              <div className="divider" />
              <div className="thread" style={{ flex: 1, padding: 0, overflowY: "auto" }}>
                {sel.messages.map((m, i) => (
                  <div key={i} className={"msg msg--" + (m.from === "agent" ? "agent" : "customer")}>
                    <div className="msg__bubble">{m.text}</div>
                    <div className="msg__time">{fmtTime(m.at)} ICT</div>
                  </div>
                ))}
              </div>
              <div className="flex-wrap">
                <button className="btn btn--primary" style={{ padding: "9px 14px" }} onClick={() => nav({ screen: "S06", conversation: sel.id })}>Mở hội thoại <Icon name="chevron" size={13} /></button>
                <button className="btn btn--secondary" style={{ padding: "9px 14px" }} onClick={() => openModal("M09", { conversation: sel.id })}><Icon name="user" size={13} /> Gán NV</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── S06 Conversation Detail ────────────────────────────── */
function S06_Conversation({ route, nav, openModal }) {
  const conv = window.DB.convById(route.conversation) || window.DB.conversations[0];
  const linked = conv.party ? window.DB.partyById(conv.party) : null;
  return (
    <div className="crm-page page-enter">
      <div className="c360-topbar">
        <button className="c360-back" onClick={() => nav({ screen: "S05" })}><Icon name="back" size={14} /> Inbox</button>
        <div className="c360-id">
          <span className="c360-name" style={{ fontSize: 22 }}>{linked ? linked.name : conv.psid}</span>
          {conv.status === "pending" && <Bdg tone="warn" dot>Pending</Bdg>}
          {conv.status === "open" && <Bdg tone="good" dot>Open</Bdg>}
          {conv.status === "closed" && <Bdg dot>Closed</Bdg>}
        </div>
        <div className="c360-actions">
          <span className="mono" style={{ fontSize: 11, color: "var(--fg-tertiary)" }}>Assignee: {conv.assignee ? window.DB.userById(conv.assignee).short : "—"}</span>
          <button className="btn btn--secondary" style={{ padding: "9px 14px" }} onClick={() => openModal("M09", { conversation: conv.id })}><Icon name="user" size={13} /> Đổi NV</button>
          <button className="btn btn--secondary" style={{ padding: "9px 14px" }} onClick={() => openModal("M08", { party: conv.party, conversation: conv.id })}><Icon name="doc" size={13} /> Ghi note</button>
          {conv.status !== "closed" && <button className="btn btn--primary" style={{ padding: "9px 14px" }} onClick={() => openModal("M10", { conversation: conv.id })}>Đóng hội thoại</button>}
        </div>
      </div>

      <div className="conv-detail">
        <div className="thread-wrap">
          <div className="thread">
            {conv.messages.map((m, i) => (
              <div key={i} className={"msg msg--" + (m.from === "agent" ? "agent" : "customer")}>
                <div className="msg__time" style={{ marginBottom: 2 }}>{m.from === "agent" ? window.DB.userById(conv.assignee).short : "Khách"}</div>
                <div className="msg__bubble">{m.text}</div>
                <div className="msg__time">{fmtTime(m.at)} ICT</div>
              </div>
            ))}
          </div>
          {conv.status === "closed" ? (
            <div className="input-bar"><div className="input-bar__fake">Hội thoại đã đóng</div><button className="btn btn--secondary" style={{ padding: "9px 14px" }}>Mở lại</button></div>
          ) : (
            <div className="input-bar"><div className="input-bar__fake">Nhập tin nhắn… (vô hiệu hóa — read-only v1, R12)</div></div>
          )}
        </div>

        <div className="stack stack-3">
          {linked ? (
            <div className="conv-cust-card">
              <div className="row-between">
                <span className="name" style={{ fontSize: 17 }}>{linked.name}</span>
                <GroupBadge group={linked.group} />
              </div>
              <div className="facts">
                <div className="fact"><span className="fact__k">SĐT</span><span className="fact__v mono">{linked.phone}</span></div>
                <div className="fact"><span className="fact__k">Status</span><span className="fact__v"><StatusBadge status={linked.status} /></span></div>
                <div className="fact"><span className="fact__k">Mua gần</span><span className="fact__v mono">{fmtDateOnly(linked.last_order)}</span></div>
              </div>
              {linked.actions.length > 0 && <div className="caveat caveat--rule caveat--info" style={{ fontSize: 12.5 }}>Action queue: {linked.actions.length} mục — {linked.actions.map((a) => window.ACTION_META[a.type].label).join(", ")}</div>}
              <button className="btn btn--primary party-cta" onClick={() => nav({ screen: "S03", party: linked.id })}>Mở hồ sơ đầy đủ <Icon name="chevron" size={13} /></button>
            </div>
          ) : (
            <div className="conv-cust-card">
              <div className="caption">Chưa link khách</div>
              <p style={{ fontSize: 13, color: "var(--fg-muted)" }}>PSID này chưa khớp với party nào. Tìm và gắn khách để xem hồ sơ 360.</p>
              <button className="btn btn--primary party-cta" onClick={() => openModal("M11", { conversation: conv.id })}><Icon name="link" size={13} /> Tìm & gắn khách</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── S07 Tasks Board ────────────────────────────────────── */
const BOARD_COLS = [{ id: "open", label: "Open" }, { id: "doing", label: "Doing" }, { id: "done", label: "Done" }, { id: "cancelled", label: "Cancelled" }];
function S07_Tasks({ nav, openModal, toast, openPreview }) {
  const [tasks, setTasks] = iUseState(() => window.DB.tasks.map((t) => ({ ...t })));
  const [assignee, setAssignee] = iUseState("all");
  const [view, setView] = iUseState("board");
  const [drag, setDrag] = iUseState(null);
  const [dropCol, setDropCol] = iUseState(null);

  let filtered = tasks;
  if (assignee !== "all") filtered = filtered.filter((t) => t.assignee === assignee);

  const move = (id, status) => { setTasks((ts) => ts.map((t) => t.id === id ? { ...t, status } : t)); toast("Đã chuyển task → " + status); };

  return (
    <div className="crm-page page-enter">
      <PageHead eyebrow="Tasks · M4" title="Bảng công việc"
        sub="R8 · idempotent · R11 · conversion attribution"
        aside={<div className="flex-wrap">
          <div className="seg"><button className={"seg__btn"} aria-selected={view === "list"} onClick={() => setView("list")}>List</button><button className="seg__btn" aria-selected={view === "board"} onClick={() => setView("board")}>Board</button></div>
          <button className="btn btn--primary" onClick={() => openModal("M05", {})}><Icon name="plus" size={14} /> Tạo task</button>
        </div>} />

      <FilterBar
        filters={[{ field: "assignee", label: "Người nhận", options: [{ value: "all", label: "Tất cả" }, ...window.DB.users.filter((u) => u.role !== "admin").map((u) => ({ value: u.id, label: u.short }))] }]}
        values={{ assignee }} onChange={(f, v) => setAssignee(v)} onClear={() => setAssignee("all")} />

      {view === "board" ? (
        <div className="board">
          {BOARD_COLS.map((col) => {
            const colTasks = filtered.filter((t) => t.status === col.id);
            return (
              <div key={col.id} className="board-col">
                <div className="board-col__head"><span className="board-col__name">{col.label}</span><span className="board-col__count">{colTasks.length}</span></div>
                <div className={"board-col__body" + (dropCol === col.id ? " is-drop" : "")}
                  onDragOver={(e) => { e.preventDefault(); setDropCol(col.id); }} onDragLeave={() => setDropCol(null)}
                  onDrop={() => { if (drag) move(drag, col.id); setDrag(null); setDropCol(null); }}>
                  {colTasks.map((t) => {
                    const p = window.DB.partyById(t.party);
                    return (
                      <div key={t.id} className={"tcard" + (drag === t.id ? " tcard--dragging" : "")} draggable onDragStart={() => setDrag(t.id)} onDragEnd={() => { setDrag(null); setDropCol(null); }}>
                        <div className="tcard__top">
                          {t.source === "action_queue" && <span className="auto-tag">AUTO</span>}
                          <span className={"prio prio--" + t.priority}>{t.priority}</span>
                          <span className="tcard__title" onClick={() => nav({ screen: "S15", task: t.id })}>{t.title}</span>
                        </div>
                        {p && <div className="tcard__meta"><span className="conv-row__name" style={{ fontSize: 12, cursor: "pointer" }} onClick={(e) => openPreview && openPreview(p.id, e.currentTarget.getBoundingClientRect())}>{p.name}</span></div>}
                        <div className="tcard__meta">
                          <span><Icon name="clock" size={10} /> {t.status === "done" && t.completed_at ? fmtDate(t.completed_at) : fmtDate(t.due)}</span>
                          <span>{window.DB.userById(t.assignee).short}</span>
                          {col.id !== "done" && <button className="ghost-link" style={{ padding: 0, fontSize: 10.5 }} onClick={() => move(t.id, "done")}>✓ Done</button>}
                        </div>
                      </div>
                    );
                  })}
                  {colTasks.length === 0 && <div className="muted" style={{ fontSize: 12, textAlign: "center", padding: "var(--sp-4) 0" }}>—</div>}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="wl-list">
          {filtered.sort((a, b) => (a.due < b.due ? -1 : 1)).map((t) => {
            const p = window.DB.partyById(t.party);
            const isDone = t.status === "done";
            return (
              <div key={t.id} className={"wl-row" + (isDone ? " wl-row--done" : "")} style={{ gridTemplateColumns: "auto 1fr auto" }}>
                <button className={"wl-check" + (isDone ? " wl-check--on" : "")} onClick={() => move(t.id, isDone ? "open" : "done")}>{isDone && <Icon name="check" size={13} />}</button>
                <div className="wl-row__main">
                  <div className="wl-row__top">{t.source === "action_queue" && <span className="auto-tag">AUTO</span>}<span className="wl-row__name" onClick={() => nav({ screen: "S15", task: t.id })}>{t.title}</span></div>
                  <div className="wl-row__meta">
                    {p && <span className="muted" style={{ fontSize: 12 }}>{p.name}</span>}
                    <span className="wl-row__due"><Icon name="clock" size={11} /> {fmtDate(t.due)}</span>
                    <span className={"prio prio--" + t.priority}>{t.priority}</span>
                    <span className={"tkind-tag tkind-tag--" + t.task_kind}>{t.task_kind}</span>
                    <Bdg dot tone={t.status === "done" ? "good" : t.status === "doing" ? "warn" : ""}>{t.status}</Bdg>
                  </div>
                </div>
                <button className="icon-btn icon-btn--sm" onClick={() => openModal("M05", { task: t.id })}><Icon name="edit" size={12} /></button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

Object.assign(window, { S05_Inbox, S06_Conversation, S07_Tasks });

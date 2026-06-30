/* ============================================================
   S03 Customer 360 Detail + panels P01–P06
   ============================================================ */
const { useState: dUseState } = React;

const TABS_360 = [
  { id: "P01", label: "Insight" }, { id: "P02", label: "Đơn hàng" }, { id: "P03", label: "Timeline" },
  { id: "P04", label: "Tasks" }, { id: "P05", label: "Ghi chú" }, { id: "P06", label: "Chat" },
];

function S03_Customer360({ route, nav, openModal, toast }) {
  const party = window.DB.partyById(route.party) || window.DB.parties[0];
  const [tab, setTab] = dUseState(route.tab || "P01");
  const ins = party.insight;
  const ownerUser = party.owner ? window.DB.userById(party.owner) : null;

  const tabCounts = {
    P02: (window.DB.orders[party.id] || []).length,
    P03: (window.DB.activities[party.id] || []).length,
    P04: window.DB.tasks.filter((t) => t.party === party.id).length,
    P05: (window.DB.notes[party.id] || []).length,
    P06: window.DB.conversations.filter((c) => c.party === party.id).length,
  };

  return (
    <div className="crm-page page-enter">
      {/* topbar */}
      <div className="c360-topbar">
        <button className="c360-back" onClick={() => nav({ screen: "S02" })}><Icon name="back" size={14} /> Quay lại</button>
        <div className="c360-id">
          <span className="c360-name">{party.name}</span>
          <GroupBadge group={party.group} />
          <StatusBadge status={party.status} />
        </div>
        <div className="c360-actions">
          <button className="btn btn--secondary" style={{ padding: "9px 14px" }} onClick={() => openModal("M08", { party: party.id })}><Icon name="doc" size={13} /> Ghi log</button>
          <button className="btn btn--secondary" style={{ padding: "9px 14px" }} onClick={() => openModal("M05", { party: party.id })}><Icon name="plus" size={13} /> Task</button>
          <button className="btn btn--secondary" style={{ padding: "9px 14px" }} onClick={() => openModal("M04", { party: party.id })}><Icon name="user" size={13} /> Gán NV</button>
          <button className="btn btn--primary" style={{ padding: "9px 14px" }} onClick={() => openModal("M03", { party: party.id })}><Icon name="tag" size={13} /> Tag</button>
        </div>
      </div>

      {party.status === "churned" && (
        <div className="merged-banner"><Icon name="warn" size={15} /><span>Khách <b>churned</b> — chưa mua {ins.recency_days} ngày. Cân nhắc đưa vào chiến dịch win-back.</span></div>
      )}

      <div className="detail-grid" style={{ padding: 0, maxWidth: "none", gridTemplateColumns: "minmax(0, 2.3fr) minmax(280px, 1fr)" }}>
        {/* info panel — right column */}
        <div className="detail-sidebar" style={{ order: 2 }}>
          <div className="scard">
            <div className="caption scard__eyebrow">Thông tin cơ bản</div>
            <div className="facts">
              <div className="fact"><span className="fact__k">Tên</span><span className="fact__v">{party.name}</span></div>
              <div className="fact"><span className="fact__k">SĐT</span><span className="fact__v mono">{party.phone}</span></div>
              <div className="fact"><span className="fact__k">Email</span><span className="fact__v">{party.email || <span className="dash">—</span>}</span></div>
              <div className="fact"><span className="fact__k">Sapo ID</span><span className="fact__v mono">{party.sapo}</span></div>
              <div className="fact"><span className="fact__k">Code</span><span className="fact__v mono">{party.code}</span></div>
              <div className="fact"><span className="fact__k">Owner</span><span className="fact__v">{ownerUser ? ownerUser.short : <span className="dash">Chưa gán</span>}</span></div>
            </div>
            <div className="consent-row" style={{ marginTop: "var(--sp-3)", paddingTop: "var(--sp-3)", borderTop: "1px solid var(--border)" }}>
              <span className="fact__k" style={{ minWidth: 92 }}>Consent</span>
              {party.consent ? <span className="consent-yes"><Icon name="check" size={13} /> Cho phép liên lạc</span> : <span className="consent-no"><Icon name="close" size={13} /> Không liên lạc (R1)</span>}
            </div>
          </div>

          <div className="scard">
            <div className="row-between" style={{ marginBottom: "var(--sp-3)" }}>
              <span className="caption">Tags</span>
              <button className="ghost-link" onClick={() => openModal("M03", { party: party.id })}><Icon name="plus" size={11} /> Thêm</button>
            </div>
            <TagChips tagIds={party.tags} editable onAdd={() => openModal("M03", { party: party.id })} onRemove={() => toast("Đã bỏ tag")} />
          </div>

          <div className="scard">
            <div className="row-between" style={{ marginBottom: "var(--sp-3)" }}>
              <span className="caption">Thông tin bổ sung</span>
              <button className="ghost-link" onClick={() => openModal("M06", { party: party.id })}><Icon name="edit" size={11} /> Sửa</button>
            </div>
            <div className="facts">
              {window.DB.fieldDefs.map((fd) => {
                const v = party.custom[fd.name];
                return <div key={fd.id} className="fact"><span className="fact__k">{fd.label}</span><span className="fact__v">{v == null ? <span className="dash">—</span> : v === true ? "Có" : v === false ? "Không" : String(v)}</span></div>;
              })}
            </div>
          </div>
        </div>

        {/* primary — tabs + panel (left) */}
        <div className="detail-main" style={{ order: 1 }}>
          <div className="tabbar">
            {TABS_360.map((t) => (
              <button key={t.id} className="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
                {t.label}{tabCounts[t.id] != null && <span className="tab__count">{tabCounts[t.id]}</span>}
              </button>
            ))}
          </div>
          <div className="tabpanel" key={tab}>
            {tab === "P01" && <P01_Insight party={party} openModal={openModal} nav={nav} />}
            {tab === "P02" && <P02_Orders party={party} openModal={openModal} />}
            {tab === "P03" && <P03_Timeline party={party} openModal={openModal} nav={nav} />}
            {tab === "P04" && <P04_Tasks party={party} openModal={openModal} toast={toast} />}
            {tab === "P05" && <P05_Notes party={party} openModal={openModal} />}
            {tab === "P06" && <P06_Convs party={party} nav={nav} />}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── P01 Insight ────────────────────────────────────────── */
function P01_Insight({ party, openModal, nav }) {
  const ins = party.insight;
  if (!ins || ins.frequency == null) return <EmptyState icon="bolt" title="Insight chưa có" sub="Chưa có row trong wh_customer_insight cho khách này." />;
  const sigTone = window.SIGNAL_META[ins.next_signal] || "muted";
  const tone = (t) => t === "moss" ? "var(--moss-500)" : t === "warn" ? "var(--honey-500)" : t === "bad" ? "var(--coral-500)" : t === "muted" ? "var(--fg-tertiary)" : "var(--fg-1)";
  return (
    <div className="stack stack-5">
      <div>
        <div className="panel-head"><span className="panel-title">Action queue</span><span className="panel-sub">{party.actions.length} đề xuất</span></div>
        {party.actions.length === 0 ? (
          <div className="caveat caveat--info">Không có hành động đề xuất nào cho khách này.</div>
        ) : (
          <div className="stack stack-3">
            {party.actions.map((a) => <ActionQueueCard key={a.action_id} action={a} party={party.id}
              onCall={(act) => window.DB.scriptByParty(party.id) ? nav({ screen: "S14", party: party.id }) : openModal("M08", { party: party.id, hinh_thuc: "call", party_name: party.name })}
              onTask={(act) => openModal("M05", { party: party.id, action: act, source: "action_queue" })} />)}
          </div>
        )}
      </div>

      <div>
        <div className="panel-head"><span className="panel-title">RFM</span><span className="panel-sub">{party.group}</span></div>
        <div className="rfm">
          <div className="rfm__cell"><div className="rfm__glyph">R</div><div className="rfm__name">Recency</div><div className="rfm__val">{ins.recency_days}<span style={{ fontSize: 12, color: "var(--fg-tertiary)" }}> ngày</span></div></div>
          <div className="rfm__cell"><div className="rfm__glyph">F</div><div className="rfm__name">Frequency</div><div className="rfm__val">{ins.frequency}<span style={{ fontSize: 12, color: "var(--fg-tertiary)" }}> đơn</span></div></div>
          <div className="rfm__cell"><div className="rfm__glyph">M</div><div className="rfm__name">Monetary · LTV</div><div className="rfm__val" style={{ fontSize: 16 }}>{fmtVNDShort(ins.monetary)}</div></div>
        </div>
      </div>

      <div>
        <div className="panel-head"><span className="panel-title">Signals</span></div>
        <div className="signal-grid">
          <div className="signal-cell"><div className="signal-cell__k">Customer status</div><div className="signal-cell__v"><StatusBadge status={party.status} /></div></div>
          <div className="signal-cell"><div className="signal-cell__k">Next purchase</div><div className="signal-cell__v"><span className="signal-dot" style={{ background: tone(sigTone) }} /> {ins.next_signal}</div></div>
          <div className="signal-cell"><div className="signal-cell__k">Discount sensitivity</div><div className="signal-cell__v">{ins.discount_sens}</div></div>
          <div className="signal-cell"><div className="signal-cell__k">Top affinity</div><div className="signal-cell__v" style={{ fontSize: 14 }}>{ins.affinity}</div></div>
          {ins.has_cogs && <div className="signal-cell"><div className="signal-cell__k">Realized margin (R7)</div><div className="signal-cell__v"><span style={{ color: "var(--moss-500)" }}>{ins.margin_pct}%</span> <span className="muted" style={{ fontSize: 11 }}>has_cogs ✓</span></div></div>}
          {!ins.has_cogs && <div className="signal-cell"><div className="signal-cell__k">Realized margin</div><div className="signal-cell__v"><span className="dash">—</span> <span className="muted" style={{ fontSize: 11 }}>has_cogs ✗</span></div></div>}
        </div>
      </div>

      <div className="row-between" style={{ paddingTop: "var(--sp-2)", borderTop: "1px solid var(--border)" }}>
        <FreshnessBadge plain table="wh_customer_insight" at={ins.refreshed_at} />
        <span className="caption">R2 · CRM không tính lại insight</span>
      </div>
    </div>
  );
}

/* ── P02 Orders ─────────────────────────────────────────── */
function P02_Orders({ party, openModal }) {
  const orders = window.DB.orders[party.id] || [];
  return (
    <div className="stack stack-4">
      <div className="toolbar">
        <span className="panel-sub">10 đơn gần nhất · cache.wh_order_hdr</span>
        <div className="flex-wrap">
          <FreshnessBadge plain table="wh_order_hdr" at="2026-06-14T01:00:00Z" />
          <button className="btn btn--secondary" style={{ padding: "8px 12px" }} onClick={() => openModal("M08", { party: party.id, prefillOrder: orders[0] ? orders[0].code : "" })}><Icon name="doc" size={13} /> Ghi log</button>
        </div>
      </div>
      {orders.length === 0 ? (
        <EmptyState icon="doc" title="Khách chưa có đơn hàng" sub="Không có bản ghi nào trong wh_order_hdr." />
      ) : (
        <div className="tbl-wrap">
          <table className="tbl tbl--orders">
            <thead><tr><th>Order code</th><th>Ngày (ICT)</th><th className="num-h">Net revenue</th><th>Status</th></tr></thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.code} className="is-clickable">
                  <td className="mono" style={{ color: "var(--fg)" }}>{o.code}</td>
                  <td className="mono" style={{ color: "var(--fg-muted)" }}>{fmtDateOnly(o.date)} <span className="ict">ICT</span></td>
                  <td className="num cell-strong">{fmtVND(o.net)}</td>
                  <td>{o.status === "completed" ? <Bdg tone="good" dot>completed</Bdg> : <Bdg tone="bad" dot>{o.status}</Bdg>}</td>
                </tr>
              ))}
            </tbody>
            <tfoot><tr><td colSpan={2}>Tổng {orders.length} đơn</td><td className="num">{fmtVND(orders.reduce((s, o) => s + o.net, 0))}</td><td></td></tr></tfoot>
          </table>
        </div>
      )}
      <div className="note-line"><span className="caveat__mark">R3</span><span>Value-link qua customer_id, không FK · R7 · không hiển thị gross_margin_pct.</span></div>
    </div>
  );
}

/* ── P03 Timeline ───────────────────────────────────────── */
const ACT_LABEL = { call: "call", note: "note", visit: "visit", email: "email", chat: "chat", other: "other" };
function P03_Timeline({ party, openModal, nav }) {
  const [filter, setFilter] = dUseState("all");
  let acts = (window.DB.activities[party.id] || []).slice().sort((a, b) => (a.at < b.at ? 1 : -1));
  if (filter !== "all") acts = acts.filter((a) => a.type === filter);
  return (
    <div className="stack stack-4">
      <div className="toolbar">
        <span className="panel-title">Activity timeline</span>
        <div className="flex-wrap">
          <FilterSelect label="Loại" value={filter} onChange={setFilter} options={[{ value: "all", label: "Tất cả" }, ...["call", "note", "visit", "email", "chat", "other"].map((t) => ({ value: t, label: t }))]} />
          <button className="btn btn--secondary" style={{ padding: "8px 12px" }} onClick={() => openModal("M08", { party: party.id })}><Icon name="plus" size={13} /> Ghi log</button>
        </div>
      </div>
      {acts.length === 0 ? (
        <EmptyState icon="clock" title="Chưa có hoạt động nào" sub="Ghi log đầu tiên để bắt đầu timeline khách." cta={<button className="btn btn--secondary" onClick={() => openModal("M08", { party: party.id })}>Ghi log</button>} />
      ) : (
        <div className="timeline">
          {acts.map((a) => {
            const mod = a.type === "call" ? "" : a.type === "chat" ? "tl-item--good" : "tl-item--muted";
            return (
              <div key={a.id} className={"tl-item " + mod}>
                <div className="row-between"><span className="tl-time">{fmtDateTime(a.at)} <span className="ict">ICT</span></span><span className="tl-type">{ACT_LABEL[a.type]}</span></div>
                <div className="tl-title">{window.DB.userById(a.user).short}: {a.text}</div>
                {a.order && <div className="tl-meta">Đơn liên quan: <span className="mono">{a.order}</span></div>}
                {a.conv && <button className="ghost-link" onClick={() => nav({ screen: "S06", conversation: a.conv })}>Xem hội thoại <Icon name="chevron" size={12} /></button>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── P04 Tasks ──────────────────────────────────────────── */
function P04_Tasks({ party, openModal, toast }) {
  const [done, setDone] = dUseState([]);
  const [filter, setFilter] = dUseState("open");
  let tasks = window.DB.tasks.filter((t) => t.party === party.id);
  if (filter === "open") tasks = tasks.filter((t) => t.status !== "done" || done.includes(t.id) === false);
  tasks = tasks.sort((a, b) => (a.due < b.due ? -1 : 1));
  return (
    <div className="stack stack-4">
      <div className="toolbar">
        <span className="panel-title">Tasks</span>
        <div className="flex-wrap">
          <FilterSelect label="Trạng thái" value={filter} onChange={setFilter} options={[{ value: "open", label: "Đang mở" }, { value: "all", label: "Tất cả" }]} />
          <button className="btn btn--secondary" style={{ padding: "8px 12px" }} onClick={() => openModal("M05", { party: party.id })}><Icon name="plus" size={13} /> Tạo task</button>
        </div>
      </div>
      {tasks.length === 0 ? <EmptyState icon="tasks" title="Không có task nào" sub="Tạo follow-up task cho khách này." /> : (
        <div className="wl-list">
          {tasks.map((t) => {
            const isDone = t.status === "done" || done.includes(t.id);
            return (
              <div key={t.id} className={"wl-row" + (isDone ? " wl-row--done" : "")} style={{ gridTemplateColumns: "auto 1fr auto" }}>
                <button className={"wl-check" + (isDone ? " wl-check--on" : "")} onClick={() => { setDone((d) => d.includes(t.id) ? d.filter((x) => x !== t.id) : [...d, t.id]); if (!isDone) toast("Đã hoàn thành task"); }}>{isDone && <Icon name="check" size={13} />}</button>
                <div className="wl-row__main">
                  <div className="wl-row__top">{t.source === "action_queue" && <span className="auto-tag">AUTO</span>}<span className="wl-row__name" style={{ cursor: "default" }}>{t.title}</span></div>
                  <div className="wl-row__meta">
                    <span className="wl-row__due"><Icon name="clock" size={11} /> {isDone && t.completed_at ? "Done: " + fmtDate(t.completed_at) : "Due: " + fmtDate(t.due)}</span>
                    <span className={"prio prio--" + t.priority}>{t.priority}</span>
                    <span className="muted" style={{ fontSize: 11 }}>{window.DB.userById(t.assignee).short}</span>
                  </div>
                </div>
                <button className="icon-btn icon-btn--sm" onClick={() => openModal("M05", { task: t.id, party: party.id })}><Icon name="edit" size={12} /></button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ── P05 Notes ──────────────────────────────────────────── */
function P05_Notes({ party, openModal }) {
  const notes = (window.DB.notes[party.id] || []).slice().sort((a, b) => (a.at < b.at ? 1 : -1));
  return (
    <div className="stack stack-4">
      <div className="toolbar"><span className="panel-title">Ghi chú</span><button className="btn btn--secondary" style={{ padding: "8px 12px" }} onClick={() => openModal("M08", { party: party.id, mode: "note_only" })}><Icon name="plus" size={13} /> Thêm ghi chú</button></div>
      {notes.length === 0 ? <EmptyState icon="doc" title="Chưa có ghi chú nào" sub="Notes là thông tin lâu dài về khách (khác activity timeline)." /> : (
        <div>
          {notes.map((n) => (
            <div key={n.id} className="note-card">
              <div className="note-card__head">
                <div className="note-card__who"><Avatar user={n.user} size={22} /> {window.DB.userById(n.user).short} <span className="note-card__when">· {fmtDateTime(n.at)} ICT</span></div>
                <div className="note-card__acts">
                  <button className="icon-btn icon-btn--sm" onClick={() => openModal("M08", { party: party.id, note_id: n.id, mode: "edit" })}><Icon name="edit" size={12} /></button>
                  <button className="icon-btn icon-btn--sm" onClick={() => openModal("O01", { confirm_type: "delete_note", note_id: n.id })}><Icon name="trash" size={12} /></button>
                </div>
              </div>
              <div className="note-card__body">{n.text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── P06 Conversations ──────────────────────────────────── */
function P06_Convs({ party, nav }) {
  const [filter, setFilter] = dUseState("all");
  let convs = window.DB.conversations.filter((c) => c.party === party.id);
  if (filter !== "all") convs = convs.filter((c) => c.status === filter);
  return (
    <div className="stack stack-4">
      <div className="toolbar"><span className="panel-title">Hội thoại · Messenger</span>
        <FilterSelect label="Trạng thái" value={filter} onChange={setFilter} options={[{ value: "all", label: "Tất cả" }, { value: "open", label: "open" }, { value: "pending", label: "pending" }, { value: "closed", label: "closed" }]} /></div>
      {convs.length === 0 ? <EmptyState icon="inbox" title="Chưa có hội thoại nào" sub="Khách này chưa link conversation Messenger nào." /> : (
        <div>
          {convs.map((c) => (
            <div key={c.id} className="note-card" style={{ marginBottom: "var(--sp-3)" }}>
              <div className="note-card__head">
                <div className="note-card__who"><Icon name="inbox" size={14} /> Messenger <span className="note-card__when">· {fmtDateTime(c.last_at)} ICT · {window.DB.userById(c.assignee).short} · {c.status}</span></div>
                <button className="ghost-link" onClick={() => nav({ screen: "S06", conversation: c.id })}>Xem <Icon name="chevron" size={12} /></button>
              </div>
              <div className="note-card__body">"{c.preview}"</div>
            </div>
          ))}
        </div>
      )}
      <div className="note-line"><span className="caveat__mark">R12</span><span>Messenger read-only v1 — chỉ ingest + hiển thị.</span></div>
    </div>
  );
}

Object.assign(window, { S03_Customer360 });

/* ============================================================
   Screens: S01 Worklist · S02 Customer List · S04 Dedup Review
   ============================================================ */
const { useState: wUseState, useMemo: wUseMemo } = React;

/* ── S01 — Worklist / Dashboard ─────────────────────────── */
function S01_Worklist({ nav, openModal, toast, openPreview }) {
  const [doneIds, setDoneIds] = wUseState([]);
  const [filters, setFilters] = wUseState(() => ({ ...WLF_DEFAULTS }));

  const partyOf = (t) => window.DB.partyById(t.party);
  const actOf = (t, p) => p && p.actions.find((x) => x.action_id === t.source_ref);

  let rows = window.DB.tasks.filter((t) => t.status !== "done" && t.status !== "cancelled");
  // Demo wiring — a few dims map to sample data so the list reacts;
  // type / strategic_tier / product are visual-only (no backing data here).
  if (filters.q.trim()) {
    const s = filters.q.toLowerCase();
    rows = rows.filter((t) => { const p = partyOf(t); return p && (p.name.toLowerCase().includes(s) || p.phone.includes(filters.q) || (p.code || "").toLowerCase().includes(s)); });
  }
  if (filters.priority === "urgent") rows = rows.filter((t) => t.priority === "P1");
  else if (filters.priority === "high") rows = rows.filter((t) => t.priority === "P1" || t.priority === "P2");
  if (filters.value_group) { const g = filters.value_group === "BRONZE" ? "NEW" : filters.value_group; rows = rows.filter((t) => { const p = partyOf(t); return p && p.group === g; }); }
  if (filters.min_value) rows = rows.filter((t) => { const p = partyOf(t); const a = actOf(t, p); return a && a.value >= 1000000; });
  if (filters.has_script) rows = rows.filter((t) => window.DB.scriptByParty(t.party));
  rows = rows.sort((a, b) => (a.due < b.due ? -1 : 1));

  const totalValue = rows.reduce((s, t) => {
    const p = window.DB.partyById(t.party); const a = p && p.actions.find((x) => x.action_id === t.source_ref);
    return s + (a ? a.value : 0);
  }, 0);
  const refreshed = "2026-06-14T00:15:00Z";

  const toggle = (id) => setDoneIds((d) => d.includes(id) ? d.filter((x) => x !== id) : [...d, id]);
  const allDone = rows.length > 0 && rows.every((r) => doneIds.includes(r.id));

  return (
    <div className="crm-page page-enter">
      <PageHead eyebrow="Worklist · hôm nay" title="Việc cần làm hôm nay"
        sub={`14/06/2026 ICT · ${rows.length} task được giao`}
        aside={<button className="btn btn--primary" onClick={() => openModal("M05", {})}><Icon name="plus" size={14} /> Tạo task</button>} />

      <div className="kpi-strip">
        <div className="kpi"><div className="kpi__label">Task mở</div><div className="kpi__val">{rows.length}</div></div>
        <div className="kpi"><div className="kpi__label">Đã xong</div><div className="kpi__val">{doneIds.length}</div></div>
        <div className="kpi"><div className="kpi__label">Giá trị tiềm năng</div><div className="kpi__val" style={{ fontSize: 20 }}>{fmtVNDShort(totalValue)}</div><div className="kpi__sub">value_at_stake</div></div>
        <div className="kpi"><div className="kpi__label">Ưu tiên P1</div><div className="kpi__val">{rows.filter((r) => r.priority === "P1").length}</div></div>
      </div>

      <WLFilterBar filters={filters} setFilters={setFilters} />

      {allDone ? (
        <EmptyState icon="check" title="Đã xong hết task hôm nay" sub="Tuyệt vời. Duyệt danh sách khách để tìm cơ hội mới." cta={<button className="btn btn--secondary" onClick={() => nav({ screen: "S02" })}>Duyệt khách hàng</button>} />
      ) : rows.length === 0 ? (
        <EmptyState icon="worklist" title="Hôm nay không có task nào" sub="Không có task được giao theo bộ lọc hiện tại." cta={<button className="btn btn--secondary" onClick={() => nav({ screen: "S02" })}>Duyệt khách hàng</button>} />
      ) : (
        <div className="wl-list">
          {rows.map((t) => {
            const p = window.DB.partyById(t.party);
            const act = p && p.actions.find((x) => x.action_id === t.source_ref);
            const done = doneIds.includes(t.id);
            const m = act ? window.ACTION_META[act.type] : null;
            return (
              <div key={t.id} className={"wl-row" + (done ? " wl-row--done" : "")}>
                <button className={"wl-check" + (done ? " wl-check--on" : "")} onClick={() => toggle(t.id)} aria-label="done">{done && <Icon name="check" size={13} />}</button>
                <div className="wl-row__main" onClick={() => nav({ screen: "S15", task: t.id })}>
                  <div className="wl-row__top">
                    {m && <Chip tone={m.tone}>{m.label}</Chip>}
                    {t.source === "action_queue" && !m && <span className="auto-tag">AUTO</span>}
                    <span className="wl-row__name" onClick={(e) => { e.stopPropagation(); openPreview && openPreview(p.id, e.currentTarget.getBoundingClientRect()); }}>{p ? p.name : t.title}</span>
                    {p && <span className="wl-row__phone">{p.phone}</span>}
                    {p && <GroupBadge group={p.group} />}
                  </div>
                  <div className="wl-row__why">{act ? act.rationale : t.title}</div>
                  <div className="wl-row__meta">
                    {act && act.value > 0 && <span className="wl-row__value"><Icon name="money" size={13} /> {fmtVND(act.value)}</span>}
                    <span className="wl-row__due"><Icon name="clock" size={11} /> Due: {sameDay(t.due) ? "Hôm nay" : fmtDate(t.due)}</span>
                    <span className={"prio prio--" + t.priority}>{t.priority}</span>
                  </div>
                </div>
                <div className="wl-row__aside">
                  {p && p.phone && (window.DB.scriptByParty(p.id)
                    ? <button className="btn btn--secondary" style={{ padding: "8px 12px" }} title="Vào chế độ gọi" onClick={() => nav({ screen: "S14", party: p.id })}><Icon name="phone" size={13} /></button>
                    : <button className="btn btn--secondary" style={{ padding: "8px 12px" }} onClick={() => toast("Đang gọi " + p.phone, "info")}><Icon name="phone" size={13} /></button>)}
                  <button className="btn btn--ghost" onClick={() => p && nav({ screen: "S03", party: p.id })} style={{ padding: "8px 10px" }}>Mở hồ sơ <Icon name="chevron" size={12} /></button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="row-between" style={{ paddingTop: "var(--sp-2)" }}>
        <FreshnessBadge plain table="wh_action_queue" at={refreshed} />
        <span className="caption">R2 · No-recompute · R8 · idempotent tasks</span>
      </div>
    </div>
  );
}
function sameDay(iso) { const p = window.ictParts(iso); return p.dd === "14" && p.mm === "06"; }

/* ── S02 — Customer List & Search ───────────────────────── */
function S02_CustomerList({ nav, openModal }) {
  const [q, setQ] = wUseState("");
  const [group, setGroup] = wUseState("all");
  const [status, setStatus] = wUseState("all");
  const [owner, setOwner] = wUseState("all");
  const [page, setPage] = wUseState(1);
  const perPage = 8;

  let rows = window.DB.parties.slice();
  if (q.trim()) { const s = q.toLowerCase(); rows = rows.filter((p) => p.name.toLowerCase().includes(s) || p.phone.includes(q) || (p.email || "").includes(s) || p.code.toLowerCase().includes(s)); }
  if (group !== "all") rows = rows.filter((p) => p.group === group);
  if (status !== "all") rows = rows.filter((p) => p.status === status);
  if (owner !== "all") rows = rows.filter((p) => (owner === "none" ? !p.owner : p.owner === owner));
  const pages = Math.max(1, Math.ceil(rows.length / perPage));
  const pageRows = rows.slice((page - 1) * perPage, page * perPage);

  const segCounts = ["GOLD", "VIP", "SILVER", "NEW"].map((g) => ({ g, n: window.DB.parties.filter((p) => p.group === g).length }));

  return (
    <div className="crm-page page-enter">
      <PageHead eyebrow="Khách hàng · M1" title="Danh sách & Tìm kiếm"
        sub={`${window.DB.parties.length} khách · FTS5 < 200ms`}
        aside={<button className="btn btn--primary" onClick={() => openModal("M02", { prefillName: q })}><Icon name="plus" size={14} /> Tạo mới</button>} />

      <div className="segcards">
        {segCounts.map(({ g, n }) => (
          <button key={g} className={"segcard" + (group === g ? " segcard--active" : "")} onClick={() => { setGroup(group === g ? "all" : g); setPage(1); }}
            style={group === g ? { borderColor: "var(--accent)" } : null}>
            <div className="segcard__top"><GroupBadge group={g} /></div>
            <div className="segcard__count">{n}<span className="segcard__count-u">khách</span></div>
            <div className="segcard__desc">{g === "GOLD" ? "Giá trị cao, mua đều" : g === "VIP" ? "LTV lớn nhất" : g === "SILVER" ? "Tiềm năng tăng trưởng" : "Mới gia nhập"}</div>
          </button>
        ))}
        <button className={"segcard" + (group === "all" ? " segcard--active" : "")} onClick={() => { setGroup("all"); setPage(1); }} style={group === "all" ? { borderColor: "var(--accent)" } : null}>
          <div className="segcard__top"><span className="caption">Tất cả</span></div>
          <div className="segcard__count">{window.DB.parties.length}<span className="segcard__count-u">base</span></div>
          <div className="segcard__desc">Toàn bộ active base</div>
        </button>
      </div>

      <div className="toolbar">
        <div className="toolbar__search">
          <Icon name="search" size={15} />
          <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="SĐT, tên, email, customer_code..." />
          {q && <button className="toolbar__clear" onClick={() => setQ("")}>✕</button>}
        </div>
        <div className="toolbar__filters">
          <FilterSelect label="Value group" value={group} onChange={(v) => { setGroup(v); setPage(1); }} options={[{ value: "all", label: "Tất cả" }, { value: "GOLD", label: "GOLD" }, { value: "VIP", label: "VIP" }, { value: "SILVER", label: "SILVER" }, { value: "NEW", label: "NEW" }]} />
          <FilterSelect label="Status" value={status} onChange={(v) => { setStatus(v); setPage(1); }} options={[{ value: "all", label: "Tất cả" }, { value: "active", label: "active" }, { value: "at_risk", label: "at_risk" }, { value: "churned", label: "churned" }]} />
          <FilterSelect label="Owner" value={owner} onChange={(v) => { setOwner(v); setPage(1); }} options={[{ value: "all", label: "Tất cả" }, ...window.DB.users.filter((u) => u.role === "sales").map((u) => ({ value: u.id, label: u.short })), { value: "none", label: "Chưa gán" }]} />
        </div>
      </div>

      {pageRows.length === 0 ? (
        <EmptyState icon="search" title="Không tìm thấy khách" sub="Thử nới lỏng bộ lọc hoặc tạo khách hàng mới." cta={<button className="btn btn--secondary" onClick={() => openModal("M02", { prefillName: q })}>Tạo khách mới</button>} />
      ) : (
        <div className="tbl-wrap tbl-wrap--scroll">
          <table className="tbl tbl--cust">
            <thead><tr><th>Họ tên</th><th>SĐT</th><th>Group</th><th>Status</th><th>Owner</th><th>Mua gần nhất</th><th className="th-go"></th></tr></thead>
            <tbody>
              {pageRows.map((p) => (
                <tr key={p.id} className="is-clickable" onClick={() => nav({ screen: "S03", party: p.id })}>
                  <td><span className="cell-strong">{p.name}</span><span className="cell-sub">{p.code}</span></td>
                  <td className="mono" style={{ color: "var(--fg-1)" }}>{p.phone}</td>
                  <td><GroupBadge group={p.group} /></td>
                  <td><StatusBadge status={p.status} /></td>
                  <td>{p.owner ? window.DB.userById(p.owner).short : <span className="dash">—</span>}</td>
                  <td className="mono" style={{ color: "var(--fg-muted)" }}>{fmtDateOnly(p.last_order)}</td>
                  <td className="td-go"><span className="go-arrow"><Icon name="chevron" size={13} /></span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="pager">
        <div className="pager__info">{rows.length} kết quả</div>
        <div className="pager__ctrls">
          <button className="pager__btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹ Trước</button>
          <span className="pager__pages">Trang {page}/{pages}</span>
          <button className="pager__btn" disabled={page >= pages} onClick={() => setPage(page + 1)}>Sau ›</button>
        </div>
      </div>
    </div>
  );
}

/* ── S04 — Dedup Review ─────────────────────────────────── */
function S04_Dedup({ nav, openModal, toast }) {
  const [rule, setRule] = wUseState("all");
  const [resolved, setResolved] = wUseState([]);
  let list = window.DB.dedup.filter((d) => !resolved.includes(d.id));
  if (rule !== "all") list = list.filter((d) => d.rule === rule);
  const [selId, setSelId] = wUseState(list[0] ? list[0].id : null);
  const sel = list.find((d) => d.id === selId) || list[0];

  const resolve = (id, msg) => { setResolved((r) => [...r, id]); const next = list.find((d) => d.id !== id); setSelId(next ? next.id : null); toast(msg); };

  return (
    <div className="crm-page page-enter">
      <PageHead eyebrow="Dedup Review · M1" title="Trùng lặp chờ duyệt"
        sub={`R9 · fuzzy → hàng đợi · R4 · merge có undo`}
        aside={<div className="flex-wrap"><Bdg tone="warn" dot>Pending: {list.length}</Bdg>
          <FilterSelect label="Match rule" value={rule} onChange={setRule} options={[{ value: "all", label: "Tất cả" }, { value: "exact_phone", label: "exact_phone" }, { value: "fuzzy_name", label: "fuzzy_name" }]} /></div>} />

      {list.length === 0 ? (
        <EmptyState icon="dedup" title="Không có trùng lặp nào cần xem xét" sub="Hàng đợi candidate đang trống. Dedup job chạy theo lô đêm." />
      ) : (
        <div className="dedup-grid">
          <div className="cand-list">
            {list.map((d) => (
              <div key={d.id} className={"cand-row" + (sel && sel.id === d.id ? " cand-row--active" : "")} onClick={() => setSelId(d.id)}>
                <div className="cand-row__top">
                  <span className="conv-row__unread" style={{ marginTop: 0 }} />
                  <span className="cand-row__names">{d.a.name} <span className="muted">vs</span> {d.b.name}</span>
                </div>
                <span className="cand-row__rule">{d.rule}</span>
              </div>
            ))}
          </div>

          {sel && (
            <div>
              <div className="dedup-compare">
                {[["A", sel.a, true], ["B", sel.b, false]].map(([k, party, survive]) => (
                  <div key={k} className={"dedup-card" + (survive ? " dedup-card--survive" : "")}>
                    <span className="dedup-card__tag">{survive ? <Bdg tone="accent">GIỮ LẠI · A</Bdg> : <Bdg>GỘP VÀO · B</Bdg>}</span>
                    <div className="name" style={{ fontSize: 18 }}>{party.name}</div>
                    <div className="facts" style={{ marginTop: 12 }}>
                      <div className="fact"><span className="fact__k">Sapo</span><span className="fact__v mono">{party.sapo}</span></div>
                      <div className="fact"><span className="fact__k">SĐT</span><span className="fact__v mono">{party.phone}</span></div>
                      <div className="fact"><span className="fact__k">Email</span><span className="fact__v">{party.email || <span className="dash">—</span>}</span></div>
                      <div className="fact"><span className="fact__k">Đơn</span><span className="fact__v mono">{party.orders}</span></div>
                      <div className="fact"><span className="fact__k">Activity</span><span className="fact__v mono">{party.activities}</span></div>
                    </div>
                    <button className="ghost-link" style={{ marginTop: 12 }} onClick={() => party.id.startsWith("p_0") && nav({ screen: "S03", party: party.id })}>Xem hồ sơ <Icon name="external" size={12} /></button>
                  </div>
                ))}
              </div>
              <div className="caveat caveat--rule caveat--info" style={{ marginTop: "var(--sp-4)" }}>
                Match rule: <b style={{ color: "var(--fg)" }}>{sel.rule}</b> · {sel.rule === "exact_phone" ? "SĐT khớp chính xác — đề xuất merge." : "Tên gần giống + prefix SĐT — cần NV xác nhận thủ công."}
              </div>
              <div className="dedup-detail-actions">
                <button className="btn btn--primary" onClick={() => openModal("M01", { candidate: sel })}><Icon name="merge" size={14} /> Merge A ← B</button>
                <button className="btn btn--secondary" onClick={() => resolve(sel.id, "Đã từ chối candidate")}>Reject</button>
                <button className="btn btn--ghost" onClick={() => { const next = list.find((d) => d.id !== sel.id); setSelId(next ? next.id : null); }} style={{ padding: "10px 14px" }}>Bỏ qua</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

Object.assign(window, { S01_Worklist, S02_CustomerList, S04_Dedup });

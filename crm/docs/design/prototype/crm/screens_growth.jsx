/* ============================================================
   S08 Segments · S09 Builder · S10 Campaigns · S11 Campaign
   detail · S12 Ads · S13 Settings
   ============================================================ */
const { useState: gUseState } = React;

/* ── S08 Segments List ──────────────────────────────────── */
function S08_Segments({ nav }) {
  const [q, setQ] = gUseState("");
  let rows = window.DB.segments.filter((s) => s.name.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="crm-page page-enter">
      <PageHead eyebrow="Segments · M6" title="Phân khúc khách hàng"
        sub="R1 · consent gating · R10 · re-eval mỗi lần materialize"
        aside={<button className="btn btn--primary" onClick={() => nav({ screen: "S09" })}><Icon name="plus" size={14} /> Tạo segment</button>} />
      <div className="toolbar">
        <div className="toolbar__search"><Icon name="search" size={15} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Tìm theo tên segment..." />{q && <button className="toolbar__clear" onClick={() => setQ("")}>✕</button>}</div>
      </div>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead><tr><th>Tên</th><th>Loại</th><th className="num-h">Thành viên</th><th>Cập nhật</th><th>Trạng thái</th><th className="th-go"></th></tr></thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id} className="is-clickable" onClick={() => nav({ screen: "S09", segment: s.id })}>
                <td><span className="cell-strong">{s.name}</span><span className="cell-sub">{s.rules.length} điều kiện</span></td>
                <td><Bdg tone={s.type === "dynamic" ? "accent" : ""}>{s.type}</Bdg></td>
                <td className="num cell-strong">{s.status === "materializing" ? <span className="spinner" style={{ display: "inline-block" }} /> : s.members}{s.excluded > 0 && <span className="cell-sub">−{s.excluded} consent</span>}</td>
                <td className="mono" style={{ color: "var(--fg-muted)" }}>{relTime(s.updated)}</td>
                <td>{s.status === "ready" ? <Bdg tone="good" dot>ready</Bdg> : s.status === "empty" ? <Bdg tone="warn" dot>0 members</Bdg> : <Bdg tone="accent" dot>đang tính…</Bdg>}</td>
                <td className="td-go"><span className="go-arrow"><Icon name="chevron" size={13} /></span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── S09 Segment Builder ────────────────────────────────── */
const FIELD_OPTS = [
  { v: "value_group", l: "value_group" }, { v: "customer_status", l: "customer_status" },
  { v: "recency_days", l: "recency_days" }, { v: "monetary_vnd", l: "monetary_vnd" },
  { v: "next_purchase_signal", l: "next_purchase_signal" }, { v: "tag", l: "tag" }, { v: "consent_contact", l: "consent_contact" },
];
function S09_Builder({ route, nav, toast }) {
  const editing = route.segment ? window.DB.segById(route.segment) : null;
  const [name, setName] = gUseState(editing ? editing.name : "");
  const [type, setType] = gUseState(editing ? editing.type : "dynamic");
  const [conds, setConds] = gUseState(editing ? editing.rules.map((r, i) => ({ id: i, ...r })) : [{ id: 0, field: "value_group", op: "=", val: "GOLD" }]);
  const [showList, setShowList] = gUseState(false);
  const previewN = editing ? editing.members : Math.max(0, 87 - conds.length * 12);
  const excluded = editing ? editing.excluded : 6;

  const addCond = () => setConds((c) => [...c, { id: Date.now(), field: "customer_status", op: "=", val: "at_risk" }]);
  const rmCond = (id) => setConds((c) => c.filter((x) => x.id !== id));
  const setCond = (id, k, v) => setConds((c) => c.map((x) => x.id === id ? { ...x, [k]: v } : x));

  return (
    <div className="crm-page page-enter">
      <div className="c360-topbar">
        <button className="c360-back" onClick={() => nav({ screen: "S08" })}><Icon name="back" size={14} /> Segments</button>
        <input className="inp" style={{ maxWidth: 320 }} value={name} onChange={(e) => setName(e.target.value)} placeholder="Tên segment..." />
        <div className="c360-actions">
          <div className="radioset">
            <label className={"radio-pill" + (type === "dynamic" ? " radio-pill--on" : "")} onClick={() => setType("dynamic")}><span className="radio-pill__dot" />Dynamic</label>
            <label className={"radio-pill" + (type === "static" ? " radio-pill--on" : "")} onClick={() => setType("static")}><span className="radio-pill__dot" />Static</label>
          </div>
        </div>
      </div>

      <div className="builder-grid">
        <div className="rule-editor">
          <div className="caption">Điều kiện (AND)</div>
          {conds.map((c, i) => (
            <React.Fragment key={c.id}>
              {i > 0 && <div className="cond-join"><span className="cond-join__line" /><span className="cond-join__pill">AND</span><span className="cond-join__line" /></div>}
              <div className="cond-row">
                <Select value={c.field} onChange={(e) => setCond(c.id, "field", e.target.value)}>{FIELD_OPTS.map((f) => <option key={f.v} value={f.v}>{f.l}</option>)}</Select>
                <Select value={c.op} onChange={(e) => setCond(c.id, "op", e.target.value)}><option value="=">=</option><option value="!=">≠</option><option value=">">&gt;</option><option value="<">&lt;</option></Select>
                <TextInput className="inp inp--mono" value={c.val} onChange={(e) => setCond(c.id, "val", e.target.value)} />
                <button className="cond-x" onClick={() => rmCond(c.id)}><Icon name="close" size={13} /></button>
              </div>
            </React.Fragment>
          ))}
          <button className="fchip" style={{ alignSelf: "flex-start", marginTop: "var(--sp-2)" }} onClick={addCond}><Icon name="plus" size={12} /> Thêm điều kiện</button>
          <div className="note-line"><span className="caveat__mark">JSON</span><span className="mono" style={{ fontSize: 11 }}>{JSON.stringify({ and: conds.map((c) => ({ [c.field]: { [c.op]: c.val } })) })}</span></div>
        </div>

        <div className="preview-panel">
          <div className="caption">Kết quả dự kiến</div>
          <div className="preview-big">{previewN}</div>
          <div className="muted" style={{ fontSize: 13, marginTop: -8 }}>khách khớp rule</div>
          {excluded > 0 && <div className="preview-excluded"><Icon name="warn" size={13} /> {excluded} bị loại do consent_contact=false (R10)</div>}
          {previewN === 0 && <div className="caveat caveat--warn">0 party khớp — cân nhắc nới rule trước khi lưu.</div>}
          <button className="ghost-link" onClick={() => setShowList(!showList)}>{showList ? "Ẩn" : "Preview"} danh sách <Icon name="chevdown" size={12} /></button>
          {showList && (
            <div>
              {window.DB.parties.slice(0, 5).map((p) => (
                <div key={p.id} className="member-mini"><span>{p.name}</span><GroupBadge group={p.group} /></div>
              ))}
            </div>
          )}
          <div className="divider" />
          <div className="flex-wrap">
            <button className="btn btn--ghost" onClick={() => nav({ screen: "S08" })} style={{ padding: "10px 12px" }}>Hủy</button>
            <button className="btn btn--primary" disabled={!name.trim() || conds.length === 0} onClick={() => { toast("Đã lưu & materialize segment"); nav({ screen: "S08" }); }}>Lưu & Materialize</button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── S10 Campaigns List ─────────────────────────────────── */
function S10_Campaigns({ nav, openModal }) {
  const [status, setStatus] = gUseState("all");
  let rows = window.DB.campaigns.slice();
  if (status !== "all") rows = rows.filter((c) => c.status === status);
  return (
    <div className="crm-page page-enter">
      <PageHead eyebrow="Chiến dịch · M6" title="Chiến dịch reactivation"
        aside={<button className="btn btn--primary" onClick={() => openModal("M07", {})}><Icon name="plus" size={14} /> Tạo chiến dịch</button>} />
      <FilterBar filters={[{ field: "status", label: "Trạng thái", options: [{ value: "all", label: "Tất cả" }, { value: "draft", label: "Draft" }, { value: "active", label: "Active" }, { value: "done", label: "Done" }] }]}
        values={{ status }} onChange={(f, v) => setStatus(v)} onClear={() => setStatus("all")} />
      {rows.length === 0 ? <EmptyState icon="campaigns" title="Chưa có chiến dịch nào" sub="Tạo chiến dịch đầu tiên từ một segment." cta={<button className="btn btn--secondary" onClick={() => openModal("M07", {})}>Tạo chiến dịch</button>} /> : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead><tr><th>Tên</th><th>Objective</th><th>Kênh</th><th className="num-h">Targets</th><th className="num-h">Converted</th><th className="num-h">Rate</th><th>Trạng thái</th><th className="th-go"></th></tr></thead>
            <tbody>
              {rows.map((c) => {
                const rate = c.targets_total ? ((c.converted / c.targets_total) * 100).toFixed(1) : null;
                return (
                  <tr key={c.id} className="is-clickable" onClick={() => nav({ screen: "S11", campaign: c.id })}>
                    <td><span className="cell-strong">{c.name}</span><span className="cell-sub">{window.DB.segById(c.segment).name}</span></td>
                    <td>{c.objective}</td>
                    <td className="muted">{c.channel}</td>
                    <td className="num">{c.targets_total}</td>
                    <td className="num cell-strong">{c.converted}</td>
                    <td className="num">{rate ? <span style={{ color: "var(--moss-500)" }}>{rate}%</span> : <span className="dash">—</span>}</td>
                    <td>{c.status === "active" ? <Bdg tone="good" dot>active</Bdg> : c.status === "draft" ? <Bdg dot>draft</Bdg> : <Bdg tone="accent" dot>done</Bdg>}</td>
                    <td className="td-go"><span className="go-arrow"><Icon name="chevron" size={13} /></span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ── S11 Campaign Detail / Targets ──────────────────────── */
const TARGET_STATUS = { queued: "", sent: "accent", responded: "warn", converted: "good", skipped: "" };
function S11_Campaign({ route, nav, openModal, toast }) {
  const c = window.DB.campaignById(route.campaign) || window.DB.campaigns[0];
  const [status, setStatus] = gUseState("all");
  let tgts = window.DB.targets[c.id] || [];
  if (status !== "all") tgts = tgts.filter((t) => t.status === status);
  const rate = c.targets_total ? ((c.converted / c.targets_total) * 100).toFixed(1) : "0";

  return (
    <div className="crm-page page-enter">
      <div className="c360-topbar">
        <button className="c360-back" onClick={() => nav({ screen: "S10" })}><Icon name="back" size={14} /> Chiến dịch</button>
        <div className="c360-id"><span className="c360-name" style={{ fontSize: 24 }}>{c.name}</span>
          {c.status === "active" ? <Bdg tone="good" dot>active</Bdg> : <Bdg dot>{c.status}</Bdg>}</div>
        <div className="c360-actions">
          <button className="btn btn--secondary" style={{ padding: "9px 14px" }} onClick={() => openModal("M07", { campaign: c.id })}><Icon name="edit" size={13} /> Sửa</button>
          {c.status === "draft" && <button className="btn btn--primary" style={{ padding: "9px 14px" }} onClick={() => toast("Đã kích hoạt chiến dịch")}><Icon name="bolt" size={13} /> Kích hoạt</button>}
        </div>
      </div>

      <div className="strip-stats">
        <div className="strip-stat"><div className="strip-stat__k caption">Targets</div><div className="strip-stat__v">{c.targets_total}</div></div>
        <div className="strip-stat"><div className="strip-stat__k caption">Sent</div><div className="strip-stat__v">{c.sent}</div></div>
        <div className="strip-stat"><div className="strip-stat__k caption">Responded</div><div className="strip-stat__v">{c.responded}</div></div>
        <div className="strip-stat"><div className="strip-stat__k caption">Converted</div><div className="strip-stat__v" style={{ color: "var(--moss-500)" }}>{c.converted}</div></div>
        <div className="strip-stat"><div className="strip-stat__k caption">Rate</div><div className="strip-stat__v">{rate}%</div></div>
      </div>
      <div className="caveat caveat--rule caveat--info">Doanh thu attributed: <b style={{ color: "var(--fg)" }}>{fmtVND(c.revenue)}</b> · R11 · order_code mới sau scheduled_at ICT</div>

      {tgts.length === 0 && c.status === "draft" ? (
        <EmptyState icon="campaigns" title="Chưa có target" sub="Segment có 0 member hoặc chiến dịch chưa kích hoạt." />
      ) : (
        <>
          <FilterBar filters={[{ field: "status", label: "Status", options: [{ value: "all", label: "Tất cả" }, ...Object.keys(TARGET_STATUS).map((s) => ({ value: s, label: s }))] }]}
            values={{ status }} onChange={(f, v) => setStatus(v)} onClear={() => setStatus("all")} />
          <div className="tbl-wrap">
            <table className="tbl">
              <thead><tr><th>Khách</th><th>Status</th><th>Assignee</th><th>Order code</th><th className="num-h">Revenue</th><th className="th-go"></th></tr></thead>
              <tbody>
                {tgts.map((t) => {
                  const p = window.DB.partyById(t.party);
                  return (
                    <tr key={t.id}>
                      <td className="is-clickable" onClick={() => nav({ screen: "S03", party: t.party })}><span className="cell-strong" style={{ cursor: "pointer" }}>{p ? p.name : t.party}</span></td>
                      <td><Bdg tone={TARGET_STATUS[t.status]} dot>{t.status}</Bdg></td>
                      <td className="muted">{window.DB.userById(t.assignee).short}</td>
                      <td className="mono">{t.order || <span className="dash">—</span>}</td>
                      <td className="num">{t.revenue ? fmtVND(t.revenue) : <span className="dash">—</span>}</td>
                      <td className="td-go">
                        {t.status !== "converted" && t.status !== "skipped" && (
                          <button className="ghost-link" style={{ fontSize: 11 }} onClick={() => openModal("M12", { target: t, campaignName: c.name })}>Ghi convert</button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

/* ── S12 Ads Tracking ───────────────────────────────────── */
function S12_Ads({ nav }) {
  const [selId, setSelId] = gUseState(window.DB.ads[0].id);
  const [showLeads, setShowLeads] = gUseState(false);
  const sel = window.DB.ads.find((a) => a.id === selId);
  const totalSpend = window.DB.ads.reduce((s, a) => s + a.spend, 0);
  const totalLeads = window.DB.ads.reduce((s, a) => s + a.leads, 0);
  const totalConv = window.DB.ads.reduce((s, a) => s + a.converted, 0);
  const totalRev = window.DB.ads.reduce((s, a) => s + a.revenue, 0);

  return (
    <div className="crm-page page-enter">
      <PageHead eyebrow="Ads · M6" title="Theo dõi quảng cáo"
        sub="R2 · no-recompute · ingest từ Python FB Ads job"
        aside={<div className="flex-wrap"><FilterSelect label="Date range" value="30d" onChange={() => {}} options={[{ value: "30d", label: "30 ngày" }, { value: "7d", label: "7 ngày" }]} />
          <FilterSelect label="Platform" value="fb" onChange={() => {}} options={[{ value: "fb", label: "Facebook" }]} /></div>} />

      <div className="ads-grid">
        <div>
          {window.DB.ads.map((a) => (
            <div key={a.id} className={"ad-card" + (selId === a.id ? " ad-card--active" : "")} onClick={() => setSelId(a.id)}>
              <div className="ad-card__head"><span className="ad-card__name">{a.name}</span><Bdg>{a.platform}</Bdg></div>
              <div className="ad-stats">
                <div><div className="ad-stat__k">Spend</div><div className="ad-stat__v">{fmtVNDShort(a.spend)}</div></div>
                <div><div className="ad-stat__k">Leads</div><div className="ad-stat__v">{a.leads}</div></div>
                <div><div className="ad-stat__k">CPC</div><div className="ad-stat__v">{fmtVNDShort(a.cpc)}</div></div>
                <div><div className="ad-stat__k">CPL</div><div className="ad-stat__v">{fmtVNDShort(a.cpl)}</div></div>
              </div>
            </div>
          ))}
          <div className="row-between" style={{ marginTop: "var(--sp-3)" }}><FreshnessBadge plain table="crm_ad_spend" at="2026-06-14T01:12:00Z" /></div>
        </div>

        <div className="stats-panel">
          <div className="caption">Tổng quan</div>
          <div className="money-line money-line--hero"><span className="money-line__label">Tổng spend</span><span className="money-line__val">{fmtVND(totalSpend)}</span></div>
          <div className="money-line"><span className="money-line__label">Tổng leads</span><span className="money-line__val">{totalLeads}</span></div>
          <div className="money-line"><span className="money-line__label">Conversion</span><span className="money-line__val">{((totalConv / totalLeads) * 100).toFixed(1)}%</span></div>
          <div className="money-line"><span className="money-line__label">Revenue attr.</span><span className="money-line__val" style={{ color: "var(--moss-500)" }}>{fmtVND(totalRev)}</span></div>
          <div className="divider" />
          <div className="row-between"><span className="caption">{sel.name} · leads</span><button className="ghost-link" onClick={() => setShowLeads(!showLeads)}>{showLeads ? "Ẩn" : "Xem"} <Icon name="chevdown" size={12} /></button></div>
          {showLeads && sel.leadList.map((l, i) => (
            <div key={i} className="member-mini">
              <span style={l.party ? { color: "var(--accent)", cursor: "pointer" } : { color: "var(--fg-muted)" }} onClick={() => l.party && nav({ screen: "S03", party: l.party })}>{l.name}</span>
              {l.converted ? <Bdg tone="good" dot>converted</Bdg> : <span className="muted" style={{ fontSize: 11 }}>{fmtDateOnly(l.at)}</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── S13 Settings ───────────────────────────────────────── */
function S13_Settings({ openModal, toast }) {
  const [sub, setSub] = gUseState("fields");
  const navItems = [{ id: "fields", label: "Custom Fields", icon: "doc" }, { id: "tags", label: "Tags", icon: "tag" }, { id: "users", label: "Người dùng", icon: "user" }];
  return (
    <div className="crm-page page-enter">
      <PageHead eyebrow="Cài đặt" title="Cấu hình hệ thống" />
      <div className="settings-grid">
        <div className="settings-nav">
          {navItems.map((it) => (
            <button key={it.id} className={"settings-nav__item" + (sub === it.id ? " settings-nav__item--on" : "")} onClick={() => setSub(it.id)}>
              <Icon name={it.icon} size={15} /> {it.label}
            </button>
          ))}
        </div>
        <div>
          {sub === "fields" && (
            <div className="stack stack-4">
              <div className="row-between"><span className="panel-title">Custom Fields</span><button className="btn btn--primary" style={{ padding: "9px 14px" }} onClick={() => openModal("M13", {})}><Icon name="plus" size={13} /> Thêm field</button></div>
              <div className="tbl-wrap">
                <table className="tbl"><thead><tr><th>Tên field</th><th>Slug</th><th>Loại</th><th>Bắt buộc</th><th className="th-go"></th></tr></thead>
                  <tbody>{window.DB.fieldDefs.map((f) => (
                    <tr key={f.id}><td className="cell-strong">{f.label}</td><td className="mono muted">{f.name}</td><td><Bdg>{f.type}</Bdg></td><td>{f.required ? "Có" : <span className="muted">Không</span>}</td>
                      <td className="td-go"><div className="flex-wrap" style={{ justifyContent: "flex-end" }}><button className="icon-btn icon-btn--sm" onClick={() => openModal("M13", { field_def: f.id })}><Icon name="edit" size={12} /></button><button className="icon-btn icon-btn--sm" onClick={() => openModal("O01", { confirm_type: "delete_field", field_def_id: f.id })}><Icon name="trash" size={12} /></button></div></td></tr>
                  ))}</tbody>
                </table>
              </div>
              <div className="note-line"><span className="caveat__mark">JSON1</span><span>Schema-less — thêm field mới không cần migration.</span></div>
            </div>
          )}
          {sub === "tags" && (
            <div className="stack stack-4">
              <div className="row-between"><span className="panel-title">Tags</span><button className="btn btn--primary" style={{ padding: "9px 14px" }} onClick={() => openModal("M14", {})}><Icon name="plus" size={13} /> Tạo tag</button></div>
              <div className="tbl-wrap"><table className="tbl"><thead><tr><th>Nhãn</th><th>Slug</th><th>Category</th><th>Màu</th></tr></thead>
                <tbody>{window.DB.tags.map((t) => (
                  <tr key={t.id}><td><Chip tone={t.tone === "default" ? "" : t.tone}>{t.label}</Chip></td><td className="mono muted">{t.name}</td><td>{t.category}</td><td><span className="lc__dot" style={{ display: "inline-block", background: t.tone === "amber" ? "var(--accent)" : t.tone === "moss" ? "var(--moss-500)" : t.tone === "coral" ? "var(--coral-500)" : "var(--honey-500)" }} /></td></tr>
                ))}</tbody></table></div>
            </div>
          )}
          {sub === "users" && (
            <div className="stack stack-4">
              <span className="panel-title">Người dùng & vai trò</span>
              <div className="tbl-wrap"><table className="tbl"><thead><tr><th>Tên</th><th>Vai trò</th><th className="th-go"></th></tr></thead>
                <tbody>{window.DB.users.map((u) => (
                  <tr key={u.id}><td><div className="flex-wrap"><Avatar user={u} size={24} /> {u.name}</div></td>
                    <td><div className="inp-sel" style={{ maxWidth: 160 }}><select defaultValue={u.role} onChange={() => toast("Đã cập nhật vai trò")}><option value="sales">sales</option><option value="care">care</option><option value="manager">manager</option><option value="admin">admin</option></select><span className="inp-sel__chev"><Icon name="chevdown" size={12} /></span></div></td>
                    <td className="td-go"></td></tr>
                ))}</tbody></table></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { S08_Segments, S09_Builder, S10_Campaigns, S11_Campaign, S12_Ads, S13_Settings });

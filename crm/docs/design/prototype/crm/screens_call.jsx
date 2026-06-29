/* ============================================================
   Screen: S14 — Call Mode / Strategy Cockpit
   Full-focus "đang gọi" cockpit. Reads cache.wh_approach_script
   (R2 — no recompute, show refreshed_at). recommended=false →
   STOP state (R14). Intentionally NO C01 sidebar (shell hides it).
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
  low: { label: "thấp", tone: "bad" },
};

/* ── Region heading strip ───────────────────────────────── */
function S14Head({ children, right }) {
  return (
    <div className="s14-rhead">
      <span className="s14-rhead__label">{children}</span>
      {right && <span className="s14-rhead__right">{right}</span>}
    </div>
  );
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
    </div>
  );
}

/* ── Loading skeleton ───────────────────────────────────── */
function S14Skeleton() {
  return (
    <div className="s14-wrap">
      <div className="s14-card s14-skel" style={{ height: 64 }} />
      <div className="s14-card s14-skel" style={{ height: 92 }} />
      <div className="s14-card s14-skel" style={{ height: 150 }} />
      <div className="s14-card s14-skel" style={{ height: 110 }} />
    </div>
  );
}

/* ── S14 — Call Mode Cockpit ────────────────────────────── */
function S14_CallMode({ route, nav, openModal, toast }) {
  const queue = window.DB.callQueue;
  const partyId = route.party || queue[0];
  const idx = Math.max(0, queue.indexOf(partyId));
  const party = window.DB.partyById(partyId);
  const script = window.DB.scriptByParty(partyId);

  // ST-LOADING: brief skeleton on each party change (simulate cache fetch)
  const [loading, setLoading] = cUseState(true);
  cUseEffect(() => {
    setLoading(true);
    const t = setTimeout(() => setLoading(false), 430);
    return () => clearTimeout(t);
  }, [partyId]);

  // interactive state
  const [channel, setChannel] = cUseState("primary"); // primary | fallback
  const [doneTP, setDoneTP] = cUseState([]);
  const [openObj, setOpenObj] = cUseState(null);
  const [objQ, setObjQ] = cUseState("");
  const [copied, setCopied] = cUseState(false);
  const [quickNote, setQuickNote] = cUseState(""); // ghi chú tạm — chép vào M08 khi ghi nhận kết quả

  cUseEffect(() => { // reset per party
    setChannel("primary"); setDoneTP([]); setOpenObj(null); setObjQ(""); setCopied(false); setQuickNote("");
  }, [partyId]);

  const nextParty = queue[(idx + 1) % queue.length];
  const goNext = () => nav({ screen: "S14", party: nextParty });

  if (loading) {
    return (
      <div className="s14-screen">
        <div className="s14-topbar">
          <button className="s14-back" onClick={() => nav({ screen: "S01" })}><Icon name="back" size={14} /> Worklist</button>
          <span className="s14-queue mono">#{idx + 1}/{queue.length}</span>
        </div>
        <S14Skeleton />
      </div>
    );
  }

  // ST-CALL-NO-SCRIPT
  if (!party || !script) {
    return (
      <div className="s14-screen">
        <div className="s14-topbar">
          <button className="s14-back" onClick={() => nav({ screen: "S01" })}><Icon name="back" size={14} /> Worklist</button>
          <span className="s14-queue mono">#{idx + 1}/{queue.length}</span>
        </div>
        <div className="s14-wrap">
          <EmptyState icon="doc" title="Chưa có kịch bản tiếp cận"
            sub={party ? `Chưa có row cache.wh_approach_script cho ${party.name}. Lô sinh kịch bản đêm chưa phủ khách này.` : "Không tìm thấy khách trong hàng đợi."}
            cta={<div className="flex-wrap" style={{ gap: 8, justifyContent: "center" }}>
              <button className="btn btn--secondary" onClick={() => nav({ screen: "S01" })}>Quay lại Worklist</button>
              {party && <button className="btn btn--ghost" onClick={() => nav({ screen: "S03", party: party.id })}>Xem hồ sơ 360</button>}
            </div>} />
        </div>
      </div>
    );
  }

  const ap = script.approach;
  const stale = window.hoursSince(script.refreshed_at) > 24;
  const lowConf = script.confidence === "low";
  const conf = CONF_META[script.confidence] || CONF_META.medium;
  const isStop = script.recommended === false;

  const opening = channel === "primary" ? ap.opening_message : ap.fallback_message;
  const chanLabel = channel === "primary" ? "Gọi điện" : "Zalo";

  const copyOpening = () => {
    const done = () => { setCopied(true); toast("Đã copy lời mở đầu", "success"); setTimeout(() => setCopied(false), 1500); };
    try { navigator.clipboard.writeText(opening).then(done, done); } catch (e) { done(); }
  };
  const toggleTP = (i) => setDoneTP((d) => d.includes(i) ? d.filter((x) => x !== i) : [...d, i]);

  const objections = (ap.objection_handling || []).filter((o) =>
    !objQ.trim() || (o.q + " " + o.a).toLowerCase().includes(objQ.toLowerCase()));

  const logOutcome = (kind, label) => {
    openModal("M08", { party: party.id, hinh_thuc: "call", source: "call_cockpit", outcome_hint: kind, body_prefill: quickNote.trim() });
    toast(`Ghi nhận: ${label}`, "info");
  };

  // ── TOPBAR + IDENTITY (shared chrome) ──────────────────
  const topbar = (
    <div className="s14-topbar">
      <button className="s14-back" onClick={() => nav({ screen: "S01" })}><Icon name="back" size={14} /> Worklist</button>
      <div className="s14-topbar__mid">
        <span className="s14-mode-dot" />
        <span className="s14-mode-label">CHẾ ĐỘ GỌI</span>
      </div>
      <span className="s14-queue mono">#{idx + 1}/{queue.length}</span>
    </div>
  );

  const identity = (
    <div className="s14-identity">
      <span className="s14-avatar">{party.name.trim().split(/\s+/).slice(-1)[0].slice(0, 1).toUpperCase()}</span>
      <div className="s14-identity__main">
        <div className="s14-identity__row">
          <span className="s14-identity__name">{party.name}</span>
          <GroupBadge group={party.group} />
          <Bdg>RETAIL</Bdg>
          {script.region !== "—" && <span className="s14-identity__region">· {script.region}</span>}
        </div>
        <div className="s14-identity__phone mono"><Icon name="phone" size={13} /> {maskPhone(party.phone)}</div>
      </div>
      <div className="s14-identity__act">
        <button className="btn btn--secondary" onClick={() => openModal("M08", { party: party.id, hinh_thuc: "call", mode: "contact_attempt", channel: "phone" })}><Icon name="phone" size={14} /> Gọi</button>
        <button className="btn btn--ghost" onClick={() => nav({ screen: "S03", party: party.id })}>Xem 360 <Icon name="chevron" size={12} /></button>
      </div>
    </div>
  );

  // ── RIGHT SIDEBAR (reference info — same vocabulary as S03) ──
  const ownerUser = party.owner ? window.DB.userById(party.owner) : null;
  const ins = party.insight || {};
  const sidebar = (
    <aside className="s14-side">
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
          <button className="ghost-link" onClick={() => nav({ screen: "S03", party: party.id })}>Hồ sơ 360 <Icon name="chevron" size={11} /></button>
        </div>
        <TagChips tagIds={party.tags} />
      </div>

      {ins.frequency != null && (
        <div className="scard">
          <div className="caption scard__eyebrow">Tóm tắt giá trị</div>
          <div className="facts">
            <div className="fact"><span className="fact__k">Recency</span><span className="fact__v mono">{ins.recency_days} ngày</span></div>
            <div className="fact"><span className="fact__k">Frequency</span><span className="fact__v mono">{ins.frequency} đơn</span></div>
            <div className="fact"><span className="fact__k">LTV</span><span className="fact__v mono">{window.fmtVNDShort(ins.monetary)}</span></div>
            <div className="fact"><span className="fact__k">Next signal</span><span className="fact__v">{ins.next_signal}</span></div>
            {ins.has_cogs
              ? <div className="fact"><span className="fact__k">Biên thực (R7)</span><span className="fact__v" style={{ color: "var(--moss-500)" }}>{ins.margin_pct}%</span></div>
              : <div className="fact"><span className="fact__k">Biên thực</span><span className="fact__v dash">— has_cogs ✗</span></div>}
          </div>
          {ins.refreshed_at && (
            <div style={{ marginTop: "var(--sp-3)", paddingTop: "var(--sp-3)", borderTop: "1px solid var(--border)" }}>
              <FreshnessBadge plain table="wh_customer_insight" at={ins.refreshed_at} />
            </div>
          )}
        </div>
      )}
    </aside>
  );

  return (
    <div className={"s14-screen" + (isStop ? " s14-screen--stop" : "")}>
      {topbar}
      <div className="s14-body">
        <div className="s14-main">
        {identity}

        {/* STRATEGY SUMMARY */}
        <div className="s14-card s14-summary">
          <div className="s14-summary__grid">
            <div className="s14-sig s14-sig--opp">
              <span className="s14-sig__dot" />
              <div><div className="s14-sig__k">Cơ hội</div><div className="s14-sig__v">{isStop ? "—" : script.opportunity}</div></div>
            </div>
            <div className="s14-sig s14-sig--risk">
              <span className="s14-sig__dot" />
              <div><div className="s14-sig__k">Rủi ro</div><div className="s14-sig__v">{isStop ? "—" : script.risk}</div></div>
            </div>
          </div>
          <div className="s14-summary__read">
            <span className="s14-summary__label">Chân dung</span> {script.profile_read}
          </div>
          <div className="s14-summary__foot">
            <span className="s14-meta-chip">{script.value_assessment}</span>
            {script.investment !== "—" && <span className="s14-meta-chip">Đầu tư: {script.investment}</span>}
          </div>
        </div>

        {isStop ? (
          /* ── ST-CALL-STOP (R14) ── */
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
            {script.data_gaps && script.data_gaps.length > 0 && (
              <div className="s14-stop__gaps">
                {script.data_gaps.map((g, i) => <span key={i} className="s14-gap">{g}</span>)}
              </div>
            )}
            <div className="s14-stop__act">
              <button className="btn btn--primary" onClick={() => openModal("M05", { party: party.id, source: "verify_account", prefill_title: "Xác minh loại tài khoản (nghi B2B)" })}>
                <Icon name="plus" size={14} /> Tạo task xác minh tài khoản
              </button>
              <button className="btn btn--ghost" onClick={() => nav({ screen: "S03", party: party.id })}>Xem hồ sơ 360</button>
            </div>
          </div>
        ) : (
          <>
            {/* TALK TRACK */}
            <div className="s14-block">
              <S14Head right={
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
              <S14Head right={<span className="s14-count mono">{doneTP.length}/{ap.talking_points.length}</span>}>Điểm nói · tick khi đã nói</S14Head>
              <div className="s14-tplist">
                {ap.talking_points.map((tp, i) => {
                  const on = doneTP.includes(i);
                  return (
                    <button key={i} className={"s14-tp" + (on ? " s14-tp--on" : "")} onClick={() => toggleTP(i)}>
                      <span className={"s14-tp__box" + (on ? " s14-tp__box--on" : "")}>{on && <Icon name="check" size={12} />}</span>
                      <span className="s14-tp__text">{tp}</span>
                    </button>
                  );
                })}
              </div>
              {ap.cross_sell && ap.cross_sell.length > 0 && (
                <div className="s14-cross">
                  <span className="s14-cross__label">Gợi thêm</span>
                  {ap.cross_sell.map((c, i) => <span key={i} className="s14-cross__chip">{c}</span>)}
                </div>
              )}
            </div>

            {/* OBJECTION HANDLING */}
            <div className="s14-block">
              <S14Head right={
                <div className="s14-objsearch">
                  <Icon name="search" size={12} />
                  <input value={objQ} onChange={(e) => setObjQ(e.target.value)} placeholder="khách vừa nói gì?" aria-label="Tìm tình huống" />
                  {objQ && <button className="s14-objsearch__x" onClick={() => setObjQ("")} aria-label="Xóa">✕</button>}
                </div>
              }>Xử lý từ chối</S14Head>
              <div className="s14-objlist">
                {objections.length === 0 ? (
                  <div className="s14-obj-empty">Không có tình huống khớp "{objQ}".</div>
                ) : objections.map((o, i) => (
                  <ObjectionCard key={i} obj={o} open={openObj === o.q} onToggle={() => setOpenObj(openObj === o.q ? null : o.q)} />
                ))}
              </div>
            </div>

            {/* GUARDRAILS */}
            <div className="s14-guard">
              <span className="s14-guard__sign"><Icon name="warn" size={14} /></span>
              <div className="s14-guard__list">
                {ap.do_not.map((d, i) => <span key={i} className="s14-guard__item">{d}</span>)}
              </div>
            </div>
          </>
        )}

        {/* TRUST FOOTER */}
        <div className="s14-trust">
          <span className="s14-trust__item">Độ tin: <b className={"s14-conf s14-conf--" + conf.tone}>{conf.label}</b></span>
          <span className="s14-trust__sep">·</span>
          <span className={"s14-trust__item" + (stale ? " s14-trust__item--stale" : "")} title={window.fmtDateTime(script.refreshed_at) + " ICT"}>
            {stale && <Icon name="warn" size={12} />} script {window.fmtDateTime(script.refreshed_at)} ICT {stale && "(quá 24h)"}
          </span>
          <span className="s14-trust__sep">·</span>
          <span className="s14-trust__caveat"><Icon name="warn" size={12} /> AI gợi ý — dùng phán đoán của bạn</span>
        </div>
        </div>{/* .s14-main */}
        {sidebar}
      </div>

      {/* OUTCOME BAR (sticky) */}
      {!isStop && (
        <div className="s14-outcome">
          <div className="s14-outcome__inner">
            <div className="s14-outcome__note">
              <textarea className="s14-quicknote" value={quickNote}
                onChange={(e) => setQuickNote(e.target.value)} rows={2}
                placeholder="Ghi chú tạm — gõ nhanh trong lúc gọi, tự chép vào nội dung khi ghi nhận kết quả…" />
            </div>
            <div className="s14-outcome__row">
              <div className="s14-outcome__btns">
                <button className="s14-oc s14-oc--good" onClick={() => logOutcome("answered", "Gọi được")}><Icon name="check" size={14} /> Gọi được</button>
                <button className="s14-oc s14-oc--miss" onClick={() => logOutcome("no_answer", "Không nghe")}><Icon name="close" size={14} /> Không nghe</button>
                <button className="s14-oc s14-oc--later" onClick={() => logOutcome("callback", "Hẹn lại")}><Icon name="clock" size={14} /> Hẹn lại</button>
                <button className="s14-oc s14-oc--buy" onClick={() => logOutcome("purchased", "Đã mua")}><Icon name="money" size={14} /> Đã mua</button>
              </div>
              <button className="btn btn--primary s14-next" onClick={goNext}>Khách kế <Icon name="chevron" size={13} /></button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

window.S14_CallMode = S14_CallMode;

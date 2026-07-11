---
id: S14
type: screen
name: "Call Mode / Strategy Cockpit"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R1, R2, R6, R14]
regions: [topbar, identity_bar, alert_row, strategy_summary, snapshot, talk_track, talking_points, objection_handling, guardrails, reason_to_call, collect, trust_footer, disposition_strip, stop_banner]
---

# S14 — Call Mode / Strategy Cockpit

## Purpose

**Operating console** cho Sales Rep trong lúc gọi — không chỉ show kịch bản mà gom đủ bối cảnh tác nghiệp vào đúng khoảnh khắc cuộc gọi. Tổ chức theo **3 pha**: TRƯỚC bấm gọi (ai / vì sao / cảnh giác) → TRONG khi nói (talk-track / điểm nói / xử lý từ chối) → SAU khi cúp máy (log outcome / hẹn lại).

Phân vùng không gian tách bạch **"vì sao gọi"** (RIGHT rail — action queue chiến lược, đọc trước khi quay số) khỏi **"nói gì"** (LEFT main — talk-track chiến thuật, tick dần khi nói). Kịch bản đọc qua `ApproachScriptRepository` (hiện tại: file JSON `{data_dir}/approach_scripts/{customer_id}.json`; tương lai có thể swap sang cache table — cùng port; R2 — CRM không tính lại, chỉ đọc + hiển thị `refreshed_at`).

**Hai host, một component:** lõi cockpit (`#s14-panel-root`) dùng chung cho cả:
- **Embedded** — tab "Gọi" trong S03 (`/customers/{id}/panels/call_cockpit`). Khi tab active, sidebar tĩnh của S03 bị ẩn (CSS `:has(#s14-panel-root)`) để cockpit chiếm full-width.
- **Full-screen** — route riêng `/customers/{id}/call`, vào từ S01 Worklist (nút "Vào chế độ gọi"). Thêm chrome topbar: `[← Worklist]` · queue counter `#n/N` · `[Khách kế →]`.
- **Từ Task Detail (S15)** — contact-task bấm "Vào phiên gọi" (A-S15-006) mở phiên gọi customer-grained này với **task context**: reason của task đó được ghim làm PRIMARY; sau khi log outcome, quay lại S15 (chrome "Khách kế →" đổi thành "Quay lại task"). Cockpit vẫn là 1 phiên/khách, không phải 1 phiên/task.

Khi `recommended=false` (nghi B2B gán nhầm / margin mâu thuẫn / chết-sâu margin âm) → **R14-WARN state** (Phase 05): sticky banner cảnh báo đỏ + nội dung che mờ (`s14-locked`). Nút "Tôi đã xác minh" (A-S14-027) ẩn banner + mở khoá nội dung (pure JS, ghi audit `r14_ack`). Identity bar + alert row + disposition strip luôn hiển thị.

## Data sourcing

Panel nạp (tất cả **cache SQLite, rẻ**): `party` (Party360), `identities` (crm_party_identity), `insight` (CacheInsight — RFM + action queue), `warning_notes`, `resolved_action_ids`, `script` (ApproachScriptRepository — file JSON), `meta`.

- **Kịch bản** (LEFT + guardrails): approach-script JSON (`ApproachScriptRepository`) — profile_read, value_assessment, opportunity, risk, approach{opening_message, fallback_message, talking_points[], cross_sell[], objection_handling[], do_not[], timing}, confidence, data_gaps, recommended. Pilot: JSON tĩnh cho tới khi batch ghi cache. Freshness: `refreshed_at` (R6 — ICT).
- **Vì sao gọi** (reason_to_call): `insight.actions` (ActionQueueItem: action_type, rationale_vi, value_at_stake_vnd, last_order_code, last_purchase_date, estimated_depletion_date) + `resolved_action_ids` + **open/doing CONTACT-TASKS** (`crm_task` kind=contact, party_id=current). Rail tổ chức thành 1 lý do PRIMARY (call trigger chín muồi nhất) + SECONDARY "tranh thủ nếu thuận" (sắp xếp theo ripeness). Read-context — claim/dismiss vẫn thuộc P01 (không rebuild ở cockpit). Disposition strip (finalize) resolve NHIỀU task_id/action_id cùng lúc (bulk); item nào backed bởi contact-task thì outcome **cập nhật luôn `task.status`** (đồng bộ với S15 — một nguồn sự thật).
- **Snapshot** (cache-first, DuckDB-fallback): dùng `insight.insight` (LTV `lifetime_contribution_margin`, AOV `avg_order_spend`, số đơn, chu kỳ `avg_days_between_orders`, recency). Nếu `insight` thiếu (None) → fallback `dim_metrics` (olap.duckdb, on-demand) để không rỗng. KHÔNG bê RFM grid / discount buckets / profitability — đó là P01.
- **Identity/kênh** (identity_bar + collect): `crm_party_identity` — kênh `is_preferred`, `contact_status` (active/invalid/unreachable), `display_label`.
- **Cảnh giác** (alert_row): `script.risk` + signals (`customer_status`, `is_high_cancel_risk`, `is_high_discount_sensitivity`, `is_margin_negative`) + `contact_status='invalid'` + `party.consent_contact` + `warning_notes` + chip **"liên hệ gần nhất X ngày"** (contact recency từ rollup activity log: `last_contacted_at`, `last_response_at`, `contact_attempts`, `response_count`, `responsiveness`). Engagement meta dùng cho chọn kênh; lưu trữ là impl phase riêng.
- **Thu thập còn thiếu** (collect): suy ra từ `identities` (thiếu zalo / email / số phụ) + `party.birthday|gender` trống + `script.data_gaps[]`. Inline write tái dùng M15 endpoints (`POST /customers/{id}/contact|core` với `inline=1` → trả fragment 1 dòng, KHÔNG re-render panel). Địa chỉ (nhiều field) → mở M15 tab=address thay vì inline.

## Layout

```yaml ui-layout
columns: [3fr, 2fr]
areas:
  - [identity_bar, identity_bar]
  - [alert_row, alert_row]
  - [talk_track, reason_to_call]
  - [strategy_summary, reason_to_call]
  - [talking_points, snapshot]
  - [objection_handling, collect]
  - [guardrails, collect]
  - [trust_footer, trust_footer]
  - [disposition_strip, disposition_strip]
floating:
  - region: stop_banner
    when: "recommended == false"
    replaces: [talk_track, strategy_summary, talking_points, objection_handling,
               guardrails, reason_to_call, snapshot, collect]
variants:
  full_screen:
    prepend_rows:
      - [topbar, topbar]
samples:
  topbar: "[← Worklist]  #9/31  [Khách kế →]"
  identity_bar: "Hoàng Thức [GOLD][active] · Miền Trung · ☎0983***35 [📞Gọi][💬Zalo] [360]"
  alert_row: "[sắp churn 11d] [cancel 32%] [SĐT phụ invalid] [liên hệ 3 ngày trước]"
  talk_track: "\"Dạ em chào anh Thức…\" [📋Copy]"
  strategy_summary: "⏱ Gọi 1-2 ngày, giờ hành chính"
  talking_points: "2/3 · ☑ Nhắc chu kỳ ☑ Ưu đãi ☐ Combo · Gợi thêm: [Omega3] [Vitamin D]"
  objection_handling: "▸ \"Chưa cần mua\" ▸ \"Giá sao?\" [🔍 khách vừa nói gì?]"
  guardrails: "⛔ không giảm sâu · không hứa giao nhanh"
  reason_to_call: "★ PRIMARY: REORDER · GT~1.2tr · quá chu kỳ 11d · #DH2093 [⏱Đặt lịch]"
  snapshot: "LTV 8.2tr · 3 đơn · 45d · gần nhất 11d"
  collect: "• Zalo [+] • Email [+] • Sinh nhật [+] • SĐT phụ invalid → [Sửa]"
  trust_footer: "độ tin vừa · script 24/6 07:15 ICT · ⚠ AI gợi ý, dùng phán đoán"
  disposition_strip: "T0 [📞Gọi ▾][⋯Ghi thủ công] · T1 ⏱[nháp autosave…]☑Zalo[■Kết thúc] · T2 [✓Nghe][🛒Mua][⏳Hẹn lại][✗Không bắt][☎Bận][🚫Từ chối][☠Sai số] · T3 ✓Đã lưu [Khách kế→]"
  stop_banner: "⛔ KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH · Lý do: ... · [Tạo task xác minh] [Xem hồ sơ 360] [Tôi đã xác minh — vẫn tiếp tục]"
elements:
  "📞Gọi": A-S14-006
  "360": A-S14-007
  "📋Copy": A-S14-001
  "⏱Đặt lịch": A-S14-024
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│IDENTITY_BAR                                                                │
│· Hoàng Thức [GOLD][active] · Miền Trung · T:0983***35 [>Gọi][~Zalo] [360]  │
├────────────────────────────────────────────────────────────────────────────┤
│ALERT_ROW                                                                   │
│· [sắp churn 11d] [cancel 32%] [SĐT phụ invalid] [liên hệ 3 ngày trước]     │
├─────────────────────────────────────────────┬──────────────────────────────┤
│TALK_TRACK                                   │REASON_TO_CALL                │
│· "Dạ em chào anh Thức…" [#Copy]             │· * PRIMARY: REORDER · GT~1.2…│
├─────────────────────────────────────────────┤                              │
│STRATEGY_SUMMARY                             │                              │
│· (t) Gọi 1-2 ngày, giờ hành chính           │                              │
├─────────────────────────────────────────────┼──────────────────────────────┤
│TALKING_POINTS                               │SNAPSHOT                      │
│· 2/3 · [x] Nhắc chu kỳ [x] Ưu đãi [ ] Combo…│· LTV 8.2tr · 3 đơn · 45d · g…│
├─────────────────────────────────────────────┼──────────────────────────────┤
│OBJECTION_HANDLING                           │COLLECT                       │
│· > "Chưa cần mua" > "Giá sao?" [(?) khách v…│· • Zalo [+] • Email [+] • Si…│
├─────────────────────────────────────────────┤                              │
│GUARDRAILS                                   │                              │
│· !! không giảm sâu · không hứa giao nhanh   │                              │
├─────────────────────────────────────────────┴──────────────────────────────┤
│TRUST_FOOTER                                                                │
│· độ tin vừa · script 24/6 07:15 ICT · ! AI gợi ý, dùng phán đoán           │
├────────────────────────────────────────────────────────────────────────────┤
│DISPOSITION_STRIP                                                           │
│· T0 [>Gọi v][⋯Ghi thủ công] · T1 (t)[nháp autosave…][x]Zalo[#Kết thúc] · T…│
└────────────────────────────────────────────────────────────────────────────┘

[variant: full_screen]
┌────────────────────────────────────────────────────────────────────────────┐
│TOPBAR                                                                      │
│· [← Worklist]  #9/31  [Khách kế →]                                         │
├────────────────────────────────────────────────────────────────────────────┤
│IDENTITY_BAR                                                                │
│· Hoàng Thức [GOLD][active] · Miền Trung · T:0983***35 [>Gọi][~Zalo] [360]  │
├────────────────────────────────────────────────────────────────────────────┤
│ALERT_ROW                                                                   │
│· [sắp churn 11d] [cancel 32%] [SĐT phụ invalid] [liên hệ 3 ngày trước]     │
├─────────────────────────────────────────────┬──────────────────────────────┤
│TALK_TRACK                                   │REASON_TO_CALL                │
│· "Dạ em chào anh Thức…" [#Copy]             │· * PRIMARY: REORDER · GT~1.2…│
├─────────────────────────────────────────────┤                              │
│STRATEGY_SUMMARY                             │                              │
│· (t) Gọi 1-2 ngày, giờ hành chính           │                              │
├─────────────────────────────────────────────┼──────────────────────────────┤
│TALKING_POINTS                               │SNAPSHOT                      │
│· 2/3 · [x] Nhắc chu kỳ [x] Ưu đãi [ ] Combo…│· LTV 8.2tr · 3 đơn · 45d · g…│
├─────────────────────────────────────────────┼──────────────────────────────┤
│OBJECTION_HANDLING                           │COLLECT                       │
│· > "Chưa cần mua" > "Giá sao?" [(?) khách v…│· • Zalo [+] • Email [+] • Si…│
├─────────────────────────────────────────────┤                              │
│GUARDRAILS                                   │                              │
│· !! không giảm sâu · không hứa giao nhanh   │                              │
├─────────────────────────────────────────────┴──────────────────────────────┤
│TRUST_FOOTER                                                                │
│· độ tin vừa · script 24/6 07:15 ICT · ! AI gợi ý, dùng phán đoán           │
├────────────────────────────────────────────────────────────────────────────┤
│DISPOSITION_STRIP                                                           │
│· T0 [>Gọi v][⋯Ghi thủ công] · T1 (t)[nháp autosave…][x]Zalo[#Kết thúc] · T…│
└────────────────────────────────────────────────────────────────────────────┘

[STOP variant — when: recommended == false]
┌────────────────────────────────────────────────────────────────────────────┐
│STOP_BANNER                                                                 │
│when: recommended == false                                                  │
│· !! KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH · Lý do: ... · [Tạo task xác mi…│
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

### Embedded trong S03 (tab "Gọi") — sidebar tĩnh S03 ẩn, cockpit full-width

### Full-screen (route `/customers/{id}/call`) — thêm topbar, lõi giữ nguyên

### R14-WARN state (recommended=false) — banner + locked content (Phase 05)

## Implementation Notes (Phase 04)

- **A2 — Queue counter wired**: `GET /customers/{id}/call` now accepts `queue_ids` (comma-joined party_id list, max 50) and `queue_pos` (int, default 0). Handler auto-corrects `queue_pos` by locating `party_id` in `queue_list.index()`. Template shows `#n/N` counter in topbar when `queue_total > 0` and "Khách kế →" links to next party with forwarded `queue_ids`. Queue nav is suppressed when `pinned_task_id` is set (S15 "Vào phiên gọi" returns to task, not next customer). When `queue_total == 0` (no queue context at all) the whole "Khách kế" control — including the `/customers` fallback link — does not render; only end-of-a-real-queue (`queue_total > 0` but `queue_next_party_id` is `None`) still shows the fallback link, since that case legitimately means "queue finished, browse customers".
- **A2 scope — full-page cockpit only**: the `#n/N` queue counter and "Khách kế →" control live in `call_cockpit.html` (topbar chrome), which only renders on the S01 → full-page cockpit entry path (`GET /customers/{id}/call`). The embedded S03 "Gọi" tab renders `fragments/c360_call_cockpit_panel.html` directly (no topbar, no queue context — a C360 tab visit is not a queue session). This is by design, not a gap.

## Implementation Notes (Phase 06)

- **Item 1 — Custom field collect rows**: `skin_type` + `preferred_contact` added as `custom_select` collect rows. Shown when `party.custom` JSON doesn't yet have the field. Pill click → `POST /customers/{id}/custom-field-inline` → `_s14_collect_row.html` swap. Fields whitelist-validated server-side.
- **Item 6 — Save toast**: `_s14_collect_row.html` appends self-removing `✓ Đã lưu` toast (2 s) when `saved=True` (returned by `custom-field-inline` handler).
- **Item 7 — Back-button tooltips**: `call_cockpit.html` back buttons and "Khách kế →" link now carry `title` attributes for discoverability.

## Implementation Notes (Phase 02 — 260706-0833 CRM Health Profile + Tag Governance)

- **Row 1 — `health_domain` collect row (`kind='tag_multiselect'`)**: shown when the party has zero `crm_party_tag` rows with `category='health_domain'` (checked via `load_health_domain_collect_context()` in `crm/src/application/health_domain_collect.py`, called from both `screen_call_cockpit.py` full-screen route and `screen_customer_360_panels.py` embedded panel route). Chips render the 8 canonical `health_domain` tags (`crm_tag WHERE category='health_domain' AND is_archived=0`, seeded migration 0041), ordered by attach-count desc. Multi-select toggle (`s14TagChipToggle`) enables a single **Lưu** button (`s14TagMultiSave`) that POSTs to the new inline endpoint. On success the row swaps to "✓ <label1>, <label2>" (fragment variant C in `_s14_collect_row.html`) and the gap clears (won't reappear once the party has ≥1 health_domain tag).
- **Row 2 — `health_context_raw` collect row (`kind='custom_text'`)**: shown when `party.custom.health_context_raw` is empty. Free-text input, `maxlength=200` (enforced both client-side and server-side), placeholder "huyết áp cao, hay mệt...". Reuses the existing `POST /customers/{id}/custom-field-inline` endpoint from Phase 06 (no new endpoint) — `health_context_raw` added to that handler's field whitelist. Saved state renders via fragment variant B (now covers `custom_select` and `custom_text`), 2 s self-removing toast.
- **New endpoint — `POST /customers/{party_id}/tags/inline`** (`crm/src/adapters/inbound/web/screens/modals/screen_modal_tags.py`): body `category` (Form) + `tag_names` (repeated Form field). **Hard whitelist**: `category` must be in `INLINE_ALLOWED_CATEGORIES = {"health_domain", "health_concern"}` — any other category → `400` before any DB lookup/write (prevents assigning sensitive categories like `risk`/`vip_tier` through this fast inline path; those still require the full M03 tag modal). Looks up `crm_tag` by `name` + `category`, attaches via `TagService.attach_tag(..., source="crm_user")` (now writes `crm_party_tag.source` explicitly rather than relying on the column default), returns the `_s14_collect_row.html` fragment with `saved=True`.
- **`skin_type` / `preferred_contact` unchanged**: both keep their Phase 06 `custom_select` behaviour untouched; the two new rows are additive only.

## Implementation Notes (Phase 03 — 260710 disposition strip v2)

- **`outcome_bar` → `disposition_strip`, 4-state machine**: replaces the old single-row static bar entirely (no dual code path kept — `s14OpenOutcome`/`s14QuickOutcomeVals`/etc removed from `c360_call_cockpit_panel.html`). One sticky-bottom fragment, JS toggles exactly one of 4 sub-blocks via `[hidden]` + `data-phase` on `#s14-strip`:
  - **T0** (before call, ~52px): `[📞 Gọi <số> ▾ số khác]` `[⋯ Ghi thủ công]`. Bấm 📞 = `s14StripStartCall()` → `POST /api/parties/{id}/call-sessions` (phase-02, idempotent per staff+party) → straight to T1, no modal.
  - **T1** (in call): `⏱ mm:ss` · draft note (`PATCH /api/activities/{id}` body, debounced 1.5s + on blur) · `☑ Zalo` (immediate PATCH `custom_fields.zalo_connected`) · `[⋯ Chi tiết]` (M08 `mode=edit_activity`) · `[■ Kết thúc]` → T2.
  - **T2** (disposition, ~96px w/o sheet): row1 = timer + note summary + `[Lưu & Khách kế →]` (disabled until a valid outcome is chosen); row2 = 7 pills in display order **Nghe(1)/Mua(2)/Hẹn lại(3)/Không bắt(4)/Bận(5)/Từ chối(6)/Sai số(7)** — the digit is also the keyboard shortcut. Pill click autosaves `contact_outcome` immediately (`PATCH`). Outcomes needing more info (`answered`/`purchased`/`callback`/`refused`/`wrong_number`) open a **sheet growing UP** (`#s14-strip-sheet`, max-height 180px, `position:absolute; bottom:100%`) over the now-dead talk_track/guardrails column — "phương án B" (swap the live left column instead) was considered and rejected (see ux-design report §IV.b: breaks the eye-anchor across 50 calls/week + a large-region re-render would violate Invariant §9). `refused`'s sheet requires a reason pill (6: còn hàng/chờ KM/giá/không hợp/kích ứng/mua chỗ khác — subset of `VALID_OUTCOME_REASONS`) before `[Lưu & Khách kế →]` enables; `[🚫 Đừng gọi nữa]` is an escalation button that sets `outcome_reason='do_not_contact'` (REFERENCE only — plan `260709-1638-crm-outreach-effort-report` owns any runtime suppression filter; no new party-level column added here).
  - **T3** (saved, no auto-advance): `✓ Đã lưu: <outcome> (<reason>) · <duration>` + `[Khách kế →]` (reuses `queue_total`/`queue_next_party_id` when present — full-screen host only, same A2 scope note above — else falls back to `/customers`). After `no_answer`, `[＋Nhắn Zalo]` appears (A-S14-028) — creates a **second, separate** activity via the existing `POST /customers/{id}/reason/resolve-async` (A-S14-026), never merged into the just-finalized call activity (multi-channel-per-session = 2 activities, per decision #3).
- **Keyboard shortcuts**: `1`-`7` pick the outcome pill at that display position; `Enter` triggers `[Lưu & Khách kế →]` when a valid outcome is selected. Both are guarded to fire **only** while `data-phase="t2"` and **never** while `document.activeElement` is a textarea/input/contenteditable — this is the only global `keydown` listener in the fragment (`s14ToggleTP`/`s14ToggleObj` bind via `onclick`, no conflict).
- **Mid-call reload recovery**: `build_draft_activity_ctx()` (`screen_call_cockpit.py`, shared by both cockpit hosts) looks up the current staff's open draft for this party and passes it as `draft_activity` into the template. On load, JS resumes **T1** (draft exists, no `contact_outcome` yet) or **T2** (outcome was already chosen before the reload) instead of restarting at T0 — never creates a second draft (`create_draft` is idempotent server-side too).
- **M08's role is now exactly two exceptions**: `[⋯ Ghi thủ công]` (T0, no draft — plain `mode=log`) and `[⋯ Chi tiết]` (T1/T2/T3, once a draft exists — `mode=edit_activity&activity_id=<draft>`, pre-filled). Every other outcome-logging path goes through the strip's own PATCH/finalize calls (plain `fetch()`, not `htmx.ajax` — mirrors the pattern phase-02's `s14StartCallSession` established; T3's displayed duration is the client timer's value at the moment "Lưu" was clicked, not re-fetched from the server, since both are computed within the same round-trip).
- **Known accepted gap**: `screen_customer_360_activity.py`'s legacy `POST /customers/{id}/log-activity` `source=call_cockpit` confirmation fragment still emits `onclick="s14OpenOutcome(...)"` (a function phase-03 removed from the template). This is unreachable dead code — nothing in the new strip sets `source=call_cockpit` any more (the 3 old quick-outcome buttons that did are gone) — left as-is because that Python file is outside phase-03's file-edit scope; tracked as a follow-up, not a live regression (existing tests for that route, e.g. `test_quick_outcome_cockpit_post.py`, only assert on the returned HTML string, not on the JS actually executing).

## Implementation Notes (Phase 04 — 260711 disposition strip CSS/merge fixes)

Live-tested with a real user against the running app; 3 issues found and fixed, all in `c360_call_cockpit_panel.html`/`ds-extra.css` (no port/service change):

- **`[hidden]` silently ignored on T0/T1/T3**: `.s14-strip__phase--row { display: flex }` (and `.s14-strip__sheetbody { display: flex }`) had no matching `[hidden]` override — author CSS beats the browser's default `[hidden]{display:none}` at equal specificity regardless of source order, so JS's `el.hidden = true` was a no-op for every phase/sheet-body carrying those classes. Symptom: T0's "Gọi" button, T1's timer/note/Kết thúc, and T3's "Đã lưu"/"Khách kế →" all rendered simultaneously from page load, and picking any of the 5 info-needing outcome pills opened ALL 5 sheet bodies at once instead of just the matching one. Fixed with `.s14-strip__phase[hidden]`/`.s14-strip__sheetbody[hidden] { display: none !important; }`.
- **Note summary blank on reload-into-T2**: `initPhase()`'s mid-call-reload-recovery path jumped straight to T2 when `DRAFT.contact_outcome` was already set, but only `s14StripEndCall()` (the manual T1→T2 transition) ever populated `#s14-strip-notesummary` — every reload that resumed straight into T2 showed a permanently blank summary line, with no visible sign the note itself wasn't lost. Fixed by adding the same summary-population logic to `initPhase()`'s T2-resume branch. (Superseded by the merge below — the summary line no longer exists.)
- **T1/T2 split actively harmful (user-reported, not originally a bug)**: once the `[hidden]` bug above was fixed and the two phases actually became mutually exclusive as designed, editing the note (T1) and picking/adjusting an outcome pill (T2) turned out to require bouncing back and forth via `[■ Kết thúc]`/`[sửa nháp]`, with no way to see or use both at once — a rep fixing a typo in the note lost the pills, and vice versa. **T1 and T2 merged into a single T1**: note stays a real editable textarea and the 7 outcome pills stay visible/pickable for the entire call, no toggle. `[■ Kết thúc]` removed (no distinct effect left once nothing swaps out); `[Lưu & Khách kế →]` is now the only end-of-call action. `[sửa nháp]` and `#s14-strip-notesummary` removed (textarea is always live, no summary needed). Keyboard shortcuts (`1`-`7`, `Enter`) now guard on `data-phase==="t1"` instead of `"t2"`. `initPhase()` simplified — no more separate "which sub-phase to resume into" branch, just `showPhase('t1')` unconditionally when a draft exists, then `restoreOutcomeSelection()` if an outcome was already chosen.
- **Screen is now a 3-state machine, not 4**: T0 (before call) → T1 (in call + disposition, merged) → T3 (saved). References to T2 elsewhere in this doc (Layout sample line, Interactions block below) predate this merge — kept as historical design record above per this doc's existing convention of leaving prior Implementation Notes sections unedited; T1's actual current shape is this section.

## States

- **ST-CALL-NO-SCRIPT**: không có file approach-script cho customer_id → empty + CTA Worklist / 360.
- **ST-CALL-R14-WARN**: `recommended=false` (R14) → sticky banner cảnh báo đỏ (`#s14-r14-banner`) + nội dung che mờ (`#s14-content.s14-locked`); talk-track/points/objection/rail render nhưng bị dim + pointer-events: none. Nút "Tôi đã xác minh" (A-S14-027) ẩn banner + xoá class s14-locked (pure JS, POST 204 → audit log).
- **ST-CALL-LOW-CONFIDENCE**: `confidence=low` → talk-track nhạt + nhãn "độ tin thấp, kiểm chứng".
- **ST-CALL-NO-ACTIONS**: `insight.actions` rỗng → rail "Vì sao gọi" hiện caveat "Không có đề xuất — dùng kịch bản".
- **ST-CALL-COLLECT-DONE**: sau khi bấm [+] ở dòng thu thập → dòng đó swap "✓ đã lưu" (client, không re-render panel).
- **ST-CALL-CONSENT-WARN** (R1): `consent_contact='denied'` → chip đỏ ở alert_row **nhưng KHÔNG chặn** nút Gọi/Zalo (chỉ cảnh báo; rep tự chịu trách nhiệm — quyết định sản phẩm, nới nhẹ R14 gating trên kênh gọi).
- Stale → dùng `ST-STALE-CACHE`; loading → `ST-LOADING`.

**Disposition strip (bulk resolve):** A-S14-009 (btn_log_outcome → finalize, phase-03) resolve được NHIỀU task_id/action_id cùng lúc — finalize nhận danh sách qua 2 hidden input (`#s14-resolve-action-ids`/`#s14-resolve-task-ids`) khi có nhiều context items trong phiên. `rail_primary` luôn nằm trong danh sách; mỗi `rail_secondary` item chỉ được gộp vào SAU KHI NV tick "đã nói" (A-S14-025) — tick vừa là ghi nhớ trực quan vừa là cơ chế chọn item để đóng cùng outcome.

**Async resolve (low-stakes items):** A-S14-026 cho phép resolve rail item thấp stakes qua Zalo/email trực tiếp từ rail (tái dùng channel toggle) mà không cần mở cuộc gọi.

## Interactions

```yaml crm-contract
interactions:
  - id: A-S14-001
    element: btn_copy_talk_track
    region: talk_track
    trigger: click
    action: mutate
    effects: [ui.clipboard.copy_opening_message]
  - id: A-S14-002
    element: toggle_channel
    region: talk_track
    trigger: click
    action: mutate
    effects: [talk_track.swap_channel_message]
  - id: A-S14-003
    element: talking_point_checkbox
    region: talking_points
    trigger: click
    action: mutate
    effects: [talking_point.toggle_done]
  - id: A-S14-004
    element: objection_card
    region: objection_handling
    trigger: click
    action: mutate
    effects: [objection.toggle_response]
  - id: A-S14-005
    element: objection_search
    region: objection_handling
    trigger: change
    action: mutate
    effects: [objection_handling.filter]
  - id: A-S14-006
    element: btn_call
    region: identity_bar
    trigger: click
    action: mutate
    effects: [activity_log.create_or_adopt_draft, disposition_strip.transition_t0_to_t1]
    # phase-03: KHÔNG còn mở M08 — tạo/adopt draft (POST /api/parties/{id}/call-sessions,
    # idempotent per staff+party) rồi chuyển thẳng disposition_strip sang T1 (timer chạy).
    # Cùng hàm JS (s14StripStartCall) với nút [📞Gọi] trong disposition_strip T0.
  - id: A-S14-007
    element: btn_view_360
    region: identity_bar
    trigger: click
    action: navigate
    target: S03
    payload: { party_id: "$party.id" }
  - id: A-S14-008
    element: btn_back_worklist
    region: topbar
    trigger: click
    action: navigate
    target: S01
  - id: A-S14-009
    element: btn_log_outcome
    region: disposition_strip
    trigger: click
    action: mutate
    effects: [activity_log.patch_contact_outcome, disposition_strip.transition_t1_to_t2]
    # phase-03: pill click trong T2 KHÔNG mở M08 nữa — PATCH /api/activities/{id}
    # contact_outcome=<key> ngay (autosave), pill cần thêm info thì sheet mọc LÊN TRÊN
    # (~180px). [⋯ Chi tiết] (mọi pha có draft) mới mở M08 (mode=edit_activity),
    # là exception duy nhất còn lại — xem Implementation Notes Phase 03.
  - id: A-S14-009b
    element: btn_save_and_next
    region: disposition_strip
    trigger: click
    action: mutate
    effects: [activity_log.finalize, disposition_strip.transition_t2_to_t3]
    # "Lưu & Khách kế →" (T2) — POST /api/activities/{id}/finalize; resolve_action_ids/
    # resolve_task_ids đọc từ 2 hidden input sẵn có (rail bulk-resolve, không đổi contract).
    # Phím tắt: 1-7 chọn pill theo thứ tự hiển thị, Enter = nút này (chỉ active ở T2,
    # không bắt khi đang gõ trong textarea/input — document.activeElement guard).
    # KHÔNG auto-advance sau khi lưu — T3 hiện "Khách kế →" nhưng phải bấm chủ động.
  - id: A-S14-010
    element: btn_next_in_queue
    region: disposition_strip
    trigger: click
    action: navigate
    target: S14
    payload: { party_id: "$queue.next_party_id" }
  - id: A-S14-011
    element: btn_verify_account
    region: stop_banner
    trigger: click
    action: open_overlay
    target: M05
    payload: { party_id: "$party.id", source: "verify_account", prefill_title: "Xác minh loại tài khoản (nghi B2B)" }
  - id: A-S14-020
    element: btn_collect_channel_add
    region: collect
    trigger: click
    action: mutate
    effects: [collect.channel.add_inline, collect.row.swap_done]
  - id: A-S14-021
    element: btn_collect_core_save
    region: collect
    trigger: click
    action: mutate
    effects: [collect.core_field.save_inline, collect.row.swap_done]
  - id: A-S14-022
    element: btn_collect_open_address
    region: collect
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "address" }
  - id: A-S14-023
    element: btn_fix_invalid_contact
    region: collect
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "contacts" }
  - id: A-S14-024
    element: btn_reason_schedule
    region: reason_to_call
    trigger: click
    action: open_overlay
    target: M05
    payload: { party_id: "$party.id", source: "action_queue", source_ref: "$action.action_id", prefill_title: "$action.title" }
  - id: A-S14-025
    element: reason_mentioned_checkbox
    region: reason_to_call
    trigger: click
    action: mutate
    effects: [reason.toggle_mentioned, disposition_strip.fold_secondary_id_into_bulk_resolve]
    # secondary items only; primary is always in the bulk-resolve set (server-rendered default)
  - id: A-S14-026
    element: btn_reason_resolve_async
    region: reason_to_call
    trigger: click
    action: mutate
    effects: [reason.resolve_via_async_channel, activity_log.append_async_attempt]
  - id: A-S14-027
    element: btn_r14_ack
    region: stop_banner
    trigger: click
    action: mutate
    effects: [stop_banner.hide, s14_content.unlock, activity_log.write_r14_ack]
    # POST /customers/{party_id}/r14-ack → 204; unlock is pure JS (Invariant §9, no panel re-render)
  - id: A-S14-028
    element: btn_zalo_followup
    region: disposition_strip
    trigger: click
    action: mutate
    effects: [activity_log.append_async_attempt]
    # phase-03, quyết định #3: chỉ hiện ở T3 sau khi outcome='no_answer' — tạo activity
    # THỨ HAI riêng biệt (không gộp field vào activity call vừa chốt). Tái dùng nguyên
    # A-S14-026 (POST /customers/{id}/reason/resolve-async), KHÔNG viết endpoint mới.
  - id: A-S14-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [script.reload, freshness_bar.update]
```

---
id: S14
type: screen
name: "Call Mode / Strategy Cockpit"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R1, R2, R6, R14]
regions: [topbar, identity_bar, alert_row, strategy_summary, snapshot, talk_track, talking_points, objection_handling, guardrails, reason_to_call, collect, trust_footer, outcome_bar, stop_banner]
---

# S14 — Call Mode / Strategy Cockpit

## Purpose

**Operating console** cho Sales Rep trong lúc gọi — không chỉ show kịch bản mà gom đủ bối cảnh tác nghiệp vào đúng khoảnh khắc cuộc gọi. Tổ chức theo **3 pha**: TRƯỚC bấm gọi (ai / vì sao / cảnh giác) → TRONG khi nói (talk-track / điểm nói / xử lý từ chối) → SAU khi cúp máy (log outcome / hẹn lại).

Phân vùng không gian tách bạch **"vì sao gọi"** (RIGHT rail — action queue chiến lược, đọc trước khi quay số) khỏi **"nói gì"** (LEFT main — talk-track chiến thuật, tick dần khi nói). Kịch bản đọc từ `cache.wh_approach_script` (keyed by `customer_id`; R2 — CRM không tính lại, chỉ đọc + hiển thị `refreshed_at`).

**Hai host, một component:** lõi cockpit (`#s14-panel-root`) dùng chung cho cả:
- **Embedded** — tab "Gọi" trong S03 (`/customers/{id}/panels/call_cockpit`). Khi tab active, sidebar tĩnh của S03 bị ẩn (CSS `:has(#s14-panel-root)`) để cockpit chiếm full-width.
- **Full-screen** — route riêng `/customers/{id}/call`, vào từ S01 Worklist (nút "Vào chế độ gọi"). Thêm chrome topbar: `[← Worklist]` · queue counter `#n/N` · `[Khách kế →]`.
- **Từ Task Detail (S15)** — contact-task bấm "Vào phiên gọi" (A-S15-006) mở phiên gọi customer-grained này với **task context**: reason của task đó được ghim làm PRIMARY; sau khi log outcome, quay lại S15 (chrome "Khách kế →" đổi thành "Quay lại task"). Cockpit vẫn là 1 phiên/khách, không phải 1 phiên/task.

Khi `recommended=false` (nghi B2B gán nhầm / margin mâu thuẫn / chết-sâu margin âm) → **R14-WARN state** (Phase 05): sticky banner cảnh báo đỏ + nội dung che mờ (`s14-locked`). Nút "Tôi đã xác minh" (A-S14-027) ẩn banner + mở khoá nội dung (pure JS, ghi audit `r14_ack`). Identity bar + alert row + outcome bar luôn hiển thị.

## Data sourcing

Panel nạp (tất cả **cache SQLite, rẻ**): `party` (Party360), `identities` (crm_party_identity), `insight` (CacheInsight — RFM + action queue), `warning_notes`, `resolved_action_ids`, `script` (wh_approach_script), `meta`.

- **Kịch bản** (LEFT + guardrails): `cache.wh_approach_script` — profile_read, value_assessment, opportunity, risk, approach{opening_message, fallback_message, talking_points[], cross_sell[], objection_handling[], do_not[], timing}, confidence, data_gaps, recommended. Pilot: JSON tĩnh cho tới khi batch ghi cache. Freshness: `refreshed_at` (R6 — ICT).
- **Vì sao gọi** (reason_to_call): `insight.actions` (ActionQueueItem: action_type, rationale_vi, value_at_stake_vnd, last_order_code, last_purchase_date, estimated_depletion_date) + `resolved_action_ids` + **open/doing CONTACT-TASKS** (`crm_task` kind=contact, party_id=current). Rail tổ chức thành 1 lý do PRIMARY (call trigger chín muồi nhất) + SECONDARY "tranh thủ nếu thuận" (sắp xếp theo ripeness). Read-context — claim/dismiss vẫn thuộc P01 (không rebuild ở cockpit). Outcome bar resolve NHIỀU task_id/action_id cùng lúc (bulk); item nào backed bởi contact-task thì outcome **cập nhật luôn `task.status`** (đồng bộ với S15 — một nguồn sự thật).
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
  - [outcome_bar, outcome_bar]
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
  outcome_bar: "[ghi chú tạm…] [✓Gọi được][✗Không nghe][⏳Hẹn lại][🛒Đã mua]"
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
│OUTCOME_BAR                                                                 │
│· [ghi chú tạm…] [vGọi được][xKhông nghe][(t)Hẹn lại][$Đã mua]              │
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
│OUTCOME_BAR                                                                 │
│· [ghi chú tạm…] [vGọi được][xKhông nghe][(t)Hẹn lại][$Đã mua]              │
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

```
┌ IDENTITY BAR ───────────────────────────────────────────────────────────┐
│ Hoàng Thức [GOLD][active] ·Miền Trung   ☎0983***35 [📞Gọi][💬Zalo] [360] │
├ ⚠ CẦN LƯU Ý (alert_row) ────────────────────────────────────────────────┤
│ [sắp churn 11d] [cancel 32%] [SĐT phụ invalid] [liên hệ 3 ngày trước]   │
├──────────────────────────────────────┬──────────────────────────────────┤
│ LEFT — NÓI GÌ (hot path)             │ RIGHT — VÌ SAO & BỐI CẢNH        │
│ ┌ Talk-track [📞Gọi][💬Zalo] ─────┐  │ ▸ VÌ SAO GỌI (reason_to_call)    │
│ │ "Dạ em chào anh Thức…"  [📋Copy]│  │  ★ PRIMARY (call trigger)         │
│ └──────────────────────────────────┘  │  ┌ REORDER · GT~1.2tr    [☐đã nói]│
│ ⏱ Gọi 1-2 ngày, giờ hành chính        │  │ Quá chu kỳ 11d · Shark…    │ │
│ ĐIỂM NÓI (tick khi đã nói)   2/3      │  │ #DH2093 · 24/5 [⏱Đặt lịch][✉]│ │
│                                       │  └────────────────────────────┘ │
│                                       │  ▾ SECONDARY "tranh thủ nếu thuận"│
│                                       │  ┌ WIN_BACK · GT~0.8tr  [☐đã nói]│
│                                       │  │ Chưa mua 45d         [✉Zalo]  │ │
│                                       │  └────────────────────────────┘ │
│  ☑ Nhắc chu kỳ  ☑ Ưu đãi  ☐ Combo    │ ▸ SNAPSHOT                       │
│  Gợi thêm: [Omega3] [Vitamin D]       │  LTV 8.2tr·3 đơn·45d·gần 11d    │
│ XỬ LÝ TỪ CHỐI  [🔍 khách vừa nói gì?] │  Chân dung: khách lẻ 3 đơn…     │
│  ▸ "Chưa cần mua"  ▸ "Giá sao?"       │ ▸ THU THẬP CÒN THIẾU (collect)  │
│ ⛔ GUARDRAILS: không giảm sâu · …     │  • Zalo  [__________] [+]        │
│                                       │  • Email [__________] [+]        │
│                                       │  • Sinh nhật [__/__/__] [+]      │
│                                       │  • SĐT phụ invalid → [Sửa]       │
├──────────────────────────────────────┴──────────────────────────────────┤
│ TRUST: độ tin vừa · script 24/6 07:15 ICT · ⚠ AI gợi ý, dùng phán đoán  │
├ OUTCOME BAR (sticky) ────────────────────────────────────────────────────┤
│ [ghi chú tạm…]  [✓Gọi được][✗Không nghe][⏳Hẹn lại][🛒Đã mua]           │
└──────────────────────────────────────────────────────────────────────────┘
```

### Full-screen (route `/customers/{id}/call`) — thêm topbar, lõi giữ nguyên

```
┌ TOPBAR ────────────── [← Worklist]   #9/31   [Khách kế →] ┐
│  … NGUYÊN KHỐI cockpit ở trên (identity_bar → outcome_bar) …│
└────────────────────────────────────────────────────────────┘
```

### R14-WARN state (recommended=false) — banner + locked content (Phase 05)

```
┌ ⛔ KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH (sticky banner) ─────────────┐
│ Lý do: nghi tổ chức gán nhầm RETAIL; margin mâu thuẫn; chết 1073 ngày.  │
│ [Tạo task xác minh]  [Xem hồ sơ 360]  [Tôi đã xác minh — vẫn tiếp tục] │
├──────────────────────────────────────┬──────────────────────────────────┤
│ (dim) TALK_TRACK / TALKING_POINTS …  │ (dim) REASON_TO_CALL / SNAPSHOT … │
│ opacity: 0.35, pointer-events: none  │ unlock → click btn_r14_ack above  │
└──────────────────────────────────────┴──────────────────────────────────┘
│ OUTCOME BAR (always accessible)                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Implementation Notes (Phase 04)

- **A2 — Queue counter wired**: `GET /customers/{id}/call` now accepts `queue_ids` (comma-joined party_id list, max 50) and `queue_pos` (int, default 0). Handler auto-corrects `queue_pos` by locating `party_id` in `queue_list.index()`. Template shows `#n/N` counter in topbar when `queue_total > 0` and "Khách kế →" links to next party with forwarded `queue_ids`. Queue nav is suppressed when `pinned_task_id` is set (S15 "Vào phiên gọi" returns to task, not next customer).

## Implementation Notes (Phase 06)

- **Item 1 — Custom field collect rows**: `skin_type` + `preferred_contact` added as `custom_select` collect rows. Shown when `party.custom` JSON doesn't yet have the field. Pill click → `POST /customers/{id}/custom-field-inline` → `_s14_collect_row.html` swap. Fields whitelist-validated server-side.
- **Item 6 — Save toast**: `_s14_collect_row.html` appends self-removing `✓ Đã lưu` toast (2 s) when `saved=True` (returned by `custom-field-inline` handler).
- **Item 7 — Back-button tooltips**: `call_cockpit.html` back buttons and "Khách kế →" link now carry `title` attributes for discoverability.

## States

- **ST-CALL-NO-SCRIPT**: không có row `cache.wh_approach_script` cho customer_id → empty + CTA Worklist / 360.
- **ST-CALL-R14-WARN**: `recommended=false` (R14) → sticky banner cảnh báo đỏ (`#s14-r14-banner`) + nội dung che mờ (`#s14-content.s14-locked`); talk-track/points/objection/rail render nhưng bị dim + pointer-events: none. Nút "Tôi đã xác minh" (A-S14-027) ẩn banner + xoá class s14-locked (pure JS, POST 204 → audit log).
- **ST-CALL-LOW-CONFIDENCE**: `confidence=low` → talk-track nhạt + nhãn "độ tin thấp, kiểm chứng".
- **ST-CALL-NO-ACTIONS**: `insight.actions` rỗng → rail "Vì sao gọi" hiện caveat "Không có đề xuất — dùng kịch bản".
- **ST-CALL-COLLECT-DONE**: sau khi bấm [+] ở dòng thu thập → dòng đó swap "✓ đã lưu" (client, không re-render panel).
- **ST-CALL-CONSENT-WARN** (R1): `consent_contact='denied'` → chip đỏ ở alert_row **nhưng KHÔNG chặn** nút Gọi/Zalo (chỉ cảnh báo; rep tự chịu trách nhiệm — quyết định sản phẩm, nới nhẹ R14 gating trên kênh gọi).
- Stale → dùng `ST-STALE-CACHE`; loading → `ST-LOADING`.

**Outcome bar (bulk resolve):** A-S14-009 (btn_log_outcome → M08) resolve được NHIỀU task_id/action_id cùng lúc — M08 payload nhận danh sách khi có nhiều context items trong phiên.

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
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id", mode: "contact_attempt", channel: "phone" }
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
    region: outcome_bar
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id", mode: "outcome", source: "call_cockpit" }
    # phase-02: truyền resolve_action_ids / resolve_task_ids qua query string → M08 forward vào form ẩn.
  - id: A-S14-010
    element: btn_next_in_queue
    region: outcome_bar
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
    effects: [reason.toggle_mentioned]
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
  - id: A-S14-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [script.reload, freshness_bar.update]
```

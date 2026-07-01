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

Khi `recommended=false` (nghi B2B gán nhầm / margin mâu thuẫn / chết-sâu margin âm) → **STOP state** (R14): ẩn talk-track + rail, chỉ chừa identity + alert + CTA xác minh tài khoản.

## Data sourcing

Panel nạp (tất cả **cache SQLite, rẻ**): `party` (Party360), `identities` (crm_party_identity), `insight` (CacheInsight — RFM + action queue), `warning_notes`, `resolved_action_ids`, `script` (wh_approach_script), `meta`.

- **Kịch bản** (LEFT + guardrails): `cache.wh_approach_script` — profile_read, value_assessment, opportunity, risk, approach{opening_message, fallback_message, talking_points[], cross_sell[], objection_handling[], do_not[], timing}, confidence, data_gaps, recommended. Pilot: JSON tĩnh cho tới khi batch ghi cache. Freshness: `refreshed_at` (R6 — ICT).
- **Vì sao gọi** (reason_to_call): `insight.actions` (ActionQueueItem: action_type, rationale_vi, value_at_stake_vnd, last_order_code, last_purchase_date, estimated_depletion_date) + `resolved_action_ids`. Read-context — claim/dismiss vẫn thuộc P01 (không rebuild ở cockpit).
- **Snapshot** (cache-first, DuckDB-fallback): dùng `insight.insight` (LTV `lifetime_contribution_margin`, AOV `avg_order_spend`, số đơn, chu kỳ `avg_days_between_orders`, recency). Nếu `insight` thiếu (None) → fallback `dim_metrics` (olap.duckdb, on-demand) để không rỗng. KHÔNG bê RFM grid / discount buckets / profitability — đó là P01.
- **Identity/kênh** (identity_bar + collect): `crm_party_identity` — kênh `is_preferred`, `contact_status` (active/invalid/unreachable), `display_label`.
- **Cảnh giác** (alert_row): `script.risk` + signals (`customer_status`, `is_high_cancel_risk`, `is_high_discount_sensitivity`, `is_margin_negative`) + `contact_status='invalid'` + `party.consent_contact` + `warning_notes`.
- **Thu thập còn thiếu** (collect): suy ra từ `identities` (thiếu zalo / email / số phụ) + `party.birthday|gender` trống + `script.data_gaps[]`. Inline write tái dùng M15 endpoints (`POST /customers/{id}/contact|core` với `inline=1` → trả fragment 1 dòng, KHÔNG re-render panel). Địa chỉ (nhiều field) → mở M15 tab=address thay vì inline.

## Layout

### Embedded trong S03 (tab "Gọi") — sidebar tĩnh S03 ẩn, cockpit full-width

```
┌ IDENTITY BAR ───────────────────────────────────────────────────────────┐
│ Hoàng Thức [GOLD][active] ·Miền Trung   ☎0983***35 [📞Gọi][💬Zalo] [360] │
├ ⚠ CẦN LƯU Ý (alert_row) ────────────────────────────────────────────────┤
│ [sắp churn 11d] [cancel 32%] [SĐT phụ invalid] [consent: OK]             │
├──────────────────────────────────────┬──────────────────────────────────┤
│ LEFT — NÓI GÌ (hot path)             │ RIGHT — VÌ SAO & BỐI CẢNH        │
│ ┌ Talk-track [📞Gọi][💬Zalo] ─────┐  │ ▸ VÌ SAO GỌI (reason_to_call)    │
│ │ "Dạ em chào anh Thức…"  [📋Copy]│  │  ┌ REORDER · GT~1.2tr    [☐đã nói]│
│ └──────────────────────────────────┘  │  │ Quá chu kỳ 11d · Shark…    │ │
│ ⏱ Gọi 1-2 ngày, giờ hành chính        │  │ #DH2093 · 24/5   [⏱Đặt lịch]│ │
│ ĐIỂM NÓI (tick khi đã nói)   2/3      │  └────────────────────────────┘ │
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

### STOP state (recommended=false) — thay LEFT+RIGHT

```
┌ ⛔ KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH ──────────────────────────────┐
│ Lý do: nghi tổ chức gán nhầm RETAIL; margin mâu thuẫn; chết 1073 ngày.  │
│ [Tạo task xác minh tài khoản]   [Xem hồ sơ 360]                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## States

- **ST-CALL-NO-SCRIPT**: không có row `cache.wh_approach_script` cho customer_id → empty + CTA Worklist / 360.
- **ST-CALL-STOP**: `recommended=false` (R14) → STOP banner; ẩn talk-track/points/objection/rail.
- **ST-CALL-LOW-CONFIDENCE**: `confidence=low` → talk-track nhạt + nhãn "độ tin thấp, kiểm chứng".
- **ST-CALL-NO-ACTIONS**: `insight.actions` rỗng → rail "Vì sao gọi" hiện caveat "Không có đề xuất — dùng kịch bản".
- **ST-CALL-COLLECT-DONE**: sau khi bấm [+] ở dòng thu thập → dòng đó swap "✓ đã lưu" (client, không re-render panel).
- **ST-CALL-CONSENT-WARN** (R1): `consent_contact='denied'` → chip đỏ ở alert_row **nhưng KHÔNG chặn** nút Gọi/Zalo (chỉ cảnh báo; rep tự chịu trách nhiệm — quyết định sản phẩm, nới nhẹ R14 gating trên kênh gọi).
- Stale → dùng `ST-STALE-CACHE`; loading → `ST-LOADING`.

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
  - id: A-S14-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [script.reload, freshness_bar.update]
```

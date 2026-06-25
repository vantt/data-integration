---
id: S14
type: screen
name: "Call Mode / Strategy Cockpit"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R1, R2, R6, R14]
regions: [topbar, identity_bar, strategy_summary, talk_track, talking_points, objection_handling, guardrails, trust_footer, outcome_bar, stop_banner]
---

# S14 — Call Mode / Strategy Cockpit

## Purpose

Màn hình "chế độ gọi" toàn-tập-trung cho Sales Rep, vào từ S01 Worklist (bấm "Vào chế độ gọi" trên task row) hoặc từ S03. Hiển thị **kịch bản tiếp cận do AI sinh** cho đúng khách đang gọi — đọc từ `cache.wh_approach_script` (keyed by `customer_id`; R2 — CRM không tính lại, chỉ đọc + hiển thị `refreshed_at`).

Khác P01 Insight Panel (RFM/value/signals để *nghiên cứu*), S14 là cockpit *trong lúc đang nói chuyện*: talk-track là chủ đạo, objection-handling tra cứu tức thì, do_not luôn hiện, log outcome ngay. Cố ý KHÔNG render sidebar (C01) để không phân tâm.

Khi kịch bản có `recommended=false` (nghi B2B gán nhầm / margin mâu thuẫn / chết-sâu margin âm) → toàn màn vào **STOP state** (R14): ẩn talk-track, hiện cảnh báo + lý do + CTA xác minh tài khoản.

## Data sourcing

- Kịch bản: `cache.wh_approach_script` row cho `customer_id` (JSON: profile_read, value_assessment, opportunity, risk, approach{primary_channel, fallback_channel, opening_message, fallback_message, talking_points[], cross_sell[], objection_handling[], do_not[]}, confidence, data_gaps, recommended).
- Pilot: 31 file JSON tĩnh trong `plans/.../pilot-run-1/scripts/` cho tới khi pipeline batch ghi vào cache.
- Identity/phone/kênh: `crm_party` + `crm_party_identity` (kênh `is_preferred`).
- Freshness: `refreshed_at` của script (R6 — hiển thị ICT).

## Layout

```
┌ TOPBAR ─────────────────────────────────────────── [← Worklist]  #9/31 ┐
├ IDENTITY ───────────────────────────────────────────────────────────────┤
│ Hoàng Thức   [RETAIL] [GOLD]  · Miền Trung   ☎ 0983****35 [Gọi] [Xem 360]│
├ STRATEGY SUMMARY ───────────────────────────────────────────────────────┤
│ 🟢 Cơ hội: nhắc mua lại Shark Cartilage   🟡 Rủi ro: sắp churn           │
│ Chân dung: khách lẻ 3 đơn, đã qua chu kỳ 11 ngày…   · đầu tư: TB         │
├ TALK TRACK ────────────────────────────── [📞 Gọi] [💬 Zalo]  (đổi kênh) ┤
│ ╔═════════════════════════════════════════════════════════╗            │
│ ║ "Dạ em chào anh Thức, em gọi từ cửa hàng…"   [📋 Copy]  ║            │
│ ╚═════════════════════════════════════════════════════════╝            │
│ ⏱ Gọi trong 1-2 ngày, giờ hành chính                                    │
├ TALKING POINTS (tick khi đã nói) ───────────────────────────────────────┤
│ ☐ Nhắc chu kỳ dùng   ☐ Ưu đãi khách quen   ☐ Gợi combo 2 hộp           │
├ OBJECTION HANDLING ───────────────────────── [🔍 khách vừa nói gì?]     │
│ ▸ "Chưa cần mua"   → bấm để xem câu trả lời                             │
│ ▸ "Giá sao?"       → bấm để xem câu trả lời                             │
├ GUARDRAILS (luôn hiện) ─────────────────────────────────────────────────┤
│ ⛔ Không giảm sâu (biên mỏng) · Không gọi như khách mới                  │
├ TRUST ──────────────────────────────────────────────────────────────────┤
│ Độ tin: vừa · script 24/6 07:15 ICT · ⚠ AI gợi ý, dùng phán đoán       │
├ OUTCOME BAR ────────────────────────────────────────────────────────────┤
│ [✓ Gọi được] [✗ Không nghe] [⏳ Hẹn lại] [🛒 Đã mua]      [Khách kế →] │
└─────────────────────────────────────────────────────────────────────────┘

STOP STATE (recommended=false) — thay toàn bộ talk-track:
┌ ⛔ KHÔNG GỌI THEO KỊCH BẢN — CẦN XÁC MINH ──────────────────────────────┐
│ Lý do: tên "Leflair" nghi tổ chức/sàn gán nhầm RETAIL; margin mâu thuẫn │
│ (is_margin_negative=false nhưng avg margin âm); chết 1073 ngày.          │
│ [Tạo task xác minh tài khoản]                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

## States

- ST-CALL-NO-SCRIPT: không có row `cache.wh_approach_script` cho customer_id → empty state + CTA "Quay lại Worklist" / "Xem 360".
- ST-CALL-STOP: `recommended=false` → render STOP banner (R14), ẩn talk_track/talking_points/objection, chỉ còn CTA xác minh.
- ST-CALL-LOW-CONFIDENCE: `confidence=low` → talk-track hiển thị nhạt + nhãn "độ tin thấp, kiểm chứng".
- ST-STALE-CACHE: `refreshed_at` > 24h → yellow badge ở trust_footer.
- ST-LOADING: skeleton khi fetch script.

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
  - id: A-S14-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [script.reload, freshness_bar.update]
```

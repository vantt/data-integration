---
id: C03
type: component
name: "Action Queue Card"
platforms: [desktop]
hosted_by: [S01]
status: active
design_ref: ""
rules: [R2]
regions: []
---

# C03 — Action Queue Card

## Purpose

Card hiển thị một action item từ `wh_action_queue`: action_type (CALL_NOW / WIN_BACK /
REORDER_NUDGE / UPSELL / CROSS_SELL / LOYALTY_REWARD), rationale_vi, value_at_stake_vnd.
Dùng trong Worklist (S01). P01 (Insight Panel) renders action cards inline (không dùng C03).
Card có hai nút hành động:
- **"Gọi Ngay"** — emit event để host navigate vào Call Mode (S14).
- **"Đặt Lịch"** — emit event để host mở M05 tạo task follow-up.
Click vào phần thân card → emit event để host navigate thẳng Customer 360.
Màu card khác nhau theo action_type urgency.

## Props / API

- `action` (object, required): { action_id, action_type, rationale_vi, value_at_stake_vnd }
- `party_id` (string, required): để prefill task modal
- `compact` (bool, optional): compact view cho worklist rows

Note: payload uses bare prop variables (`$party_id`) — these are component-level props passed from the host's loop context, not entity field paths. VR-PAYLOAD-GRAMMAR warns are accepted (see CONVENTION.md §9).

## States

- default: Card rendered với type badge + rationale + value + hai nút [Gọi Ngay] [Đặt Lịch]
- actioned: Mờ nhạt sau khi đã xử lý action này (task đã tạo hoặc đã gọi)

## Emits

```yaml crm-contract
emits:
  - id: A-C03-001
    element: card_call_now_btn
    trigger: click
    event: action_queue.call_mode_requested
    payload: { action_id: "$action.action_id", party_id: "$party_id", action_type: "$action.action_type" }
  - id: A-C03-002
    element: card_schedule_btn
    trigger: click
    event: action_queue.task_requested
    payload: { action_id: "$action.action_id", party_id: "$party_id", action_type: "$action.action_type" }
  - id: A-C03-003
    element: card_body
    trigger: click
    event: action_queue.card_clicked
    payload: { party_id: "$party_id" }

---
id: C03
type: component
name: "Action Queue Card"
platforms: [desktop]
hosts: [P01, S01]
status: active
design_ref: ""
rules: [R2]
regions: []
---

# C03 — Action Queue Card

## Purpose

Card hiển thị một action item từ `wh_action_queue`: action_type (CALL_NOW / WIN_BACK /
REORDER_NUDGE / UPSELL / CROSS_SELL / LOYALTY_REWARD), rationale_vi, value_at_stake_vnd.
Dùng trong Insight Panel (P01) và Worklist (S01). Click → emit event để host mở M05 tạo task
prefilled từ action, hoặc navigate thẳng Customer 360. Màu card khác nhau theo action_type urgency.

## Props / API

- `action` (object, required): { action_id, action_type, rationale_vi, value_at_stake_vnd }
- `party_id` (string, required): để prefill task modal
- `compact` (bool, optional): compact view cho worklist rows

## States

- default: Card rendered với type badge + rationale + value
- actioned: Mờ nhạt sau khi task đã tạo từ card này

## Emits

```yaml crm-contract
emits:
  - id: A-C03-001
    element: card_create_task_btn
    trigger: click
    event: action_queue.task_requested
    payload: { action_id: "$action.action_id", party_id: "$party_id", action_type: "$action.action_type" }
  - id: A-C03-002
    element: card_body
    trigger: click
    event: action_queue.card_clicked
    payload: { party_id: "$party_id" }

---
id: S09
type: screen
name: "Segment Builder"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: [R1, R10]
regions: [topbar, rule_editor, preview_panel, actions_bar]
---

# S09 — Segment Builder

## Purpose

Tạo mới hoặc chỉnh sửa segment. Manager định nghĩa rule JSON (value_group, customer_status,
next_purchase_signal, affinity, tag, v.v.) bằng giao diện rule builder trực quan — không cần
viết JSON tay. Preview real-time hiển thị số party khớp rule (có thể trừ consent_contact=false).

Segment dynamic: mỗi lần job materialize, member list được tính lại theo rule.
Segment static: Manager add/remove party thủ công sau khi tạo.

## Layout

```
┌─ C01 SIDEBAR ─┬──────────────────────────────────────────────────────────────┐
│               │  TOPBAR: [← Segments]  Tên segment: [___________]  [Lưu]    │
│               │  Loại: ● Dynamic  ○ Static                                   │
│               ├──────────────────────────────────────────────────────────────┤
│               │  RULE EDITOR (60%)              │  PREVIEW PANEL (40%)       │
│               │  ┌────────────────────────────┐ │  Kết quả dự kiến:          │
│               │  │ Điều kiện (AND/OR)         │ │  34 khách                  │
│               │  │ ┌──────────────────────┐   │ │  (3 bị loại do consent)    │
│               │  │ │ value_group = GOLD ✕ │   │ │                            │
│               │  │ └──────────────────────┘   │ │  [Preview danh sách]       │
│               │  │ ┌──────────────────────┐   │ │  Nguyễn Văn A   GOLD       │
│               │  │ │ customer_status =    │   │ │  Trần Thị B     GOLD       │
│               │  │ │   at_risk         ✕  │   │ │  ...                       │
│               │  │ └──────────────────────┘   │ │                            │
│               │  │ [+ Thêm điều kiện]         │ │                            │
│               │  └────────────────────────────┘ │                            │
│               │  ACTIONS BAR: [Hủy]  [Lưu & Materialize]                    │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

## States

- ST-BUILDER-PREVIEW-LOADING: Preview query in-flight
- ST-BUILDER-PREVIEW-ZERO: 0 party khớp → warn trước khi lưu
- ST-BUILDER-CONSENT-FILTERED: Hiển thị count bị loại do consent
- ST-SEGMENT-MATERIALIZING: Materialize job đang chạy sau save

## Interactions

```yaml crm-contract
interactions:
  - id: A-S09-001
    element: btn_back
    region: topbar
    trigger: click
    action: navigate
    target: S08
  - id: A-S09-002
    element: btn_add_condition
    region: rule_editor
    trigger: click
    action: mutate
    effects: [rule_editor.add_condition_row]
  - id: A-S09-003
    element: condition_field_select
    region: rule_editor
    trigger: change
    action: mutate
    effects: [rule_editor.update_condition, preview_panel.reload]
  - id: A-S09-004
    element: condition_remove_btn
    region: rule_editor
    trigger: click
    action: mutate
    effects: [rule_editor.remove_condition, preview_panel.reload]
  - id: A-S09-005
    element: btn_preview_list
    region: preview_panel
    trigger: click
    action: mutate
    effects: [preview_panel.expand_member_list]
  - id: A-S09-006
    element: btn_save_materialize
    region: actions_bar
    trigger: click
    guard: "segment.name != '' && rule.conditions.length > 0"
    action: mutate
    effects: [segment.save, segment.materialize_job.trigger, ui.toast.show]
  - id: A-S09-007
    element: btn_cancel
    region: actions_bar
    trigger: click
    action: navigate
    target: S08
  - id: A-S09-008
    element: segment_type_toggle
    region: topbar
    trigger: change
    action: mutate
    effects: [rule_editor.toggle_static_mode]
  - id: A-S09-LSN01
    listens_to: segment.materialized
    action: mutate
    effects: [topbar.member_count.update, ui.toast.show]

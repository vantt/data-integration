---
id: M01
type: modal
name: "Merge Confirm Modal"
platforms: [desktop]
hosted_by: [S04]
status: active
design_ref: ""
rules: [R4, R5, R9]
regions: [header, body, actions]
---

# M01 — Merge Confirm Modal

## Purpose

Xác nhận merge 2 party từ Dedup Review (S04). Hiển thị tóm tắt 2 party, party nào là surviving,
các identity sẽ chuyển qua, cảnh báo hành động không thể hoàn tác (nhưng có undo từ merge_log — R4).
User phải gõ xác nhận hoặc check checkbox trước khi merge.

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
content:
  header:
    - row:
        - { h: "Merge Party B → Party A (surviving)" }
        - { btn: "✕", action: A-M01-001 }
  body:
    - text: "Party A (giữ lại): Nguyễn Văn A +84901234567"
    - text: "Party B (gộp vào): NVA"
    - text: "Sẽ chuyển: 1 identity, 3 activity, 0 task"
    - badge: "⚠ Party B sẽ bị ẩn (is_merged=true)"
    - text: "✓ Snapshot undo sẽ được lưu"
    - checklist: ["Tôi xác nhận muốn gộp 2 khách này"]
  actions:
    - row:
        - { btn: "Hủy", action: A-M01-002 }
        - { btn: "Xác nhận Merge", action: A-M01-003, primary: true }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Merge Party B → Party A (surviving) [x]                                   │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Party A (giữ lại): Nguyễn Văn A +84901234567 · Party B (gộp vào): NVA · S…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy] [Xác nhận Merge]                                                    │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## States

- default: Form hiển thị, checkbox unchecked
- submitting: Merge transaction in-flight, button disabled
- error: ERR-MERGE-CONSTRAINT — hiển thị conflict detail

## Interactions

```yaml crm-contract
interactions:
  - id: A-M01-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M01-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M01-003
    element: btn_confirm_merge
    region: actions
    trigger: click
    guard: "confirm_checkbox.checked"
    action: mutate
    effects: [party.merge.execute, merge_log.snapshot.save, ui.toast.show, modal.close]

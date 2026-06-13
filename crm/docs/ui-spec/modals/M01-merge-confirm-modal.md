---
id: M01
type: modal
name: "Merge Confirm Modal"
platforms: [desktop]
hosts: [S04]
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

```
┌ MODAL — Xác nhận gộp khách ────────────────────────┐
│  Merge Party B → Party A (surviving)          [✕]  │
├────────────────────────────────────────────────────┤
│  Party A (giữ lại):   Nguyễn Văn A  +84901234567  │
│  Party B (gộp vào):   NVA           +84901234567  │
│                                                    │
│  Sẽ chuyển: 1 identity, 3 activity, 0 task       │
│  ⚠ Party B sẽ bị ẩn (is_merged=true)             │
│  ✓ Snapshot undo sẽ được lưu tự động              │
│                                                    │
│  [✓] Tôi xác nhận muốn gộp 2 khách này           │
├────────────────────────────────────────────────────┤
│  [Hủy]                           [Xác nhận Merge] │
└────────────────────────────────────────────────────┘
```

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

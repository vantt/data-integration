---
id: M03
type: modal
name: "Tag Management Modal"
platforms: [desktop]
hosts: [S03, S15]
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# M03 — Tag Management Modal

## Purpose

Gán hoặc bỏ tag cho party hiện tại trong Customer 360 (S03). Hiển thị danh sách tag đang có,
cho phép tìm kiếm + chọn thêm tag từ `crm_tag`, hoặc tạo tag mới nhanh inline.
Tag có category (từ `crm_tag.category`).

## Layout

```
┌ MODAL — Quản lý tag ───────────────────────────────┐
│  Tag cho: Nguyễn Văn A                       [✕]  │
├────────────────────────────────────────────────────┤
│  Đang có: [VIP ✕] [repeat ✕] [da-nhạy-cảm ✕]    │
│                                                    │
│  [🔍 Tìm hoặc tạo tag mới...]                    │
│  ┌──────────────────────────────────────────────┐  │
│  │ [+] skin-care     [+] wholesale              │  │
│  │ [+] gift-buyer    [+] price-sensitive        │  │
│  └──────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────┤
│  [Đóng]                                [Lưu]     │
└────────────────────────────────────────────────────┘
```

## States

- default: Tags hiện tại loaded
- submitting: Save in-flight

## Interactions

```yaml crm-contract
interactions:
  - id: A-M03-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M03-002
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M03-003
    element: tag_remove_btn
    region: body
    trigger: click
    action: mutate
    effects: [party_tag.remove]
  - id: A-M03-004
    element: tag_add_btn
    region: body
    trigger: click
    action: mutate
    effects: [party_tag.add]
  - id: A-M03-005
    element: btn_save
    region: actions
    trigger: click
    action: mutate
    effects: [party_tags.save_batch, modal.close, ui.toast.show]
  - id: A-M03-006
    element: tag_search_input
    region: body
    trigger: input
    action: mutate
    effects: [tag_list.filter]
  - id: A-M03-007
    element: btn_create_new_tag
    region: body
    trigger: click
    action: open_overlay
    target: M14

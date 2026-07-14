---
id: M03
type: modal
name: "Tag Management Modal"
platforms: [desktop]
hosted_by: [S03, S15]
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

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [body]
  - [actions]
content:
  header:
    - row:
        - { h: "Tag cho: Nguyễn Văn A" }
        - { btn: "✕", action: A-M03-001 }
  body:
    - text: "Đang có:"
    - row:
        - { btn: "VIP ✕", action: A-M03-003 }
        - { btn: "repeat ✕", action: A-M03-003 }
        - { btn: "da-nhạy-cảm ✕", action: A-M03-003 }
    - row:
        - { input: "🔍 Tìm hoặc tạo tag mới..." }
        - { btn: "+ Tạo tag mới", action: A-M03-007 }
    - row:
        - { btn: "+ skin-care", action: A-M03-004 }
        - { btn: "+ wholesale", action: A-M03-004 }
        - { btn: "+ gift-buyer", action: A-M03-004 }
        - { btn: "+ price-sensitive", action: A-M03-004 }
  actions:
    - row:
        - { btn: "Đóng", action: A-M03-002 }
        - { btn: "Lưu", action: A-M03-005, primary: true }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Tag cho: Nguyễn Văn A [x]                                                 │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Đang có: · [VIP x] [repeat x] [da-nhạy-cảm x] · [input: (?) Tìm hoặc tạo …│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Đóng] [Lưu]                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

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

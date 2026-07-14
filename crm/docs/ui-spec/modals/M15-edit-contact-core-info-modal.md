---
id: M15
type: modal
name: "Edit Contact & Core Info Modal"
platforms: [desktop]
hosted_by: [S03, S15]
status: active
design_ref: ""
rules: [R5, R13]
regions: [header, tab_bar, body, actions]
---

# M15 — Edit Contact & Core Info Modal

## Purpose

Chỉnh sửa thông tin cốt lõi của party: kênh liên lạc (contacts), địa chỉ, và core fields
(display_name, email, ngày sinh). Tách khỏi M06 (custom fields) vì đây là structured data
được sync từ Sapo hoặc nhập thủ công — không phải schema-less JSON.

3 tabs: Liên lạc / Địa chỉ / Thông tin cơ bản.
Mở từ S03 sidebar với tab được preselect theo button clicked (A-S03-013/014/015).

## Layout

```yaml ui-layout
columns: [1fr]
areas:
  - [header]
  - [tab_bar]
  - [body]
  - [actions]
content:
  header:
    - row:
        - { h: "Nguyễn Văn A" }
        - { btn: "✕", action: A-M15-001 }
  tab_bar:
    - tabs: ["Liên lạc", "Địa chỉ", "Thông tin cơ bản"]
      active: "Liên lạc"
      actions:
        "Liên lạc": A-M15-002
        "Địa chỉ": A-M15-003
        "Thông tin cơ bản": A-M15-004
  body:
    - h: "Kênh liên lạc"
    - list: { item: "📞 Số chính +84901234567 · ● active · is_preferred · ✎", rows: 3 }
    - row:
        - { btn: "✗ Vô hiệu kênh", action: A-M15-006 }
        - { btn: "＋ Thêm kênh liên lạc", action: A-M15-005 }
  actions:
    - row:
        - { btn: "Hủy", action: A-M15-008 }
        - { btn: "Lưu", action: A-M15-007, primary: true }
```

<!-- ui-layout:ascii:start -->
```
┌────────────────────────────────────────────────────────────────────────────┐
│HEADER                                                                      │
│· Nguyễn Văn A [x]                                                          │
├────────────────────────────────────────────────────────────────────────────┤
│TAB_BAR                                                                     │
│· |*Liên lạc*|| Địa chỉ || Thông tin cơ bản |                               │
├────────────────────────────────────────────────────────────────────────────┤
│BODY                                                                        │
│· Kênh liên lạc · list ×3 {> Số chính +84901234567 · o active · is_preferre…│
├────────────────────────────────────────────────────────────────────────────┤
│ACTIONS                                                                     │
│· [Hủy] [Lưu]                                                               │
└────────────────────────────────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

## Layout — Tab: Liên lạc

## Layout — Tab: Địa chỉ

## Layout — Tab: Thông tin cơ bản

- `Giới tính` maps to `party.gender`; options: `male`, `female`, `other`, `unknown`
- `Đồng ý LH` maps to `party.consent_contact` (enum: `na` default / `allowed` / `denied`); `denied` = R1 rule enforced; `na` = chưa xác nhận, không bị R1 gating nhưng không được chủ động outreach

## Business Rules

- R5: Phone values phải normalized E.164 trước khi save (+84xxx)
- R13: Khi save địa chỉ thủ công → `address_source='manual'`; sync Sapo không ghi đè
- `is_preferred`: chỉ 1 kênh được `is_preferred=true` mỗi lúc; set kênh mới làm preferred → unset kênh cũ
- Xóa kênh liên lạc (✗): soft-deactivate (`contact_status='invalid'`), không xóa cứng để giữ identity history

## States

- default: Data prefilled từ crm_party + crm_party_identity
- saving: In-flight
- error: Validation inline (E.164 format, required fields)

## Interactions

```yaml crm-contract
interactions:
  - id: A-M15-001
    element: btn_close
    region: header
    trigger: click
    action: close_overlay
    target: return_to_invoker
  - id: A-M15-002
    element: tab_contacts
    region: tab_bar
    trigger: click
    action: mutate
    effects: [body.show_contacts_tab]
  - id: A-M15-003
    element: tab_address
    region: tab_bar
    trigger: click
    action: mutate
    effects: [body.show_address_tab]
  - id: A-M15-004
    element: tab_core
    region: tab_bar
    trigger: click
    action: mutate
    effects: [body.show_core_tab]
  - id: A-M15-005
    element: btn_add_channel
    region: body
    trigger: click
    action: mutate
    effects: [add_channel_form.show]
  - id: A-M15-006
    element: btn_deactivate_channel
    region: body
    trigger: click
    action: mutate
    effects: [identity.contact_status.set_invalid, contacts_list.reload]
  - id: A-M15-007
    element: btn_save
    region: actions
    trigger: click
    guard: "active_tab == 'core' ? form.display_name != '' : true"
    action: mutate
    effects: [party_or_identity.save, modal.close, ui.toast.show, sidebar.reload]
  - id: A-M15-008
    element: btn_cancel
    region: actions
    trigger: click
    action: close_overlay
    target: return_to_invoker
```

---
id: M15
type: modal
name: "Edit Contact & Core Info Modal"
platforms: [desktop]
hosts: [S03]
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
Mở từ S03 left col với tab được preselect theo button clicked (A-S03-013/014/015).

## Layout — Tab: Liên lạc

```
┌ MODAL — Chỉnh sửa thông tin ──────────────────────┐
│  Nguyễn Văn A                                [✕]  │
│  [Liên lạc]  [Địa chỉ]  [Thông tin cơ bản]       │
├───────────────────────────────────────────────────┤
│  Danh sách kênh liên lạc:                         │
│  ┌─────────────────────────────────────────────┐  │
│  │ 📞 Số chính   +84901234567      [✎] [✗]    │  │
│  │    Trạng thái: ● active                      │  │
│  ├─────────────────────────────────────────────┤  │
│  │ 💬 Zalo       zalo_handle_123   [✎] [✗]    │  │
│  │    Trạng thái: ● active                      │  │
│  ├─────────────────────────────────────────────┤  │
│  │ 📘 Facebook   fb_handle         [✎] [✗]    │  │
│  │    Trạng thái: ○ invalid                     │  │
│  └─────────────────────────────────────────────┘  │
│  [+ Thêm kênh liên lạc]                           │
│                                                   │
│  Add form (khi click +):                          │
│  Loại:  [Zalo ▼]  -- phone_secondary / zalo /    │
│          facebook / email                         │
│  Giá trị: [___________]                           │
│  Nhãn:    [VD: Số công ty] (optional)            │
│  Ưu tiên: [○ Không ● Có]                         │
├───────────────────────────────────────────────────┤
│  [Hủy]                                  [Lưu]   │
└───────────────────────────────────────────────────┘
```

## Layout — Tab: Địa chỉ

```
├───────────────────────────────────────────────────┤
│  Địa chỉ đầy đủ  [123 Nguyễn Huệ____________]   │
│  Phường/Xã       [Bến Nghé________________]      │
│  Quận/Huyện      [Quận 1_________________]       │
│  Tỉnh/Thành phố  [TP. Hồ Chí Minh________]      │
│                                                   │
│  Ghi chú địa chỉ [Địa chỉ sàn bị mask,___]      │
│                  [đã xác nhận qua điện thoại]    │
│                                                   │
│  Nguồn: sapo_sync (tự động) / manual (đã xác nhận)│
│  → Lưu sẽ set address_source = 'manual'          │
├───────────────────────────────────────────────────┤
│  [Hủy]                                  [Lưu]   │
└───────────────────────────────────────────────────┘
```

## Layout — Tab: Thông tin cơ bản

```
├───────────────────────────────────────────────────┤
│  Tên hiển thị *  [Nguyễn Văn A___________]       │
│  Email           [email@domain.com________]      │
│  Ngày sinh       [dd/mm/yyyy]                    │
├───────────────────────────────────────────────────┤
│  [Hủy]                                  [Lưu]   │
└───────────────────────────────────────────────────┘
```

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
    effects: [party_or_identity.save, modal.close, ui.toast.show, left_col.reload]
```

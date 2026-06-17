---
id: S03
type: screen
name: "Customer 360 Detail"
platforms: [desktop]
hosts: [P01, P02, P03, P04, P05, P06]
status: active
design_ref: ""
rules: [R2, R3, R6, R7]
regions: [topbar, left_col, right_col, tab_bar]
---

# S03 — Customer 360 Detail

## Purpose

Hồ sơ đầy đủ 360° của một party. Sales Rep mở màn hình này trước khi gọi điện để nắm:
cảnh báo về khách, kênh liên lạc ưu tiên, insight warehouse (RFM, affinity, action_queue),
insight do rep đúc kết, lịch sử đơn hàng, tags, ghi chú, task đang mở, và activity timeline.

Layout 2 cột: cột trái = thông tin tĩnh (warnings, contacts, address, core info, tags, custom fields);
cột phải = tab bar chứa các panel động (Insight P01, Đơn hàng P02, Timeline P03, Tasks P04, Ghi chú P05, Hội thoại P06).

Target: point-lookup ≤ 200ms (view `crm_party_360`). `refreshed_at` hiển thị tại P01.

## Layout

```
┌─ C01 SIDEBAR ─┬──────────────────────────────────────────────────────────────┐
│               │  TOPBAR: [← Quay lại]  Nguyễn Văn A  GOLD · active          │
│               │  [Gán NV ▼]  [+ Tag]  [Ghi log]  [Tạo task]                │
│               ├──────────────────────────────────────────────────────────────┤
│               │  LEFT COL (30%)           │  RIGHT COL (70%)                 │
│               │  ┌─────────────────────┐  │  [Insight|Đơn|Timeline|Tasks|   │
│               │  │ ⚠ Cảnh báo (nếu có)│  │   Ghi chú|Chat]                 │
│               │  ├─────────────────────┤  │                                 │
│               │  │ LIÊN LẠC        [+] │  │  (P01 / P02 / P03 / P04 /      │
│               │  │ 📞 0901234567 Chính │  │   P05 / P06 shown here)         │
│               │  │ 💬 zalo_id    Zalo  │  │                                 │
│               │  ├─────────────────────┤  │                                 │
│               │  │ ĐỊA CHỈ        [✎] │  │                                 │
│               │  │ Q.1, TP.HCM (sync) │  │                                 │
│               │  ├─────────────────────┤  │                                 │
│               │  │ THÔNG TIN      [✎] │  │                                 │
│               │  │ Tên, email, ...     │  │                                 │
│               │  ├─────────────────────┤  │                                 │
│               │  │ TAGS           [✎] │  │                                 │
│               │  │ [VIP] [repeat]      │  │                                 │
│               │  ├─────────────────────┤  │                                 │
│               │  │ CUSTOM FIELDS  [✎] │  │                                 │
│               │  │ (grouped by section)│  │                                 │
│               │  ├─────────────────────┤  │                                 │
│               │  │ Consent: ✓          │  │                                 │
│               │  └─────────────────────┘  │                                 │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

## Left Column Sections

### Cảnh báo (warning notes)
- Chỉ hiển thị khi có `crm_note.note_type='warning'` và `is_active=true`
- Luôn nằm đầu left col, nền đỏ nhạt
- Click → expand note body
- Chỉ manager mới xóa được warning note

### Liên lạc
- Render tất cả `crm_party_identity` của party, group theo identity_type
- Mỗi row: icon type, value, display_label, status badge (invalid/dnc nếu không active)
- `is_preferred=true` → hiển thị trước, bold
- Quick-action: click phone → copy số; click zalo/facebook → log contact attempt (M08 mode=contact_attempt)
- [+] → M15 (Add/Edit Contact)
- `contact_pref` notes hiển thị inline bên dưới contact list

### Địa chỉ
- Hiển thị `address_line`, ward, district, province
- Badge nguồn: `sapo_sync` (xám) hoặc `manual` (xanh lá, "đã xác nhận")
- `address_note` hiển thị italic nếu có
- [✎] → M15 (Edit Address tab)

### Thông tin cơ bản
- display_name, email (từ crm_party_identity type=email), ngày sinh (nếu có)
- [✎] → M15 (Edit Core Info tab)

### Tags
- [✎] → M03

### Custom Fields
- Grouped by `crm_custom_field_def.section`, entity_type='customer'
- Sort theo sort_order trong mỗi section
- [✎] → M06

## States

- ST-360-LOADING: Point-lookup in-flight
- ST-360-NO-PROFILE: Profile chưa tạo → CTA "Tạo hồ sơ"
- ST-360-NO-INSIGHT: Insight chưa có trong cache → placeholder + refreshed_at
- ST-360-MERGED: Party is_merged=true → warning banner + link to surviving party
- ST-360-WARNING: Có warning note → red banner đầu left col

## Interactions

```yaml crm-contract
interactions:
  - id: A-S03-001
    element: btn_back
    region: topbar
    trigger: click
    action: navigate
    target: S02
  - id: A-S03-002
    element: btn_assign_owner
    region: topbar
    trigger: click
    action: open_overlay
    target: M04
    payload: { party_id: "$party.id" }
  - id: A-S03-003
    element: btn_add_tag
    region: topbar
    trigger: click
    action: open_overlay
    target: M03
    payload: { party_id: "$party.id" }
  - id: A-S03-004
    element: tab_insight
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P01]
  - id: A-S03-005
    element: tab_orders
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P02]
  - id: A-S03-006
    element: tab_timeline
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P03]
  - id: A-S03-007
    element: tab_tasks
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P04]
  - id: A-S03-008
    element: tab_notes
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P05]
  - id: A-S03-009
    element: tab_chat
    region: tab_bar
    trigger: click
    action: mutate
    effects: [right_col.show_panel_P06]
  - id: A-S03-010
    element: btn_edit_custom_fields
    region: left_col
    trigger: click
    action: open_overlay
    target: M06
    payload: { party_id: "$party.id" }
  - id: A-S03-011
    element: btn_log_activity
    region: topbar
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id" }
  - id: A-S03-012
    element: btn_create_task
    region: topbar
    trigger: click
    action: open_overlay
    target: M05
    payload: { party_id: "$party.id" }
  - id: A-S03-013
    element: btn_edit_contacts
    region: left_col
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "contacts" }
  - id: A-S03-014
    element: btn_edit_address
    region: left_col
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "address" }
  - id: A-S03-015
    element: btn_edit_core_info
    region: left_col
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "core" }
  - id: A-S03-016
    element: contact_channel_quick_action
    region: left_col
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id", mode: "contact_attempt", channel: "$channel.type" }
  - id: A-S03-LSN01
    listens_to: cache.refreshed
    action: mutate
    effects: [P01.insight.reload]
  - id: A-S03-LSN02
    listens_to: party.merged
    action: mutate
    effects: [topbar.merged_banner.show]
  - id: A-S03-LSN03
    listens_to: tag_chips.add_requested
    action: open_overlay
    target: M03
    payload: { party_id: "$event.party_id" }
  - id: A-S03-LSN04
    listens_to: tag_chips.remove_requested
    action: mutate
    effects: [party_tag.remove, tags_display.reload]
  - id: A-S03-LSN05
    listens_to: tag_chips.chip_clicked
    action: mutate
    effects: [ui.tag_filter.set]
```

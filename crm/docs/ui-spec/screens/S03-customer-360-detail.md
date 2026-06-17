---
id: S03
type: screen
name: "Customer 360 Detail"
platforms: [desktop]
hosts: [P01, P02, P03, P04, P05, P06]
status: active
design_ref: ""
rules: [R2, R3, R6, R7]
regions: [topbar, sidebar, main_col, tab_bar]
---

# S03 — Customer 360 Detail

## Purpose

Hồ sơ đầy đủ 360° của một party. Sales Rep mở màn hình này trước khi gọi điện để nắm:
cảnh báo về khách, kênh liên lạc ưu tiên, insight warehouse (RFM, affinity, action_queue),
insight do rep đúc kết, lịch sử đơn hàng, tags, ghi chú, task đang mở, và activity timeline.

Layout 2 cột: cột trái (70%) = main + tab bar chứa các panel động (Insight P01, Đơn hàng P02,
Timeline P03, Tasks P04, Ghi chú P05, Hội thoại P06); cột phải (30%) = sidebar tĩnh với các
block: Cảnh báo, Thông Tin Cơ Bản, Head Line, Liên Lạc, Dates, Tags.

Target: point-lookup ≤ 200ms (view `crm_party_360`). `refreshed_at` hiển thị tại P01.

## Layout

```
┌──────────────────────────────────────────────┬─── SIDEBAR (30%) ─────────────┐
│ TOPBAR: [← Quay lại]  Nguyễn Văn A           │ ⚠ Cảnh báo (conditional)     │
│ [Gán NV ▼]  [+ Tag]  [Ghi log]  [Tạo task]  ├───────────────────────────────┤
├──────────────────────────────────────────────┤ THÔNG TIN CƠ BẢN          [✎] │
│  MAIN (70%) — tabbar + lazy panels           │ tên, badges, phone,            │
│  [Insight|Đơn|Timeline|Tasks|Ghi chú|Chat]   │ sapo-id, sapo-code,            │
│                                              │ sex, owner, consent            │
│  (P01 / P02 / P03 / P04 / P05 / P06)         ├───────────────────────────────┤
│                                              │ HEAD LINE                      │
│                                              │ LTV  ·  Đơn  ·  AOV  ·  Recency│
│                                              ├───────────────────────────────┤
│                                              │ LIÊN LẠC                  [+] │
│                                              │ 📞 0901234567 (chính)          │
│                                              │ 💬 zalo_id                     │
│                                              │ ✉ email                        │
│                                              │ 📍 Q.1, TP.HCM · region        │
│                                              ├───────────────────────────────┤
│                                              │ DATES                          │
│                                              │ First Order · Last Order       │
│                                              │ Tenure                         │
│                                              ├───────────────────────────────┤
│                                              │ TAGS                      [✎] │
│                                              │ [VIP] [repeat]                 │
└──────────────────────────────────────────────┴───────────────────────────────┘
```

## Sidebar Sections

### Cảnh báo (warning notes)
- Chỉ hiển thị khi có `crm_note.note_type='warning'` và `is_active=true`
- Luôn nằm đầu sidebar, nền đỏ nhạt
- Chỉ manager mới xóa được warning note

### Thông Tin Cơ Bản
- **tên**: `party.display_name`
- **badges**: value_group (warehouse), status
- **phone**: số điện thoại chính (crm_party_identity type=phone, is_preferred=true)
- **sapo-id**: `wh_customer_base.customer_id` (Sapo customer ID)
- **sapo-code**: `wh_customer_base.customer_code`
- **sex**: `party.gender`
- **owner**: `party.owner_user_id`
- **consent**: `party.consent_contact` → icon ✓ "Cho phép liên lạc" hoặc ✕ "Không liên lạc (R1)"
- [✎] → M15 (tab: core)

### Head Line
KPI grid (4 ô), source: `wh_customer_insight` (warehouse cache):
- **Lifetime value** (`lifetime_contribution_margin`) — hero, định dạng VND
- **Đơn** (`order_count`) — số lượng đơn hàng
- **AOV** (`avg_order_spend`) — định dạng VND
- **Recency** (`avg_days_between_orders` hoặc days since last order) — đơn vị ngày
- Placeholder "—" khi insight chưa có (ST-360-NO-INSIGHT)

### Liên Lạc
Gộp contact channels + địa chỉ + region thành một block:
- **Channels**: tất cả `crm_party_identity` (phone, phone_secondary, zalo, facebook, email)
  - Mỗi row: icon, value, display_label, status badge; is_preferred → bold, hiển thị trước
  - Quick-action: phone → copy; zalo/facebook → log contact attempt (M08)
  - `contact_pref` notes hiển thị inline bên dưới channel list
- **Địa chỉ**: `address_line`, ward, district, province; badge nguồn sapo_sync/manual; `address_note` italic
- **Region**: `wh_customer_base.geo_region` (nếu có)
- [+] → M15 (tab: contacts); [✎] địa chỉ → M15 (tab: address)

### Dates
Source: `wh_customer_insight` / `wh_customer_base` (warehouse cache):
- **First Order**: ngày đặt hàng đầu tiên (`first_order_date`)
- **Last Order**: ngày đặt hàng gần nhất (`last_order_date`)
- **Tenure**: số ngày kể từ first order (lifespan_days), format "N d (X y)"
- Placeholder "—" khi không có dữ liệu

### Tags
- [✎] → M03

## States

- ST-360-LOADING: Point-lookup in-flight
- ST-360-NO-PROFILE: Profile chưa tạo → CTA "Tạo hồ sơ"
- ST-360-NO-INSIGHT: Insight chưa có trong cache → placeholder + refreshed_at
- ST-360-MERGED: Party is_merged=true → warning banner + link to surviving party
- ST-360-WARNING: Có warning note → red banner đầu sidebar

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
    effects: [main_col.show_panel_P01]
  - id: A-S03-005
    element: tab_orders
    region: tab_bar
    trigger: click
    action: mutate
    effects: [main_col.show_panel_P02]
  - id: A-S03-006
    element: tab_timeline
    region: tab_bar
    trigger: click
    action: mutate
    effects: [main_col.show_panel_P03]
  - id: A-S03-007
    element: tab_tasks
    region: tab_bar
    trigger: click
    action: mutate
    effects: [main_col.show_panel_P04]
  - id: A-S03-008
    element: tab_notes
    region: tab_bar
    trigger: click
    action: mutate
    effects: [main_col.show_panel_P05]
  - id: A-S03-009
    element: tab_chat
    region: tab_bar
    trigger: click
    action: mutate
    effects: [main_col.show_panel_P06]
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
    region: sidebar
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "contacts" }
  - id: A-S03-014
    element: btn_edit_address
    region: sidebar
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "address" }
  - id: A-S03-015
    element: btn_edit_core_info
    region: sidebar
    trigger: click
    action: open_overlay
    target: M15
    payload: { party_id: "$party.id", tab: "core" }
  - id: A-S03-016
    element: contact_channel_quick_action
    region: sidebar
    trigger: click
    action: open_overlay
    target: M08
    payload: { party_id: "$party.id", mode: "contact_attempt", channel: "$channel.type" }
  - id: A-S03-017
    element: btn_edit_tags
    region: sidebar
    trigger: click
    action: open_overlay
    target: M03
    payload: { party_id: "$party.id" }
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

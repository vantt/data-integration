---
id: S13
type: screen
name: "Settings"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: []
regions: [topbar, sidebar, settings_nav, settings_content]
---

# S13 — Settings

## Purpose

Admin/Manager quản lý cấu hình hệ thống: custom field definitions, tag categories, user list và
role assignment. Structured as a tabbed settings page — mỗi tab là một sub-section.

Thay đổi custom field def ảnh hưởng toàn bộ `crm_customer_profile.custom` JSON validation.
Không cần migration khi thêm field mới (schema-less JSON1).

## Layout

### Tab: Custom Fields (default)

```
┌─ C01 SIDEBAR ─┬──────────────────────────────────────────────────────────────┐
│               │  TOPBAR: Cài đặt                                             │
│               ├────────────────┬─────────────────────────────────────────────┤
│               │  SETTINGS NAV  │  SETTINGS CONTENT                           │
│               │  > Custom Fields│  Custom Fields                   [+ Thêm]  │
│               │    Tags         │  ┌────────────────────────────────────────┐ │
│               │    Người dùng   │  │ Tên field    Loại     Bắt buộc  [Edit] │ │
│               │                 │  │ Da nhạy cảm  bool     không    [Edit]  │ │
│               │                 │  │ Nguồn KH     select   không    [Edit]  │ │
│               │                 │  └────────────────────────────────────────┘ │
└───────────────┴────────────────┴─────────────────────────────────────────────┘
```

### Tab: Tags

```
┌─ C01 SIDEBAR ─┬──────────────────────────────────────────────────────────────┐
│               │  TOPBAR: Cài đặt                                             │
│               ├────────────────┬─────────────────────────────────────────────┤
│               │  SETTINGS NAV  │  SETTINGS CONTENT                           │
│               │    Custom Fields│  Tags                           [+ Tạo tag] │
│               │  > Tags         │  ┌──────────────────────────────────────────┐│
│               │    Người dùng   │  │Nhãn     Tên(slug)  Category  Màu  [•][✕]││
│               │                 │  │[VIP]    vip-repeat vip_tier   ●   [✏][✕]││
│               │                 │  │[Deal]   deal       behavioral —   [✏][✕]││
│               │                 │  └──────────────────────────────────────────┘│
└───────────────┴────────────────┴─────────────────────────────────────────────┘
```

**Columns:**
- **Nhãn** — chip colored via `.chip--{color}` DS modifier (moss/coral/amber/default)
- **Tên (slug)** — mono muted; the raw `name` field
- **Category** — enum label or `—` if unset
- **Màu** — 10px dot `tag-dot` colored `background: var(--{color}-500)`; `—` if unset or default
- **Actions** — `[✏ Edit]` + `[✕ Delete]` icon buttons, no-wrap, right-aligned

## States

- ST-SETTINGS-SAVED: Toast "Đã lưu" sau mỗi thay đổi
- ST-LOADING: Settings content loading

## Interactions

```yaml crm-contract
interactions:
  - id: A-S13-001
    element: nav_custom_fields
    region: settings_nav
    trigger: click
    action: mutate
    effects: [settings_content.show_custom_fields]
  - id: A-S13-002
    element: nav_tags
    region: settings_nav
    trigger: click
    action: mutate
    effects: [settings_content.show_tags]
  - id: A-S13-003
    element: nav_users
    region: settings_nav
    trigger: click
    action: mutate
    effects: [settings_content.show_users]
  - id: A-S13-004
    element: btn_add_custom_field
    region: settings_content
    trigger: click
    action: open_overlay
    target: M13
  - id: A-S13-005
    element: btn_edit_custom_field
    region: settings_content
    trigger: click
    action: open_overlay
    target: M13
    payload: { field_def_id: "$field.id" }
  - id: A-S13-006
    element: btn_delete_custom_field
    region: settings_content
    trigger: click
    action: open_overlay
    target: O01
    payload: { confirm_type: "delete_field", field_def_id: "$field.id" }
  - id: A-S13-007
    element: btn_add_tag
    region: settings_content
    trigger: click
    action: open_overlay
    target: M14
  - id: A-S13-008
    element: btn_edit_tag
    region: settings_content
    trigger: click
    action: open_overlay
    target: M14
    payload: { tag_id: "$tag.tag_id" }
  - id: A-S13-009
    element: btn_delete_tag
    region: settings_content
    trigger: click
    action: mutate
    effects: [tag.delete, tag_row.remove]
    notes: "HTMX confirm dialog; removes row via outerHTML swap"
  - id: A-S13-010
    element: btn_edit_user_role
    region: settings_content
    trigger: click
    action: mutate
    effects: [user.role.update, ui.toast.show]

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

```yaml ui-layout
columns: [1fr, 1fr, 4fr]
row_heights: [auto, "minmax(280px,auto)"]
areas:
  - [sidebar, topbar, topbar]
  - [sidebar, settings_nav, settings_content]
content:
  sidebar:
    - slot: "C01 Sidebar Nav (global)"
  topbar:
    - h: "Cài đặt"
  settings_nav:
    - tabs: ["Custom Fields", "Tags", "Người dùng"]
      actions: { "Custom Fields": A-S13-001, "Tags": A-S13-002, "Người dùng": A-S13-003 }
  settings_content:
    - row:
        - { h: "Custom Fields" }
        - { btn: "+ Thêm", action: A-S13-004, primary: true }
    - table: { cols: ["Nhãn", "Kiểu", "Bắt buộc", "Actions"], rows: 3 }
```

<!-- ui-layout:ascii:start -->
```
┌────────────┬───────────────────────────────────────────────────────────────┐
│SIDEBAR     │TOPBAR                                                         │
│· <<C01 Sid…│· Cài đặt                                                      │
│            ├────────────┬──────────────────────────────────────────────────┤
│            │SETTINGS_NAV│SETTINGS_CONTENT                                  │
│            │· | Custom …│· Custom Fields [+ Thêm] · tbl(Nhãn | Kiểu | Bắt …│
└────────────┴────────────┴──────────────────────────────────────────────────┘
```
<!-- ui-layout:ascii:end -->

### Tab: Custom Fields (default)

### Tab: Tags

**Columns:**
- **Nhãn** — chip colored via `.chip--{color}` DS modifier (moss/coral/amber/default)
- **Tên (slug)** — mono muted; the raw `name` field
- **Category** — enum label or `—` if unset
- **Màu** — 10px dot `tag-dot` colored `background: var(--{color}-500)`; `—` if unset or default
- **Actions** — `[✏ Edit]` + `[✕ Delete]` icon buttons, no-wrap, right-aligned

## States

- ST-SETTINGS-SAVED: Toast "Đã lưu" sau mỗi thay đổi
- ST-LOADING: Settings content loading

Delete tag (btn_delete_tag) uses an HTMX confirm dialog; on confirm removes the row via `outerHTML` swap without a full page reload.

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
  - id: A-S13-010
    element: btn_edit_user_role
    region: settings_content
    trigger: click
    action: mutate
    effects: [user.role.update, ui.toast.show]

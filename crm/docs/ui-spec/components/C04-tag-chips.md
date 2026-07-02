---
id: C04
type: component
name: "Tag Chips"
platforms: [desktop]
hosted_by: [S02, S03, S04]
status: active
design_ref: ""
rules: []
regions: []
---

# C04 — Tag Chips

## Purpose

Hiển thị danh sách tags của party dưới dạng chips inline. Mỗi chip có màu theo category.
Dùng trong Customer List rows (S02), Customer 360 left col (S03), Dedup detail pane (S04).
Click vào chip "+" → emit event để host mở M03. Click vào chip existing → emit để host filter
hoặc mở quản lý tag.

## Props / API

- `tags` (array, required): [{ id, name, display_label, category, color }]
- `editable` (bool, optional, default false): hiện nút "+" thêm tag và nút "✕" xóa
- `max_visible` (number, optional, default 5): overflow thành "+N more"

## States

- default: Chips rendered inline
- overflow: Hiện "+N more" khi > max_visible

## Emits

```yaml crm-contract
emits:
  - id: A-C04-001
    element: btn_add_tag
    trigger: click
    event: tag_chips.add_requested
    payload: { party_id: "$party.id" }
  - id: A-C04-002
    element: tag_chip_remove
    trigger: click
    event: tag_chips.remove_requested
    payload: { tag_id: "$tag.id", party_id: "$party.id" }
  - id: A-C04-003
    element: tag_chip
    trigger: click
    event: tag_chips.chip_clicked
    payload: { tag_id: "$tag.id", tag_name: "$tag.name" }

---
id: C05
type: component
name: "Filter Bar"
platforms: [desktop]
hosted_by: [S01, S02, S05, S07, S10, S11]
status: active
design_ref: ""
rules: []
regions: []
---

# C05 — Filter Bar

## Purpose

Thanh filter tái sử dụng cho các list screens. Render dynamically từ `filter_config` prop —
danh sách filter fields, types (select/date-range/search/multi-select), và options. Emit event
khi bất kỳ filter thay đổi để host screen reload list. Active filter count badge.

## Props / API

- `filter_config` (array, required): [{ field, label, type, options? }]
- `initial_values` (object, optional): prefilled filter values
- `show_clear_all` (bool, optional): hiện nút "Xóa filter"

Note: payload uses bare prop variable (`$current_filter_values`) — this is a component-level prop representing the current filter state blob, not an entity field path. VR-PAYLOAD-GRAMMAR warn is accepted (see CONVENTION.md §9).

## States

- default: Filters rendered, no active filters
- active: ≥1 filter set, badge count shows
- collapsed: (mobile) dropdown view

## Emits

### S01-specific filters (Worklist)

- `has_script` (checkbox, value=1): keeps only action items whose `customer_id ∈ script_cids`
  (set computed via `os.scandir(approach_scripts/)` each load — no restart for new files).
  Tasks are not filtered (v1). Chip label: "📋 Có kịch bản".

```yaml crm-contract
emits:
  - id: A-C05-001
    element: filter_field
    trigger: change
    event: filter_bar.changed
    payload: { filters: "$current_filter_values" }
  - id: A-C05-002
    element: btn_clear_all
    trigger: click
    event: filter_bar.cleared
    payload: {}

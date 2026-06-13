---
id: {ID}
type: component
name: "{NAME}"
platforms: [desktop, mobile]
hosts: []        # surfaces that use this component
status: active
design_ref: ""
rules: []
regions: []
---

# {ID} — {NAME}

## Purpose
<!-- What this reusable component does and when to use it.
     Example: "Generic data table with sortable columns, pagination, and row selection." -->

## Props / API
<!-- Document the component's input interface.
     - prop_name (type, required/optional): description
     Example:
     - items (array, required): rows to display
     - page_size (number, optional, default 20): rows per page
     - on_row_click (callback, optional): fired when a row is selected
-->

## States
<!-- - default: data loaded
     - loading: skeleton shown
     - empty: no rows, empty state message displayed
-->

## Emits
<!-- Components use `emits:` (not interactions) — they broadcast events upward for hosts to handle. -->

```yaml {project}-contract
emits:
  # Each emit entry declares an event this component can fire.
  # id is REQUIRED in emits for cross-reference by host surfaces.
  #
  # Example — row selection event:
  # - id: A-{ID}-RowSelect
  #   element: table_row
  #   region: body
  #   trigger: click
  #   guard: "row.selectable"
  #   event: row_selected
  #   payload:
  #     row_id: string
  #
  # Example — page change:
  # - id: A-{ID}-PageChange
  #   element: pagination
  #   trigger: click
  #   event: page_changed
  #   payload:
  #     page: number
```

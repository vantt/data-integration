---
id: {ID}
type: panel
name: "{NAME}"
platforms: [desktop]
hosts: []        # screens that embed this panel
status: active
design_ref: ""
rules: []
regions: [toolbar, content]
---

# {ID} — {NAME}

## Purpose
<!-- What this panel displays and why it exists as a reusable panel.
     Example: "Sidebar panel for filtering a data grid by date, status, and assignee." -->

## Layout

```
<!-- ASCII wireframe of the panel. -->
┌ PANEL ──────────────────┐
│ TOOLBAR: [actions]      │
├─────────────────────────┤
│                         │
│   CONTENT               │
│   (list / form / tree)  │
│                         │
└─────────────────────────┘
```

## States
<!-- - default: loaded with data
     - loading: fetching content
     - collapsed: minimised view (if applicable)
-->

## Interactions

```yaml {project}-contract
interactions:
  # Example — filter change triggers data reload:
  # - element: filter_status
  #   region: toolbar
  #   trigger: change
  #   action: mutate
  #   effects: ["reload_list"]
  #
  # Example — row click opens detail:
  # - element: list_row
  #   region: content
  #   trigger: click
  #   action: open_overlay
  #   target: P02
```

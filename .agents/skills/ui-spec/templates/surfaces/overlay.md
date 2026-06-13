---
id: {ID}
type: overlay
name: "{NAME}"
platforms: [desktop]
hosts: []        # surfaces that trigger this overlay
status: active
design_ref: ""
rules: []
regions: [content, actions]
---

# {ID} — {NAME}

## Purpose
<!-- What this overlay provides. Overlays are lighter than modals — used for contextual menus,
     tooltips, popovers, drawers, and inline panels that don't block the full page.
     Example: "Contextual action menu for a kanban card — quick-edit, move, archive." -->

## Layout

```
<!-- ASCII wireframe of the overlay. -->
     ┌ OVERLAY ─────────────────┐
     │  CONTENT                 │
     │  (contextual info/form)  │
     ├──────────────────────────┤
     │  ACTIONS: [Btn1] [Btn2]  │
     └──────────────────────────┘
```

## Trigger
<!-- How/where this overlay is opened. Example: "Right-click on a table row." -->

## States
<!-- - default: opened with context data
     - loading: async content fetch
-->

## Interactions

```yaml {project}-contract
interactions:
  # Dismiss on outside click (if applicable)
  # - element: overlay_backdrop
  #   trigger: click
  #   action: close_overlay
  #
  # Primary action
  # - element: btn_primary
  #   region: actions
  #   trigger: click
  #   guard: "optional_condition"
  #   action: mutate
  #   effects: ["apply_change"]
  #
  # Secondary / cancel
  # - element: btn_cancel
  #   region: actions
  #   trigger: click
  #   action: close_overlay
```

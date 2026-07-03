---
id: {ID}
type: overlay
name: "{NAME}"
platforms: [desktop]
hosted_by: []    # surfaces that trigger this overlay
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

<!-- ui-layout: machine-readable spatial model. Edit this fence, not the generated ASCII below.
     Schema: columns (fr widths), areas (grid-template-areas rows), floating (overlay toggles),
     variants (prepend/append rows), samples (sample content per region), children (sub-layouts).
     After editing, run: node tools/build.mjs (regenerates ASCII + wireframe).
-->

```yaml ui-layout
columns: ["1fr"]
areas:
  - [header]
  - [body]
  - [actions]
samples:
  header: ""
  body: ""
  actions: ""
```

<!-- ui-layout:ascii:start -->
<!-- ui-layout:ascii:end -->

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

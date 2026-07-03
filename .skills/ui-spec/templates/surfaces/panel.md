---
id: {ID}
type: panel
name: "{NAME}"
platforms: [desktop]
hosted_by: []    # screens that embed this panel
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

<!-- ui-layout: machine-readable spatial model. Edit this fence, not the generated ASCII below.
     Schema: columns (fr widths), areas (grid-template-areas rows), floating (overlay toggles),
     variants (prepend/append rows), samples (sample content per region), children (sub-layouts).
     After editing, run: node tools/build.mjs (regenerates ASCII + wireframe).
-->

```yaml ui-layout
columns: ["1fr"]
areas:
  - [header]
  - [content]
samples:
  header: ""
  content: ""
```

<!-- ui-layout:ascii:start -->
<!-- ui-layout:ascii:end -->

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

---
id: {ID}
type: screen
name: "{NAME}"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: []
regions: [header, body, footer]
---

# {ID} — {NAME}

## Purpose
<!-- Why this screen exists and what user goal it serves.
     Example: "Allows users to browse and filter the product catalog before adding items to cart." -->

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
  - [footer]
samples:
  header: ""
  body: ""
  footer: ""
```

<!-- ui-layout:ascii:start -->
<!-- ui-layout:ascii:end -->

## States
<!-- Key states this screen can be in. Link to shared states file if applicable.
     - default: normal loaded state
     - loading: data fetch in progress
     - empty: no data to display
     - error: failed to load
-->

## Interactions

```yaml {project}-contract
interactions:
  # Each interaction entry describes one user action on this screen.
  # id is optional — omit to auto-generate, or set explicitly for cross-reference.
  #
  # Example — navigate on button click:
  # - element: btn_save
  #   region: footer
  #   trigger: click
  #   guard: "form.isValid"
  #   action: navigate
  #   target: S02
  #   payload: {}
  #   effects: []
  #
  # Example — open modal:
  # - element: btn_add
  #   region: header
  #   trigger: click
  #   action: open_overlay
  #   target: M01
```

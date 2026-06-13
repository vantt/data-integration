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

```
<!-- ASCII wireframe of the screen layout. Replace with actual regions. -->
┌ HEADER ──────────────────────────────────────┐
│  [Logo]              [Nav]        [User Menu] │
├──────────────────────────────────────────────┤
│                                              │
│                   BODY                       │
│   (main content area)                        │
│                                              │
├ FOOTER ──────────────────────────────────────┤
│  [Links]                        [Copyright]  │
└──────────────────────────────────────────────┘
```

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

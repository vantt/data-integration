---
id: {ID}
type: modal
name: "{NAME}"
platforms: [desktop, mobile]
hosts: []        # screens that can open this modal
status: active
design_ref: ""
rules: []
regions: [header, body, actions]
---

# {ID} — {NAME}

## Purpose
<!-- Why this modal exists. What decision or action it captures.
     Example: "Confirms destructive delete action before execution." -->

## Layout

```
<!-- ASCII wireframe of the modal. -->
┌ MODAL ─────────────────────────────┐
│  {NAME}                      [✕]   │
├────────────────────────────────────┤
│                                    │
│   BODY                             │
│   (form fields / confirmation msg) │
│                                    │
├────────────────────────────────────┤
│  ACTIONS: [Cancel]      [Confirm]  │
└────────────────────────────────────┘
```

## States
<!-- - default: opened fresh
     - submitting: async action in progress
     - error: validation or server error
-->

## Interactions

```yaml {project}-contract
interactions:
  # Close via X button — always include this
  # - element: btn_close
  #   region: header
  #   trigger: click
  #   action: close_overlay
  #
  # Cancel button — return without side effects
  # - element: btn_cancel
  #   region: actions
  #   trigger: click
  #   action: close_overlay
  #
  # Confirm / Submit — primary action
  # - element: btn_confirm
  #   region: actions
  #   trigger: click
  #   guard: "form.isValid"
  #   action: mutate
  #   effects: ["save_record", "show_toast_success"]
  #
  # Return to invoker after close (optional)
  # - element: btn_confirm
  #   region: actions
  #   trigger: click
  #   action: navigate
  #   target: return_to_invoker
```

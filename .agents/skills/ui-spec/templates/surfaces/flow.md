---
id: {ID}
type: flow
name: "{NAME}"
platforms: [desktop, mobile]
hosts: []
status: active
design_ref: ""
rules: []
regions: []
---

# {ID} — {NAME}

## Purpose
<!-- What end-to-end user goal this flow achieves.
     Example: "Guides a new user through account setup: profile → preferences → billing." -->

## Surfaces Involved
<!-- List all screens/modals/panels touched in this flow.
     - S01 — Entry screen
     - M01 — Confirmation modal
     - S02 — Success screen
-->

## Happy Path
<!-- Numbered steps of the ideal path with no errors or branches. -->
1. User arrives at ...
2. User fills ...
3. User confirms ...
4. System saves and navigates to ...

## Branches / Edge Cases
<!-- What happens when things go wrong or the user takes an alternate path. -->

## Flow Contract

```yaml {project}-contract
flow:
  goal: "{NAME} — describe the user goal in one sentence"
  preconditions:
    # - "user.isAuthenticated"
    # - "cart.itemCount > 0"
  steps:
    # List action IDs in order (must match ids defined in surface contracts)
    # - A-S01-PrimaryAction
    # - A-S02-ConfirmAction
  branches:
    # Alternate paths keyed by condition
    # - when: "payment.failed"
    #   action: A-S02-RetryPayment
    # - when: "user.cancelled"
    #   action: A-M01-Close
```

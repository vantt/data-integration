---
id: S01
type: screen
name: Home
platforms: [desktop]
hosts: [P01, M01]
regions: [top, side.info]
rules: []
---
# S01 Home

## Interactions

```yaml fx-contract
interactions:
  - { id: A-S01-001, element: go_btn, trigger: click, action: navigate, target: S99 }
  - { id: A-S01-002, element: mystery_btn, trigger: click, action: mutate, region: nowhere, effects: [P99.reload] }
  - { id: A-S01-003, element: tab_a, trigger: click, action: show_panel, target: M01 }
  - { id: A-S01-LSN01, listens_to: ghost_event, action: mutate, effects: [x.y] }
  - { id: A-S01-004, element: go_btn, trigger: click, action: mutate }
  - { id: A-S01-005, element: pay_btn, trigger: click, action: navigate, target: S01, payload: { order_id: "$orderId" } }
```

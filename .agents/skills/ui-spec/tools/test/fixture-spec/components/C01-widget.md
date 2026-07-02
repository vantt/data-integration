---
id: C01
type: component
name: Widget
hosted_by: [S01]
---
# C01 Widget — seeded defect: component using navigate (VR-COMPONENT-NAV)

```yaml fx-contract
interactions:
  - { id: A-C01-001, element: link, trigger: click, action: navigate, target: S01 }
emits:
  - { id: A-C01-002, element: chip, trigger: click, event: widget.lonely_event }
```

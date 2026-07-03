---
id: S02
type: screen
name: Caller
platforms: [desktop]
hosts: [P01]
regions: []
rules: []
---
# S02 Caller — seeded defect: S02.hosts includes P01 but P01.hosted_by does not include S02 (VR-HOSTS-BIDIR reverse)

```yaml fx-contract
interactions:
  - { id: A-S02-001, element: back_btn, trigger: click, action: navigate, target: S01 }
```

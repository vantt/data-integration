---
id: M01
type: modal
name: Edit
---
# M01 Edit — seeded defects: no exit action (VR-MODAL-EXIT), duplicate action id (VR-ID-UNIQUE)

```yaml fx-contract
interactions:
  - { id: A-S01-001, element: save_btn, trigger: click, action: mutate, effects: [thing.save] }
```

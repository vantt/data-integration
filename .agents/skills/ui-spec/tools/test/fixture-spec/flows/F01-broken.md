---
id: F01
type: flow
name: Broken Flow
---
# F01 Broken Flow — seeded defect: dangling flow step A-DEAD-999 (VR-FLOW)

```yaml fx-contract
flow:
  goal: "test flow with a dangling step reference"
  steps: [A-S01-001, A-DEAD-999]
```

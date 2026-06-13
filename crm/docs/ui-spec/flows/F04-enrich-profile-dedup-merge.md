---
id: F04
type: flow
name: "Enrich Profile + Dedup Merge"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: []
regions: []
---

# F04 — Enrich Profile + Dedup Merge

## Purpose

Luồng Manager làm giàu hồ sơ khách: duyệt dedup candidate, merge 2 party trùng lặp, sau đó
thêm custom field + tag + assign owner. Tương ứng J4 trong PRD.

## Surfaces Involved

- S04 — Dedup Review
- M01 — Merge Confirm Modal
- S03 — Customer 360 Detail
- M06 — Custom Fields Edit Modal
- M03 — Tag Management Modal
- M04 — Assign Owner Modal

## Happy Path

1. Manager mở S04 → thấy candidate "Nguyễn Văn A" vs "NVA" (exact_phone match)
2. Manager xem detail pane: 2 party, identities, orders
3. Manager click btn_merge → M01 hiện tóm tắt + confirm checkbox
4. Manager check checkbox → btn_confirm_merge → party B merged vào A, snapshot lưu
5. SSE party.merged → S04 cập nhật, navigate về S03 của surviving party A
6. Manager click btn_edit_custom_fields → M06, điền "Da nhạy cảm = true"
7. Manager click btn_add_tag → M03, thêm tag "VIP-repeat"
8. Manager click btn_assign_owner → M04, gán NV phụ trách

## Branches / Edge Cases

- Merge thất bại ERR-MERGE-CONSTRAINT: M01 hiện error, Manager resolve thủ công
- Manager reject candidate: A-S04-003 → candidate status=rejected

## Flow Contract

```yaml crm-contract
flow:
  goal: "Manager merge dedup candidate rồi làm giàu hồ sơ surviving party"
  preconditions:
    - "user.role == manager"
    - "crm_dedup_candidate has pending items"
  steps:
    - A-S04-002
    - A-M01-003
    - A-S03-010
    - A-M06-003
    - A-S03-003
    - A-M03-005
    - A-S03-002
    - A-M04-003
  branches:
    - { when: "merge constraint error", action: A-M01-001 }
    - { when: "reject candidate", action: A-S04-003 }
```

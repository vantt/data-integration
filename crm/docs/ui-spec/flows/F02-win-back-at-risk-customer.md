---
id: F02
type: flow
name: "Win-back At-risk Customer"
platforms: [desktop]
hosted_by: []
status: active
design_ref: ""
rules: []
regions: []
---

# F02 — Win-back At-risk Customer

## Purpose

Luồng Manager tạo chiến dịch win-back cho segment khách at-risk/churned, gán NV, theo dõi conversion.
Tương ứng J2 trong PRD.

## Surfaces Involved

- S08 — Segments List
- S09 — Segment Builder
- S10 — Campaigns List
- S11 — Campaign Detail / Targets
- M07 — Create / Edit Campaign Modal
- M12 — Record Conversion Modal

## Happy Path

1. Manager vào S08, nhấn btn_create_segment → S09
2. Manager định nghĩa rule: value_group=GOLD, customer_status=churned
3. Manager nhấn Save & Materialize → segment "Win-back GOLD Q3" tạo với 87 member
4. Manager nhấn "Dùng trong chiến dịch" → S10 với segment prefilled
5. Manager nhấn btn_create_campaign → M07, điền tên/objective/assignee/scheduled_at
6. Manager lưu → campaign targets generated (87 − consent-excluded)
7. NV Sales thấy targets trong S11, gọi lần lượt, ghi converted_order_code qua M12
8. SSE campaign.target.converted → S11 stats update realtime

## Branches / Edge Cases

- Segment 0 members sau consent filter: ST-SEGMENT-EMPTY-MEMBERS warning ở S09
- NV ghi conversion thủ công trước khi hệ thống tự khớp: M12 cho phép manual entry

## Flow Contract

```yaml crm-contract
flow:
  goal: "Manager tạo segment win-back, campaign, gán NV, theo dõi conversion"
  preconditions:
    - "user.role == manager"
    - "wh_customer_insight has churned GOLD customers"
  steps:
    - A-S08-001
    - A-S09-006
    - A-S08-003
    - A-S10-001
    - A-M07-004
    - A-S11-003
    - A-M12-004
  branches:
    - { when: "segment preview = 0 members", action: A-S09-005 }
    - { when: "target skipped", action: A-S11-004 }
```

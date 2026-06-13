---
id: F05
type: flow
name: "Build Segment → Run Campaign → Measure Conversion"
platforms: [desktop]
hosts: []
status: active
design_ref: ""
rules: []
regions: []
---

# F05 — Build Segment → Run Campaign → Measure Conversion

## Purpose

Luồng Manager tạo segment động từ insight warehouse, tạo campaign gắn segment, NV liên hệ
từng target, đo conversion rate + attributed revenue sau 30 ngày. Tương ứng J5 trong PRD.

## Surfaces Involved

- S08 — Segments List
- S09 — Segment Builder
- S10 — Campaigns List
- M07 — Create / Edit Campaign Modal
- S11 — Campaign Detail / Targets
- M12 — Record Conversion Modal

## Happy Path

1. Manager vào S08 → btn_create_segment → S09
2. Manager định nghĩa rule: customer_status=at_risk, value_group=VIP|GOLD,
   next_purchase_signal=OVERDUE
3. Preview hiện 34 party (3 loại do consent) → btn_save_materialize
4. Manager navigate S10 → btn_create_campaign → M07
5. Manager chọn segment vừa tạo, channel=messenger, assign NV D, scheduled_at=01/07
6. M07 save → 31 campaign_target generated (consent filtered)
7. NV D xem S11, liên hệ lần lượt target list
8. Khi khách đặt đơn: auto-conversion tracker khớp → SSE campaign.target.converted
9. Với target chưa tự khớp: NV click btn_mark_converted → M12, nhập order_code
10. Sau 30 ngày: S11 summary bar hiện conversion rate + revenue_attributed

## Branches / Edge Cases

- Segment 0 member: ST-BUILDER-PREVIEW-ZERO warning, Manager điều chỉnh rule
- Consent filter loại toàn bộ: ERR-CONSENT-BLOCK, Manager kiểm tra data consent
- NV bỏ qua target: A-S11-004 btn_mark_skipped → status=skipped

## Flow Contract

```yaml crm-contract
flow:
  goal: "Tạo segment động → campaign → NV liên hệ targets → đo conversion"
  preconditions:
    - "user.role == manager"
    - "wh_customer_insight refreshed"
  steps:
    - A-S08-001
    - A-S09-006
    - A-S08-003
    - A-S10-001
    - A-M07-004
    - A-S11-003
    - A-M12-004
  branches:
    - { when: "preview = 0 members", action: A-S09-004 }
    - { when: "target skipped", action: A-S11-004 }
    - { when: "manual conversion entry", action: A-S11-003 }
```

---
id: F06
type: flow
name: "Ad → Lead → Attribution"
platforms: [desktop]
hosted_by: []
status: active
design_ref: ""
rules: []
regions: []
---

# F06 — Ad → Lead → Attribution

## Purpose

Luồng theo dõi full funnel quảng cáo Facebook: Python ingest spend/lead → CSKH resolve PSID
từ ad-referral → link party → khách đặt đơn → attribution last-touch ghi nhận. Tương ứng J6
trong PRD.

## Surfaces Involved

- S12 — Ads Tracking
- S05 — Inbox
- S06 — Conversation Detail
- M11 — Link Party to Conversation Modal
- S03 — Customer 360 Detail

## Happy Path

1. Python FB Ads job ingest: crm_ad_campaign + crm_ad_spend + crm_ad_lead (PSID + ad_ref)
2. Messenger conversation tạo với ad_ref trong crm_conversation
3. CSKH mở S05 → thấy conversation từ ad (badge "Chưa link") → S06
4. CSKH link PSID → party qua M11 (hoặc tạo mới M02)
5. crm_ad_lead.party_id cập nhật sau khi psid linked
6. Khách đặt đơn trên Sapo → wh_order_hdr incremental sync
7. Go attribution job: tìm ad_lead của party trước order_date → ghi crm_ad_attribution last-touch
8. S12: Manager xem CPC / CPL / revenue attributed per campaign

## Branches / Edge Cases

- PSID không có ad_ref: conversation không link vào ad_lead, attribution skip
- Nhiều ad click trước đơn: last-touch lấy ad_campaign gần nhất

## Flow Contract

```yaml crm-contract
flow:
  goal: "Theo dõi full funnel: FB ad spend → Messenger lead → party resolve → order attribution"
  preconditions:
    - "crm_ad_campaign ingested by Python job"
    - "conversation has ad_ref in external metadata"
  steps:
    - A-S05-001
    - A-S06-005
    - A-M11-005
    - A-S06-006
    - A-S12-001
  branches:
    - { when: "party not found", action: A-M11-006 }
    - { when: "no ad_ref on conversation", action: A-S06-002 }
```

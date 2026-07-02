---
id: F03
type: flow
name: "Inbound Chat → Resolve PSID → Link Party"
platforms: [desktop]
hosted_by: []
status: active
design_ref: ""
rules: []
regions: []
---

# F03 — Inbound Chat → Resolve PSID → Link Party

## Purpose

Luồng CSKH xử lý tin nhắn Messenger inbound từ PSID chưa khớp party: mở inbox, đọc nội dung,
tìm/link khách, ghi note, đóng hội thoại. Tương ứng J3 trong PRD.

## Surfaces Involved

- S05 — Inbox
- S06 — Conversation Detail
- M11 — Link Party to Conversation Modal
- M02 — Create Party Modal (nếu chưa có party)
- M10 — Close Conversation Modal
- S03 — Customer 360 Detail (optional, xem đầy đủ sau khi link)

## Happy Path

1. CSKH mở S05 → thấy conversation với badge "Chưa link khách" (ST-INBOX-UNRESOLVED-PSID)
2. CSKH click conv_row → S06, thấy message thread
3. CSKH đọc nội dung → khách nhắn SĐT → CSKH click btn_link_party → M11
4. CSKH nhập SĐT trong M11 search, chọn party phù hợp, click btn_link_party
5. M11 lưu identity psid → party, conversation.party_id cập nhật
6. S06 sidebar hiện Customer 360 summary (tên, GOLD, action_queue)
7. CSKH ghi note (btn_log_note → M08), sau đó đóng hội thoại (btn_close_conversation → M10)
8. Activity type=chat tạo tự động gắn party

## Branches / Edge Cases

- Khách chưa có trong hệ thống: M11 → btn_create_new_party → M02 tạo mới, sau đó link
- CSKH không tìm được khách: đóng conversation không link, party_id vẫn null

## Flow Contract

```yaml crm-contract
flow:
  goal: "CSKH link PSID Messenger vào party CRM, ghi note, đóng conversation"
  preconditions:
    - "user.role == care"
    - "conversation.party_id == null"
  steps:
    - A-S05-001
    - A-S06-005
    - A-M11-003
    - A-M11-005
    - A-S06-003
    - A-M08-003
    - A-S06-002
    - A-M10-003
  branches:
    - { when: "party not found in search", action: A-M11-006 }
    - { when: "cannot identify customer", action: A-M10-003 }
```

# Phase 05 — Activity Log + Tasks + Conversation/Chat Tracking

**Context:** [plan.md](plan.md) · Report: `plans/reports/schema-scan-260613-1133-engagement-chat-ads-channel-domain-report.md`

## Overview
- **Priority:** P1
- **Status:** ⬜ (cần Phase 02 party)
- Flow tác nghiệp: nhật ký tương tác, giao việc follow-up, và **theo dõi hội thoại** (chat) gắn với khách. Worklist follow-up có thể sinh từ `wh_cache.action_queue`.
- **Chat: v1 chỉ Messenger** (Shopee + Zalo để sau). Schema `conversation/message` tổng quát theo `channel` → thêm 2 kênh sau chỉ là viết adapter, không đổi schema.

## Key Insights
- Warehouse FB Messenger models **disabled stubs** — KHÔNG data, KHÔNG link customer. CRM phải **tự ingest** chat từ FB Graph API và **tự build psid→party** (qua `crm.party_identity` type=`psid`).
- Không có precedent gán NV cho hội thoại → CRM tự thiết kế inbox assignment.
- `action_queue` (Phase 04) là nguồn task tự động (CALL_NOW, WIN_BACK…) — `task.source='action_queue'`, `source_ref=action_id`.

## Requirements
- **FR:** activity đa loại (call/note/visit/email/chat) gắn party + NV + (tuỳ chọn) order_code; task có assignee/due/status, sinh từ action_queue hoặc thủ công; conversation đa kênh (messenger/zalo) + messages; gán NV xử lý hội thoại; khớp psid→party.
- **NFR:** message ingest idempotent theo `external_message_id`; inbox query theo assignee/status nhanh.

## Architecture
> DDL Postgres-style — map **SQLite** theo Quy ước [plan.md](plan.md): `crm_*` prefix, `uuid`→`TEXT`, `timestamptz`→`TEXT` UTC, `jsonb`(attachments)→`TEXT`+JSON1, ở `crm.db`.

### Core DDL
```sql
CREATE TABLE crm.activity (
  activity_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  party_id uuid NOT NULL REFERENCES crm.party(party_id),
  activity_type text NOT NULL,     -- call|note|visit|email|chat|other
  direction text,                   -- in|out
  channel text,                     -- phone|messenger|zalo|store|...
  subject text, body text, outcome text,
  related_order_code text,          -- gắn đơn (không FK cứng — order ở warehouse)
  staff_user_id uuid REFERENCES crm.app_user(user_id),
  occurred_at timestamptz NOT NULL DEFAULT now(),
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE crm.task (
  task_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  party_id uuid REFERENCES crm.party(party_id),
  title text NOT NULL, description text,
  due_at timestamptz, priority int DEFAULT 0,
  status text NOT NULL DEFAULT 'open',   -- open|doing|done|cancelled
  assignee_user_id uuid REFERENCES crm.app_user(user_id),
  source text DEFAULT 'manual',          -- manual|action_queue|campaign
  source_ref text,                       -- action_id / campaign_id
  created_by uuid REFERENCES crm.app_user(user_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE TABLE crm.conversation (
  conversation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  party_id uuid REFERENCES crm.party(party_id),   -- nullable cho tới khi resolve ext-id→party
  channel text NOT NULL,                           -- messenger|shopee|zalo
  external_thread_id text NOT NULL, page_id text,  -- page_id=fb page / shopee shop / zalo oa
  status text NOT NULL DEFAULT 'open',             -- open|pending|closed
  assignee_user_id uuid REFERENCES crm.app_user(user_id),
  last_message_at timestamptz, unread_count int DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (channel, external_thread_id)
);
CREATE TABLE crm.message (
  message_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES crm.conversation(conversation_id),
  external_message_id text, direction text,        -- in|out
  sender_ref text, body text, attachments jsonb,
  sent_at timestamptz NOT NULL,
  UNIQUE (conversation_id, external_message_id)
);
CREATE INDEX ON crm.task (assignee_user_id, status, due_at);
CREATE INDEX ON crm.activity (party_id, occurred_at DESC);
CREATE INDEX ON crm.conversation (assignee_user_id, status);
```
### Chat ingest (CRM-owned, mới) — cổng `ChatSource`, v1 chỉ Messenger
```
ports.ChatSource  ← messenger (v1) | shopee, zalo (để sau, cùng interface)
crm/sync/ingest_messenger.py        # v1
# crm/sync/ingest_shopee_chat.py | ingest_zalo_oa.py  # sau, không đổi schema
  FB Graph API → upsert conversation/message (idempotent external_*)
  → resolve identity: party_identity(psid) → gắn party_id
    nếu không → để null, đẩy gợi ý link (phone trong hội thoại) cho NV
```
- identity_type: `psid` (messenger, v1); `shopee_uid`/`zalo_uid` thêm khi build adapter sau.

## Related Code Files
- **Tạo:** `crm/migrations/0007_activity_task_conversation_message.up.sql`, `crm/sync/ingest_messenger.py`, Go inbox/task handler. **Đọc:** `dim_fb_conversations.sql`/`fact_fb_messages.sql` (tham khảo field, dù disabled).

## Implementation Steps
1. Migration 0007 (4 bảng + index).
2. Task generator: map `wh_cache.action_queue` → `crm.task` (idempotent theo source_ref), tránh tạo trùng.
3. Activity CRUD + timeline theo party.
4. Chat ingest từ FB Graph (idempotent) + psid→party resolve.
5. Inbox: list theo assignee/status, gán NV, đóng/mở.

## Todo
- [ ] Migration 0007
- [ ] action_queue → task generator
- [ ] Activity timeline
- [ ] Messenger ingest + psid resolve
- [ ] Inbox assignment

## Success Criteria
- Action "WIN_BACK" → 1 task cho NV (không trùng khi sync lại); timeline khách hiện đủ activity; message ingest 2 lần không nhân đôi; hội thoại có psid khớp party tự gắn.

## Risk Assessment
- **Chat ingest = build mới lớn** → v1 có thể chỉ ingest read (xem hội thoại + gán), gửi tin nhắn 2 chiều để pha sau.
- **psid→party khó** → cho phép null + link thủ công; không chặn luồng.
- **Zalo OA** (câu hỏi mở #2) → schema `channel` đã tổng quát, chỉ thêm ingest adapter.

## Security
- Nội dung chat = PII nhạy cảm → role-gated, audit truy cập.

## Next Steps
→ Phase 06 campaign tạo task/activity hàng loạt. → Phase 07 activity-summary có thể ghi ngược Sapo (nếu API cho).

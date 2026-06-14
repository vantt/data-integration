-- Migration 0004 UP: activity, task, conversation, message
-- SQLite dialect — TEXT uuid (app-generated), TEXT UTC ISO-8601, INTEGER bool, crm_* prefix

-- Activity log: any interaction touchpoint linked to a party
CREATE TABLE IF NOT EXISTS crm_activity (
  activity_id       TEXT PRIMARY KEY,
  party_id          TEXT NOT NULL REFERENCES crm_party(party_id),
  activity_type     TEXT NOT NULL,  -- call|note|visit|email|chat|other
  direction         TEXT,           -- in|out
  channel           TEXT,           -- phone|messenger|zalo|store|...
  subject           TEXT,
  body              TEXT,
  outcome           TEXT,
  related_order_code TEXT,          -- soft ref — order lives in warehouse
  staff_user_id     TEXT REFERENCES crm_app_user(user_id),
  occurred_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_activity_party_occurred
  ON crm_activity (party_id, occurred_at DESC);

-- Task: follow-up work item (manual or auto-generated from action_queue)
CREATE TABLE IF NOT EXISTS crm_task (
  task_id           TEXT PRIMARY KEY,
  party_id          TEXT REFERENCES crm_party(party_id),  -- nullable
  title             TEXT NOT NULL,
  description       TEXT,
  due_at            TEXT,   -- UTC ISO-8601 nullable
  priority          INTEGER NOT NULL DEFAULT 0,
  status            TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'doing', 'done', 'cancelled')),
  assignee_user_id  TEXT REFERENCES crm_app_user(user_id),
  source            TEXT NOT NULL DEFAULT 'manual', -- manual|action_queue|campaign
  source_ref        TEXT,   -- action_id / campaign_id (for idempotency)
  created_by        TEXT REFERENCES crm_app_user(user_id),
  created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  completed_at      TEXT    -- UTC ISO-8601 nullable
);

CREATE TRIGGER IF NOT EXISTS trg_task_touch
AFTER UPDATE ON crm_task
BEGIN
  UPDATE crm_task
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE rowid = NEW.rowid;
END;

CREATE INDEX IF NOT EXISTS idx_task_assignee_status_due
  ON crm_task (assignee_user_id, status, due_at);

-- Unique index for action_queue idempotency: prevents duplicate tasks per source_ref.
-- Manual tasks (source_ref IS NULL) are excluded from the constraint.
CREATE UNIQUE INDEX IF NOT EXISTS uidx_task_source_ref
  ON crm_task (source, source_ref) WHERE source_ref IS NOT NULL;

-- Conversation: a thread of messages on a channel, optionally linked to a party
CREATE TABLE IF NOT EXISTS crm_conversation (
  conversation_id   TEXT PRIMARY KEY,
  party_id          TEXT REFERENCES crm_party(party_id),  -- nullable until psid resolved
  channel           TEXT NOT NULL,     -- messenger|shopee|zalo
  external_thread_id TEXT NOT NULL,    -- psid (Messenger) / shopee buyer id / zalo user id
  page_id           TEXT,             -- FB page id / shopee shop / zalo OA id
  status            TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'pending', 'closed')),
  assignee_user_id  TEXT REFERENCES crm_app_user(user_id),
  last_message_at   TEXT,
  unread_count      INTEGER NOT NULL DEFAULT 0,
  created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (channel, external_thread_id)
);

CREATE TRIGGER IF NOT EXISTS trg_conversation_touch
AFTER UPDATE ON crm_conversation
BEGIN
  UPDATE crm_conversation
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE rowid = NEW.rowid;
END;

CREATE INDEX IF NOT EXISTS idx_conversation_assignee_status
  ON crm_conversation (assignee_user_id, status);

CREATE INDEX IF NOT EXISTS idx_conversation_last_message
  ON crm_conversation (last_message_at DESC);

-- Message: individual message within a conversation (idempotent on external_message_id)
CREATE TABLE IF NOT EXISTS crm_message (
  message_id          TEXT PRIMARY KEY,
  conversation_id     TEXT NOT NULL REFERENCES crm_conversation(conversation_id),
  external_message_id TEXT,    -- FB mid / shopee msg id / zalo msg id
  direction           TEXT,    -- in|out
  sender_ref          TEXT,    -- psid or page_id or staff identifier
  body                TEXT,
  attachments         TEXT,    -- JSON array of attachment objects
  sent_at             TEXT NOT NULL,
  UNIQUE (conversation_id, external_message_id)
);

CREATE INDEX IF NOT EXISTS idx_message_conversation_sent
  ON crm_message (conversation_id, sent_at DESC);

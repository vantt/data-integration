-- Conversation and Message queries (crm_conversation, crm_message)

-- name: UpsertConversation :one
INSERT INTO crm_conversation (
  conversation_id, party_id, channel, external_thread_id, page_id,
  status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (channel, external_thread_id) DO NOTHING
RETURNING conversation_id;

-- name: GetConversationByChannelThread :one
SELECT
  conversation_id, party_id, channel, external_thread_id, page_id,
  status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
WHERE channel = ? AND external_thread_id = ?;

-- name: GetConversationByID :one
SELECT
  conversation_id, party_id, channel, external_thread_id, page_id,
  status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
WHERE conversation_id = ?;

-- name: UpdateConversation :exec
UPDATE crm_conversation
SET
  party_id         = ?,
  status           = ?,
  assignee_user_id = ?,
  last_message_at  = ?,
  unread_count     = ?,
  updated_at       = ?
WHERE conversation_id = ?;

-- name: UpdateConversationOnMessage :exec
-- Atomically advances last_message_at and increments unread_count by delta.
-- Pass delta=1 for inbound messages, delta=0 for echo/outbound.
-- Called only when a new message row was actually inserted (idempotency enforced by caller).
UPDATE crm_conversation
SET
  last_message_at = CASE WHEN last_message_at IS NULL OR last_message_at < ? THEN ? ELSE last_message_at END,
  unread_count    = unread_count + ?
WHERE conversation_id = ?;

-- name: ListConversationsByAssigneeAndStatus :many
SELECT
  conversation_id, party_id, channel, external_thread_id, page_id,
  status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
WHERE assignee_user_id = ? AND status = ?
ORDER BY last_message_at DESC;

-- name: ListConversationsByAssignee :many
SELECT
  conversation_id, party_id, channel, external_thread_id, page_id,
  status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
WHERE assignee_user_id = ?
ORDER BY last_message_at DESC;

-- name: ListConversationsByStatus :many
SELECT
  conversation_id, party_id, channel, external_thread_id, page_id,
  status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
WHERE status = ?
ORDER BY last_message_at DESC;

-- name: ListAllConversations :many
SELECT
  conversation_id, party_id, channel, external_thread_id, page_id,
  status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
ORDER BY last_message_at DESC;

-- name: InsertMessage :one
INSERT INTO crm_message (
  message_id, conversation_id, external_message_id, direction,
  sender_ref, body, attachments, sent_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (conversation_id, external_message_id) DO NOTHING
RETURNING message_id;

-- name: ListMessagesByConversation :many
SELECT
  message_id, conversation_id, external_message_id, direction,
  sender_ref, body, attachments, sent_at
FROM crm_message
WHERE conversation_id = ?
ORDER BY sent_at ASC;

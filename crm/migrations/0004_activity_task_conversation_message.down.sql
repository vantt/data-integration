-- Migration 0004 DOWN: drop activity, task, conversation, message tables

DROP TRIGGER IF EXISTS trg_conversation_touch;
DROP TRIGGER IF EXISTS trg_task_touch;

DROP INDEX IF EXISTS idx_message_conversation_sent;
DROP INDEX IF EXISTS idx_conversation_last_message;
DROP INDEX IF EXISTS idx_conversation_assignee_status;
DROP INDEX IF EXISTS idx_task_assignee_status_due;
DROP INDEX IF EXISTS idx_activity_party_occurred;

DROP TABLE IF EXISTS crm_message;
DROP TABLE IF EXISTS crm_conversation;
DROP TABLE IF EXISTS crm_task;
DROP TABLE IF EXISTS crm_activity;

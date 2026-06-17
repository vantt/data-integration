-- crm_action_state: employee-set lifecycle state for warehouse action_queue items.
-- Keyed on action_id (episode-scoped); auto-expires when a new episode starts
-- (new pending_since → new action_id → old state is orphaned and ignored by queries).
CREATE TABLE IF NOT EXISTS crm_action_state (
  action_id     TEXT    PRIMARY KEY,
  status        TEXT    NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'dismissed', 'snoozed')),
  snoozed_until TEXT,   -- YYYY-MM-DD; only meaningful when status = 'snoozed'
  updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_by    TEXT    REFERENCES crm_app_user(user_id)
);

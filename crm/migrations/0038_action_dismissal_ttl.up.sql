-- Migration 0038 UP: B5 dismiss memory keyed by (party_id, action_type) with 30-day TTL.
--
-- The prior mechanism (crm_action_state, keyed on action_id) loses dismiss memory
-- across the warehouse's weekly action_id regeneration for the same semantic action
-- (same customer + action_type): a rep dismisses an item, the warehouse mart
-- regenerates a new action_id next week for the same item, and it reappears —
-- the rep loses trust in dismiss. This table keys on the semantic identity
-- (party_id, action_type) instead, so a dismiss survives action_id churn.
-- Expires automatically via dismissed_until (30 days from dismiss) so a
-- mistaken/stale dismiss cannot hide a customer forever; after expiry the
-- action reappears with no special badge (unlike snooze-wake).
CREATE TABLE IF NOT EXISTS crm_action_dismissal (
  party_id             TEXT    NOT NULL REFERENCES crm_party(party_id),
  action_type          TEXT    NOT NULL,
  dismissed_by_user_id TEXT    REFERENCES crm_app_user(user_id),
  dismissed_at         TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  dismissed_until      TEXT    NOT NULL,
  PRIMARY KEY (party_id, action_type)
);

-- Manager view (AI-11) lists active (non-expired) dismissals ordered by recency.
CREATE INDEX IF NOT EXISTS idx_action_dismissal_until
  ON crm_action_dismissal (dismissed_until);

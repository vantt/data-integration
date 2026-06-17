-- Migration 0011 UP: rep-curated party insights
-- Distinct from warehouse machine-generated insights (wh_customer_insight in cache.db).
-- Source: M16 (Promote / Create Insight Modal). Surfaces in P01 insight panel.
-- Can be promoted from a note (source_note_id set) or created directly (source_note_id NULL).

CREATE TABLE IF NOT EXISTS crm_party_insight (
  insight_id     TEXT PRIMARY KEY,
  party_id       TEXT NOT NULL REFERENCES crm_party(party_id),
  insight_type   TEXT NOT NULL,
    -- persona | buying_pattern | decision_style | life_event | relationship | advocate_signal
  body           TEXT NOT NULL,
  confidence     TEXT NOT NULL DEFAULT 'medium',
    -- low | medium | high
  source_note_id TEXT REFERENCES crm_note(note_id),
  created_by     TEXT REFERENCES crm_app_user(user_id),
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  deleted_at     TEXT
);

CREATE TRIGGER IF NOT EXISTS trg_party_insight_touch
AFTER UPDATE ON crm_party_insight
BEGIN
  UPDATE crm_party_insight
  SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
  WHERE rowid = NEW.rowid;
END;

CREATE INDEX IF NOT EXISTS idx_insight_party
  ON crm_party_insight (party_id) WHERE deleted_at IS NULL;

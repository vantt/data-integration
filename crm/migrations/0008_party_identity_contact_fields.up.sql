-- Migration 0008 UP: contact channel management fields on crm_party_identity
-- Enables M15 (Edit Contact & Core Info Modal) — add/edit/deactivate contact channels
-- is_preferred: at most one identity per party should be preferred (enforced at app layer)

ALTER TABLE crm_party_identity ADD COLUMN display_label  TEXT;
  -- optional human-readable label, e.g. "Số công ty", "Zalo cá nhân"
ALTER TABLE crm_party_identity ADD COLUMN contact_status TEXT NOT NULL DEFAULT 'active';
  -- active | invalid | unreachable — soft-deactivate instead of hard delete
ALTER TABLE crm_party_identity ADD COLUMN is_preferred   INTEGER NOT NULL DEFAULT 0;
  -- 1 = preferred channel for outreach; only 1 per party enforced by app

CREATE INDEX IF NOT EXISTS idx_identity_party_status
  ON crm_party_identity (party_id, contact_status);

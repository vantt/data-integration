-- Mirror rebuild back to the 0038 shape. Collapses the per-mart rows back to one row per
-- (party_id, action_type), keeping the LATEST dismissed_until — never shortens an active
-- suppression on rollback. dismissed_by_user_id/dismissed_at come along with that same row.
CREATE TABLE IF NOT EXISTS crm_action_dismissal_old (
  party_id             TEXT    NOT NULL REFERENCES crm_party(party_id),
  action_type          TEXT    NOT NULL,
  dismissed_by_user_id TEXT    REFERENCES crm_app_user(user_id),
  dismissed_at         TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  dismissed_until      TEXT    NOT NULL,
  PRIMARY KEY (party_id, action_type)
);

INSERT OR IGNORE INTO crm_action_dismissal_old
  (party_id, action_type, dismissed_by_user_id, dismissed_at, dismissed_until)
SELECT d.party_id, d.action_type, d.dismissed_by_user_id, d.dismissed_at, d.dismissed_until
FROM crm_action_dismissal d
WHERE d.dismissed_until = (
  SELECT MAX(d2.dismissed_until)
  FROM crm_action_dismissal d2
  WHERE d2.party_id = d.party_id AND d2.action_type = d.action_type
);

DROP TABLE crm_action_dismissal;

ALTER TABLE crm_action_dismissal_old RENAME TO crm_action_dismissal;

CREATE INDEX IF NOT EXISTS idx_action_dismissal_until
  ON crm_action_dismissal (dismissed_until);

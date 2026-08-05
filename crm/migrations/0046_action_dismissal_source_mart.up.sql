-- Suppression is now tracked per originating mart so a customer-level REORDER_NUDGE can be
-- turned off while the per-SKU REORDER_NUDGE for the same customer keeps firing. SQLite cannot
-- alter a primary key in place, so the table is rebuilt. Pre-existing rows were mart-agnostic
-- ("suppress everywhere") and are expanded into one row per mart to preserve that meaning.
-- No PRAGMA foreign_keys=OFF here — SQLite ignores it inside a transaction anyway (the migration
-- runner always runs with foreign_keys=ON inside a savepoint); crm_action_dismissal has only
-- outgoing FKs and nothing else references it, so the rebuild is safe without it.
CREATE TABLE IF NOT EXISTS crm_action_dismissal_new (
  party_id             TEXT    NOT NULL REFERENCES crm_party(party_id),
  action_type          TEXT    NOT NULL,
  source_mart          TEXT    NOT NULL
    CHECK (source_mart IN ('mart_customer_action_queue','mart_customer_sku_action_queue')),
  dismissed_by_user_id TEXT    REFERENCES crm_app_user(user_id),
  dismissed_at         TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  dismissed_until      TEXT    NOT NULL,
  PRIMARY KEY (party_id, action_type, source_mart)
);

INSERT OR IGNORE INTO crm_action_dismissal_new
  (party_id, action_type, source_mart, dismissed_by_user_id, dismissed_at, dismissed_until)
SELECT d.party_id, d.action_type, m.mart_name,
       d.dismissed_by_user_id, d.dismissed_at, d.dismissed_until
FROM crm_action_dismissal d
CROSS JOIN (
  SELECT 'mart_customer_action_queue' AS mart_name
  UNION ALL
  SELECT 'mart_customer_sku_action_queue'
) m;

DROP TABLE crm_action_dismissal;

ALTER TABLE crm_action_dismissal_new RENAME TO crm_action_dismissal;

CREATE INDEX IF NOT EXISTS idx_action_dismissal_until
  ON crm_action_dismissal (dismissed_until);

CREATE INDEX IF NOT EXISTS idx_action_dismissal_party
  ON crm_action_dismissal (party_id, source_mart);

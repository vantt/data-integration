-- crm_last_contact: one row per customer, upserted on every activity log.
-- last_activity_id links to crm_activity for full-detail drill-through.
-- The WHERE clause on upsert ensures older activities never overwrite newer ones.
CREATE TABLE IF NOT EXISTS crm_last_contact (
  party_id            TEXT PRIMARY KEY,
  last_activity_id    TEXT NOT NULL REFERENCES crm_activity(activity_id),
  last_contacted_at   TEXT NOT NULL,  -- ISO-8601 UTC (occurred_at from activity)
  last_contact_result TEXT NOT NULL,  -- answered|no_answer|callback|refused|replied|no_reply|met|not_met|other
  channel             TEXT,           -- call|zalo|fb|email|visit|other
  updated_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_crm_last_contact_at ON crm_last_contact (last_contacted_at DESC);

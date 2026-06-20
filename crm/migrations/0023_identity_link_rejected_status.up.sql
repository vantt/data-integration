-- Migration 0023 UP: add 'rejected' to crm_identity_link.status allowed values
--
-- SQLite CHECK constraints cannot be altered in place; the only safe approach is
-- the recommended table-rebuild: create new table, copy data, swap names.
-- This migration widens the allowed set from ('linked','needs_review') to
-- ('linked','needs_review','rejected') so CS agents can dismiss flagged links.
--
-- Rejected rows stay in the table for audit purposes but are excluded from the
-- review queue (WHERE status='needs_review') and must never be re-applied as
-- identities to any party.

-- Step 1: create replacement table with the widened CHECK
CREATE TABLE IF NOT EXISTS crm_identity_link_v2 (
    token                TEXT NOT NULL,
    buyer_customer_id    TEXT,
    scanner_phone        TEXT,
    scanner_zalo_uid     TEXT,
    resolved_customer_id TEXT,
    confidence           REAL NOT NULL DEFAULT 1.0,
    status               TEXT NOT NULL CHECK (status IN ('linked', 'needs_review', 'rejected')),
    ts                   TEXT NOT NULL,

    UNIQUE (token, scanner_phone)
);

-- Step 2: copy all existing rows (all have status in the old allowed set, so CHECK passes)
INSERT INTO crm_identity_link_v2
SELECT token, buyer_customer_id, scanner_phone, scanner_zalo_uid,
       resolved_customer_id, confidence, status, ts
FROM crm_identity_link;

-- Step 3: drop the old table (and its indexes — they reference the old table)
DROP INDEX IF EXISTS idx_identity_link_resolved;
DROP INDEX IF EXISTS idx_identity_link_token;
DROP INDEX IF EXISTS idx_identity_link_status;
DROP TABLE IF EXISTS crm_identity_link;

-- Step 4: rename replacement into place
ALTER TABLE crm_identity_link_v2 RENAME TO crm_identity_link;

-- Step 5: recreate indexes on the renamed table
CREATE INDEX IF NOT EXISTS idx_identity_link_status
    ON crm_identity_link (status);

CREATE INDEX IF NOT EXISTS idx_identity_link_token
    ON crm_identity_link (token);

CREATE INDEX IF NOT EXISTS idx_identity_link_resolved
    ON crm_identity_link (resolved_customer_id)
    WHERE resolved_customer_id IS NOT NULL;

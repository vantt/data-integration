-- Migration 0022 UP: hug_identity_link — per-token identity resolution outcomes
--
-- Each row records how a Hug opt-in event was resolved:
--   * which token was scanned
--   * who the buyer was (from the token's order context)
--   * what phone/zalo_uid the scanner left
--   * which CRM party the opt-in was routed to (resolved_customer_id)
--   * confidence score and review status for the CS queue
--
-- Idempotency: UNIQUE(token, scanner_phone) — re-processing the same (token, phone)
-- pair updates the existing row instead of inserting a duplicate.
-- NULL scanner_phone rows (Zalo-only opt-ins) are each treated as distinct events
-- because SQLite NULL != NULL; that is intentional (each zalo-only opt-in stands alone).
--
-- contact_quality enum mapping (§8 contactability ladder vs existing crm_party_identity):
--   masked           → existing 'masked' (no contact data)
--   zalo_follower    → NEW value added in this migration: signals OA follow without phone
--   phone_unverified → existing 'unverified' (phone captured but not OTP-confirmed)
--   phone_verified   → existing 'verified' (confirmed by successful contact)
-- The resolver writes 'zalo_follower' to crm_party_identity.contact_quality.
-- Existing rows with 'masked'/'unverified'/'verified' are NOT touched.
-- Only upgrades are applied (contactability ladder is strictly non-decreasing).

CREATE TABLE IF NOT EXISTS crm_identity_link (
    token                TEXT NOT NULL,
    buyer_customer_id    TEXT,           -- Sapo customer_id from the token's order; NULL if not resolved
    scanner_phone        TEXT,           -- normalised VN format (09...); NULL if Zalo-only
    scanner_zalo_uid     TEXT,           -- Zalo UID from opt-in; NULL if not provided
    resolved_customer_id TEXT,           -- CRM party_id the opt-in was routed to; NULL if unresolvable
    confidence           REAL NOT NULL DEFAULT 1.0,  -- 0.0–1.0; lower when routed to needs_review
    status               TEXT NOT NULL CHECK (status IN ('linked', 'needs_review')),
    ts                   TEXT NOT NULL,  -- UTC ISO-8601 when this row was written/updated

    -- Idempotency: same (token + phone) seen again → update in place
    UNIQUE (token, scanner_phone)
);

-- Fast path for the CS review queue (task 5 will query WHERE status = 'needs_review')
CREATE INDEX IF NOT EXISTS idx_identity_link_status
    ON crm_identity_link (status);

-- Lookup by token (attribution, per-token resolution check)
CREATE INDEX IF NOT EXISTS idx_identity_link_token
    ON crm_identity_link (token);

-- Lookup by resolved party (customer 360 view join)
CREATE INDEX IF NOT EXISTS idx_identity_link_resolved
    ON crm_identity_link (resolved_customer_id)
    WHERE resolved_customer_id IS NOT NULL;

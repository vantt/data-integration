-- Migration 0025 UP: crm_hug_voucher + v_hug_voucher_attribution
--
-- crm_hug_voucher is the local master issuance ledger: "code X was issued to
-- customer Y from campaign Z".  The local CRM is the brain; the edge D1
-- hug_voucher table (schema_hug.sql) is a deferred projection (not in scope here).
--
-- Schema mirrors the edge hug_voucher table column-for-column so a future push
-- requires no transform.  Natural key (code, customer_id): one row per
-- campaign-code × customer pair.  redeemed_at and order_code start NULL and are
-- set by the redeem matcher when fact_orders.order_coupon_code matches.

CREATE TABLE IF NOT EXISTS crm_hug_voucher (
    code         TEXT NOT NULL,
    customer_id  TEXT NOT NULL,
    token        TEXT,              -- hug_token that triggered issuance (nullable: some flows may not have a token)
    campaign_id  TEXT NOT NULL,
    min_order    INTEGER,           -- min order value in VND at issuance time (informational)
    sku_guard    TEXT,              -- JSON list of excluded SKUs (informational)
    issued_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    redeemed_at  TEXT,              -- set by redeem matcher when the matching order is found
    order_code   TEXT,              -- Sapo order_code of the redeeming order
    PRIMARY KEY (code, customer_id)
);

-- Fast lookup by campaign (attribution queries, quota checks)
CREATE INDEX IF NOT EXISTS idx_crm_hug_voucher_campaign
    ON crm_hug_voucher (campaign_id);

-- Fast lookup by customer (dedup check at issuance, customer timeline)
CREATE INDEX IF NOT EXISTS idx_crm_hug_voucher_customer
    ON crm_hug_voucher (customer_id);

-- Fast lookup by token (resolve issuance from a scan event)
CREATE INDEX IF NOT EXISTS idx_crm_hug_voucher_token
    ON crm_hug_voucher (token);

-- Partial index: redeem matcher iterates only unmatched rows
CREATE INDEX IF NOT EXISTS idx_crm_hug_voucher_unmatched
    ON crm_hug_voucher (code, customer_id) WHERE redeemed_at IS NULL;

-- Attribution view: issued vs redeemed counts per (campaign, code).
-- redeem_rate_pct = (redeemed / issued) * 100, rounded to 1 decimal.
-- COUNT(redeemed_at) counts only non-NULL rows (i.e. redeemed vouchers).
CREATE VIEW IF NOT EXISTS v_hug_voucher_attribution AS
SELECT
    campaign_id,
    code,
    COUNT(*)              AS issued,
    COUNT(redeemed_at)    AS redeemed,
    ROUND(
        CAST(COUNT(redeemed_at) AS REAL) / NULLIF(COUNT(*), 0) * 100,
        1
    )                     AS redeem_rate_pct
FROM crm_hug_voucher
GROUP BY campaign_id, code;

-- Hug Dynamic Touchpoint Platform — D1 persistent tables
-- Apply AFTER schema.sql (which handles the webhooks queue).
-- These tables have a DIFFERENT lifecycle: NOT drained/deleted on ack.
-- Apply with: wrangler d1 execute fgcare-webhook-db --remote --file=schema_hug.sql
-- DO NOT apply to production until the coordinated deploy step.

-- ---------------------------------------------------------------------------
-- hug_token  (edge projection of bound tokens; master lives in local DB)
-- Tokens are generated locally (random 12-char Crockford base32) and pushed
-- here via POST /hug/token/upsert only when status='bound'.
-- unbound / printed-only tokens stay local-only → scans fall to DEFAULT.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hug_token (
    token         TEXT PRIMARY KEY,          -- opaque random-12 Crockford-b32, unique
    customer_id   TEXT,                      -- nullable: may be unlinked (acquire op)
    op_type       TEXT NOT NULL,             -- package_insert | loyalty_card | winback_flyer | receipt | acquire | ...
    order_code    TEXT,                      -- Sapo order code at pack time (bind key)
    channel       TEXT,                      -- shopee | tiki | website | pos | ...
    ship_date     TEXT,                      -- ISO date YYYY-MM-DD (approx)
    sku           TEXT,                      -- primary SKU on the order (informational)
    campaign_hint TEXT,                      -- optional: preferred campaign_id at pack time
    status        TEXT NOT NULL DEFAULT 'bound',  -- bound | revoked
    batch_id      TEXT,                      -- pack-run batch identifier
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_hug_token_customer ON hug_token(customer_id);
CREATE INDEX IF NOT EXISTS idx_hug_token_batch    ON hug_token(batch_id);

-- ---------------------------------------------------------------------------
-- hug_customer  (nightly replica snapshot from mart_customer_tier ~7.5k rows)
-- Gives Worker access to tier/recency without calling local host.
-- Local pushes changed rows each night via POST /hug/customer/upsert.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hug_customer (
    customer_id   TEXT PRIMARY KEY,
    tier          TEXT,                      -- VIP | CORE | CASUAL | NEW | MASKED_REPEAT | ...
    recency_days  INTEGER,                   -- days since last order
    value_group   TEXT,                      -- HIGH | MID | LOW
    is_contactable INTEGER NOT NULL DEFAULT 0,  -- 0/1; 1 = has phone or zalo uid
    customer_type TEXT,                      -- WHOLESALE | CROSSBORDER | PARTNER | STAFF | KOL | RETAIL | NULL
                                             -- Added via migrations/add_hug_customer_type_column.sql
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- ---------------------------------------------------------------------------
-- hug_campaign  (routing rules; managed via POST /hug/campaign/upsert)
-- targeting JSON follows the AND/OR model from discussion-hug.md §7:
--   { "op_type": ["package_insert","loyalty_card"], "tier": ["VIP","CORE"] }
--   → top-level keys ANDed; list values ORed within each key.
--   Missing key = no constraint on that attribute.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hug_campaign (
    campaign_id      TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    targeting        TEXT NOT NULL DEFAULT '{}',  -- JSON object; '{}' = DEFAULT (always matches)
    destination_type TEXT NOT NULL,               -- zalo_oa | cf_pages | url
    destination_url  TEXT NOT NULL,               -- redirect target
    offer_ref        TEXT,                        -- voucher/campaign code (e.g. "HUG50")
    priority         INTEGER NOT NULL DEFAULT 100, -- lower = higher priority; DEFAULT campaign uses max int
    schedule_start   TEXT,                        -- ISO datetime or NULL (no start constraint)
    schedule_end     TEXT,                        -- ISO datetime or NULL (no end constraint)
    quota_total      INTEGER,                     -- NULL = unlimited
    quota_used       INTEGER NOT NULL DEFAULT 0,
    status           TEXT NOT NULL DEFAULT 'active', -- active | paused | archived
    updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_hug_campaign_status_priority ON hug_campaign(status, priority);

-- ---------------------------------------------------------------------------
-- hug_voucher  (issuance ledger; NOT a redemption engine — Sapo handles that)
-- Records "we issued code X to customer Y from campaign Z".
-- Redemption is detected downstream via fact_orders.order_coupon_code pipeline.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hug_voucher (
    code         TEXT NOT NULL,              -- shared-per-campaign code (e.g. "HUG50") or unique code
    customer_id  TEXT NOT NULL,
    token        TEXT,                       -- hug_token that triggered issuance
    campaign_id  TEXT NOT NULL,
    min_order    INTEGER,                    -- min order value in VND for this issuance (informational)
    sku_guard    TEXT,                       -- JSON list of excluded SKUs (informational)
    issued_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    redeemed_at  TEXT,                       -- set by local pipeline when order_coupon_code matches
    order_code   TEXT,                       -- Sapo order_code when redeemed
    PRIMARY KEY (code, customer_id)          -- one code+customer pair = one voucher row
);

CREATE INDEX IF NOT EXISTS idx_hug_voucher_token      ON hug_voucher(token);
CREATE INDEX IF NOT EXISTS idx_hug_voucher_campaign   ON hug_voucher(campaign_id);
CREATE INDEX IF NOT EXISTS idx_hug_voucher_customer   ON hug_voucher(customer_id);

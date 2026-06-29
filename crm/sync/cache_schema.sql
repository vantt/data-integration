-- cache.db DDL — warehouse read-cache for CRM.
-- Python is the SOLE writer. Go ATTACHes this file read-only.
-- No FK constraints (bulk-load order not guaranteed; integrity owned by warehouse).
-- Money = INTEGER (VND); pct = REAL; timestamps = TEXT UTC ISO-8601 'Z'.

-- ─── GROUP 2: Computed insight (warehouse has already calculated these) ────────

CREATE TABLE IF NOT EXISTS wh_customer_insight (
  customer_key                TEXT    PRIMARY KEY,  -- MD5 surrogate from warehouse
  customer_id                 INTEGER,              -- natural key (links to crm_party_identity)
  value_group                 TEXT,                 -- VIP|GOLD|SILVER|BRONZE
  customer_status             TEXT,                 -- active|at_risk|churned
  next_purchase_signal        TEXT,                 -- OVERDUE|DUE_SOON|ON_TRACK
  predicted_next_purchase_date TEXT,
  avg_days_between_orders     REAL,
  avg_order_spend             REAL,
  discount_sensitivity        TEXT,                 -- HIGH|MEDIUM|LOW
  cancel_rate                 REAL,
  last_purchased_sku          TEXT,
  top_affinity_product        TEXT,
  second_affinity_product     TEXT,
  channel_preference          TEXT,
  lifetime_contribution_margin REAL,
  is_margin_negative          INTEGER,              -- 0/1 (SQLite bool)
  -- Discount bucket metrics (4 buckets × 2 metrics; 0.0–1.0; NULL = customer never had this type)
  last_line_discount_rate       REAL,
  max_line_discount_rate        REAL,
  last_voucher_discount_rate    REAL,
  max_voucher_discount_rate     REAL,
  last_campaign_discount_rate   REAL,
  max_campaign_discount_rate    REAL,
  last_negotiated_discount_rate REAL,
  max_negotiated_discount_rate  REAL,
  refreshed_at                TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS wh_product_insight (
  product_key         TEXT    PRIMARY KEY,
  sku                 TEXT,
  abc_class           TEXT,   -- A|B|C
  health_class        TEXT,   -- STAR|CASH_COW|QUESTION|DOG
  lifecycle_stage     TEXT,
  velocity_momentum   TEXT,
  oos_risk            TEXT,   -- HIGH|MEDIUM|LOW
  realized_margin_pct REAL,   -- use realized_margin_pct, NOT gross_margin_pct (H010 bug)
  discount_dependency TEXT,
  refreshed_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS wh_action_queue (
  action_id         TEXT    PRIMARY KEY,  -- md5(customer_key|action_type|pending_since); stable per episode
  customer_key      TEXT,
  action_type       TEXT,                 -- CALL_NOW|REORDER_NUDGE|WIN_BACK|UPSELL|CROSS_SELL|COLLECT_FEEDBACK
  rationale_vi      TEXT,                 -- human-readable Vietnamese rationale
  value_at_stake_vnd INTEGER,             -- VND
  priority          INTEGER,
  pending_since          TEXT,            -- YYYY-MM-DD; first day this episode appeared (never updated)
  generated_date         TEXT,            -- YYYY-MM-DD; last warehouse refresh (updated daily)
  top_affinity_product   TEXT,            -- product customer buys most (display + search)
  last_purchased_product TEXT,            -- product from customer's last order (display + search)
  refreshed_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  -- status/snoozed_until live in crm.db:crm_action_state (keyed on action_id)
);

-- ─── GROUP 3: Source relational data (Sapo → warehouse; CRM does NOT recompute) ─

CREATE TABLE IF NOT EXISTS wh_customer_base (
  customer_key    TEXT    PRIMARY KEY,
  customer_id     INTEGER,               -- value-link to crm_party_identity
  customer_code   TEXT,
  display_name    TEXT,
  phone           TEXT,
  email           TEXT,
  customer_group  TEXT,
  first_order_date TEXT,                 -- YYYY-MM-DD
  refreshed_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS wh_product (
  product_key  TEXT    PRIMARY KEY,
  sku          TEXT,
  variant_id   INTEGER,
  product_name TEXT,
  brand        TEXT,
  unit_price   INTEGER,                  -- VND INTEGER
  is_active    INTEGER,                  -- 0/1
  refreshed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS wh_order_hdr (
  order_id     TEXT    PRIMARY KEY,
  order_code   TEXT,
  customer_id  INTEGER,                  -- value-link to crm_party_identity
  date_key     INTEGER,                  -- ICT YYYYMMDD (pass-through from warehouse; do NOT recompute)
  net_revenue  INTEGER,                  -- VND INTEGER (VAT-inclusive, matches warehouse convention)
  status       TEXT,
  channel      TEXT,
  item_count   INTEGER,
  refreshed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- ─── GROUP 2 (cont): Strategic tier — NBA resell engine ──────────────────────

CREATE TABLE IF NOT EXISTS wh_customer_tier (
  customer_key              TEXT    PRIMARY KEY,   -- MD5 surrogate from warehouse
  customer_id               INTEGER,               -- natural key (links to crm_party_identity)
  customer_code             TEXT,
  full_name                 TEXT,
  customer_type             TEXT,
  value_group               TEXT,
  customer_status           TEXT,
  order_count               INTEGER,
  recency_days              INTEGER,
  last_order_date           TEXT,                  -- YYYY-MM-DD
  lifetime_value            INTEGER,               -- VND INTEGER
  lifetime_contribution_margin INTEGER,            -- VND INTEGER
  channel_preference        TEXT,
  is_contactable            INTEGER,               -- 0/1
  source_contact_quality    TEXT,
  contact_quality           TEXT,
  strategic_tier            TEXT,                  -- LIVE_CORE|SECOND_ORDER|DORMANT_VALUABLE|LAPSED_VALUABLE|MASKED_REPEAT|NONBUYER|GRAVEYARD
  tier_reason               TEXT,
  tier_generated_at         TEXT,                  -- ISO-8601 ICT
  refreshed_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- ─── PLUMBING ─────────────────────────────────────────────────────────────────

-- wh_party_seed: one-way channel so Go creates crm_party / crm_party_identity
-- without Python ever touching crm.db (1-writer rule).
-- Quality fields are warehouse-computed and written once (first-write wins on conflict).
CREATE TABLE IF NOT EXISTS wh_party_seed (
  customer_id           INTEGER PRIMARY KEY,  -- Sapo customer_id (natural key)
  customer_key          TEXT,                 -- MD5 surrogate from warehouse
  seen_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  source_contact_quality TEXT NOT NULL DEFAULT 'real',  -- masked|real, immutable
  contact_quality        TEXT NOT NULL DEFAULT 'real'   -- masked|unverified|verified, initial value
);

-- wh_sync_run: audit log for every ETL run (one row per source table per run).
CREATE TABLE IF NOT EXISTS wh_sync_run (
  run_id       TEXT PRIMARY KEY,         -- UUID generated by Python
  source_table TEXT NOT NULL,
  row_count    INTEGER,
  status       TEXT,                     -- ok|failed
  started_at   TEXT,
  finished_at  TEXT,
  error        TEXT
);

-- ─── Dead-stock targeting engine (PLAN-004) ──────────────────────────────────
-- One row per (product_key × customer_key) — mirrors mart_deadstock_target_queue grain.
-- Tracked independently from wh_action_queue (NBA customer-state queue).
-- PII: full_name, customer_key → keep in cache.db only (never export to git).

CREATE TABLE IF NOT EXISTS wh_deadstock_target (
  product_key               TEXT    NOT NULL,  -- SKU surrogate (own-brand FJV slow/dead)
  customer_key              TEXT    NOT NULL,  -- Customer MD5 surrogate
  sku                       TEXT,
  product_name              TEXT,
  category                  TEXT,
  brand_code                TEXT,
  health_class              TEXT,              -- DOG|QUESTION|BALANCED (dead_stock=TRUE)
  is_dead_stock             INTEGER,           -- 0/1
  dead_stock_value_at_risk  INTEGER,           -- VND
  stock_value_at_mac        INTEGER,           -- VND
  days_since_last_sale      INTEGER,
  full_name                 TEXT,              -- PII — cache.db only
  strategic_tier            TEXT,              -- LIVE_CORE|SECOND_ORDER|DORMANT_VALUABLE|LAPSED_VALUABLE|MASKED_REPEAT
  source_contact_quality    TEXT,              -- real|masked
  next_purchase_signal      TEXT,              -- OVERDUE|DUE_SOON|ON_TRACK|NULL
  predicted_next_purchase_date TEXT,           -- YYYY-MM-DD or NULL
  discount_sensitivity      TEXT,              -- PROMO_DEPENDENT|PROMO_MIXED|FULL_PRICE|NULL
  value_group               TEXT,
  lifetime_value            INTEGER,           -- VND
  recency_days              INTEGER,
  order_count               INTEGER,
  buyer_sku_qty             INTEGER,           -- units bought of this SKU historically
  buyer_sku_last_date       TEXT,              -- YYYYMMDD date_key of last purchase of this SKU
  route_channel             TEXT    NOT NULL,  -- HUG|SHOPEE_NATIVE
  voucher_eligible          INTEGER NOT NULL,  -- 0/1; FALSE for FULL_PRICE buyers
  is_holdout                INTEGER NOT NULL,  -- 0/1; ~20% deterministic holdout for measurement
  target_rank               INTEGER,           -- rank within SKU (1 = highest priority)
  reason_fragment           TEXT,              -- human-readable Vietnamese context
  queue_generated_at        TEXT,              -- ISO-8601 ICT
  refreshed_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  PRIMARY KEY (product_key, customer_key)
);

-- ─── SKU-level action queue (product-aware regimen reminders) ────────────────
-- Grain: (customer_key, sku, action_type) — one row per customer per core SKU per signal type.
-- Companion to wh_action_queue (customer-level behavioral NBA).
-- action_id = md5(customer_key|sku|action_type|pending_since) — stable per episode.
-- 5 signal types: USAGE_FOLLOWUP, PROGRESS_CHECK, REORDER_PREEMPT, REORDER_NUDGE, REORDER_OVERDUE.

CREATE TABLE IF NOT EXISTS wh_sku_action_queue (
  action_id                TEXT    PRIMARY KEY,  -- md5(customer_key|sku|action_type|pending_since)
  customer_key             TEXT,
  sku                      TEXT,                 -- Fine Japan core SKU (e.g. VCSC20001L001)
  product_display_name     TEXT,                 -- human-readable product name (e.g. 'Cordyceps')
  action_type              TEXT,                 -- USAGE_FOLLOWUP|PROGRESS_CHECK|REORDER_PREEMPT|REORDER_NUDGE|REORDER_OVERDUE
  rationale_vi             TEXT,                 -- Vietnamese rationale string (product name + context embedded)
  days_until_depletion     INTEGER,              -- days until supply runs out (<0 = overdue)
  estimated_depletion_date TEXT,                 -- YYYY-MM-DD
  priority                 INTEGER,
  pending_since            TEXT,                 -- first day this episode appeared (never updated)
  generated_date           TEXT,                 -- last warehouse refresh date
  refreshed_at             TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
  -- status/snoozed_until live in crm.db:crm_action_state (keyed on action_id, same mechanism)
);

-- ─── INDEXES ─────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_wh_customer_insight_customer_id  ON wh_customer_insight (customer_id);
-- Enforce one active row per (customer_key, action_type) — required by upsert_action_queue ON CONFLICT.
CREATE UNIQUE INDEX IF NOT EXISTS uidx_wh_action_queue_customer_type ON wh_action_queue (customer_key, action_type);
CREATE INDEX IF NOT EXISTS idx_wh_action_queue_customer_key_pri  ON wh_action_queue (customer_key, priority);
CREATE INDEX IF NOT EXISTS idx_wh_customer_base_customer_id      ON wh_customer_base (customer_id);
CREATE INDEX IF NOT EXISTS idx_wh_product_sku                    ON wh_product (sku);
CREATE INDEX IF NOT EXISTS idx_wh_order_hdr_customer_date        ON wh_order_hdr (customer_id, date_key);
CREATE INDEX IF NOT EXISTS idx_wh_customer_tier_customer_id      ON wh_customer_tier (customer_id);
CREATE INDEX IF NOT EXISTS idx_wh_customer_tier_strategic_tier   ON wh_customer_tier (strategic_tier);
CREATE INDEX IF NOT EXISTS idx_wh_deadstock_target_route_holdout ON wh_deadstock_target (route_channel, is_holdout);
CREATE INDEX IF NOT EXISTS idx_wh_deadstock_target_customer_key  ON wh_deadstock_target (customer_key);
CREATE UNIQUE INDEX IF NOT EXISTS uidx_wh_sku_action_queue_key ON wh_sku_action_queue (customer_key, sku, action_type);
CREATE INDEX IF NOT EXISTS idx_wh_sku_action_queue_customer ON wh_sku_action_queue (customer_key, priority);

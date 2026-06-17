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
  pending_since     TEXT,                 -- YYYY-MM-DD; first day this episode appeared (never updated)
  generated_date    TEXT,                 -- YYYY-MM-DD; last warehouse refresh (updated daily)
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

-- ─── INDEXES ─────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_wh_customer_insight_customer_id  ON wh_customer_insight (customer_id);
CREATE INDEX IF NOT EXISTS idx_wh_action_queue_customer_key_pri  ON wh_action_queue (customer_key, priority);
CREATE INDEX IF NOT EXISTS idx_wh_customer_base_customer_id      ON wh_customer_base (customer_id);
CREATE INDEX IF NOT EXISTS idx_wh_product_sku                    ON wh_product (sku);
CREATE INDEX IF NOT EXISTS idx_wh_order_hdr_customer_date        ON wh_order_hdr (customer_id, date_key);

-- Migration 0009 UP: platform-independent external identity registry
-- Decouples crm_party from any specific sales platform (Sapo, WooCommerce, Shopify, etc.)
-- Anti-corruption layer: CRM uses party_id internally; platform IDs live here as lookup keys only

CREATE TABLE IF NOT EXISTS crm_party_external_id (
  ext_id        TEXT PRIMARY KEY,
  party_id      TEXT NOT NULL REFERENCES crm_party(party_id),
  source_system TEXT NOT NULL,   -- sapo | woocommerce | shopify | tiki | shopee
  external_key  TEXT NOT NULL,   -- customer_id or equivalent in that platform
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE (source_system, external_key)
);

CREATE INDEX IF NOT EXISTS idx_party_ext_id_party
  ON crm_party_external_id (party_id);

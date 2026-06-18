-- Drop old trigger-maintained FTS (replaced by rebuild-based unified FTS)
DROP TRIGGER IF EXISTS trg_party_fts_insert;
DROP TRIGGER IF EXISTS trg_party_fts_update;
DROP TRIGGER IF EXISTS trg_party_fts_delete;
DROP TABLE IF EXISTS crm_party_fts;

-- Unified search index: one row per party, token blob covers all searchable values
-- Tokenizer: unicode61 with diacritic removal (Vietnamese names) + tokenchars for
-- special chars in emails, order codes
CREATE VIRTUAL TABLE IF NOT EXISTS crm_party_search USING fts5(
    party_id  UNINDEXED,
    tokens,
    tokenize = "unicode61 remove_diacritics 2 tokenchars '@.'"
);

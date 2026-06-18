-- Migration 0018 UP: rename source_system 'sapo' → 'sapo_v2' in identity tables
-- Reason: source_system is a combined {system}_{version} identifier; bare 'sapo' is invalid.

UPDATE crm_party_identity
SET source_system = 'sapo_v2'
WHERE source_system = 'sapo';

UPDATE crm_party_external_id
SET source_system = 'sapo_v2'
WHERE source_system = 'sapo';

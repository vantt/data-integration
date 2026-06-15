-- Migration 0006 UP: add contact quality fields to crm_party_identity
ALTER TABLE crm_party_identity ADD COLUMN source_contact_quality TEXT NOT NULL DEFAULT 'real';
ALTER TABLE crm_party_identity ADD COLUMN contact_quality TEXT NOT NULL DEFAULT 'real';

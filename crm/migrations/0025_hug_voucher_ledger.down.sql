-- Migration 0025 DOWN: remove crm_hug_voucher and its attribution view
-- Safe: no other table holds FK references to crm_hug_voucher.
DROP VIEW  IF EXISTS v_hug_voucher_attribution;
DROP INDEX IF EXISTS idx_crm_hug_voucher_unmatched;
DROP INDEX IF EXISTS idx_crm_hug_voucher_token;
DROP INDEX IF EXISTS idx_crm_hug_voucher_customer;
DROP INDEX IF EXISTS idx_crm_hug_voucher_campaign;
DROP TABLE IF EXISTS crm_hug_voucher;

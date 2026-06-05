-- =================================================================================================
-- SINGULAR TEST: PROMO ACCOUNT NOT IN KEEP POOL
-- =================================================================================================
-- Invariant: any account tagged `drop_promo_count_once` must NEVER appear with a `keep_*`
-- treatment in stg_overhead_account_classification.
--
-- A promo account in a keep_* pool would cause double-counting: promo cost flows once
-- via COGS (Sapo-MAC revenue=0 gift lines), so it must not also enter the overhead pool.
--
-- Returns offending (account, treatment, pool_id) rows — test FAILS if any rows returned.
-- =================================================================================================

SELECT
    account,
    treatment,
    pool_id
FROM {{ ref('stg_overhead_account_classification') }}
WHERE treatment LIKE 'keep_%'
  AND account IN (
      SELECT account
      FROM {{ ref('stg_overhead_account_classification') }}
      WHERE treatment = 'drop_promo_count_once'
  )

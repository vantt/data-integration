{{ config(severity='warn') }}

-- =================================================================================================
-- SINGULAR TEST: OVERHEAD ACCOUNTS CLASSIFIED (WARN)
-- =================================================================================================
-- Severity: WARN — a new unclassified MISA account should alert the team but NOT break
-- the pipeline. The account will simply be excluded from all overhead pools until it is
-- added to the classification gsheet.
--
-- Logic: find MISA accounts that appear in std_misa_account_ledger but have NO matching
-- row in stg_overhead_account_classification for ANY period (effective-date-agnostic —
-- if the account has never been classified at all, it surfaces here).
--
-- Returns unclassified (account, account_group) rows — test WARNS if any rows returned.
-- =================================================================================================

SELECT DISTINCT
    m.account,
    m.account_group
FROM {{ ref('std_misa_account_ledger') }} m
WHERE NOT EXISTS (
    SELECT 1
    FROM {{ ref('stg_overhead_account_classification') }} c
    WHERE c.account = m.account
)
ORDER BY m.account_group, m.account

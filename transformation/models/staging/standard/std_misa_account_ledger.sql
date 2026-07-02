{{ config(
    materialized='view',
    tags=['standard', 'misa']
) }}

-- =================================================================================================
-- STD: MISA ACCOUNT LEDGER
-- =================================================================================================
-- Source:  src_misa_account_ledger
-- Grain:   1 row per (account, period_month) — monthly rollup per leaf account
-- PK:      (account, period_month) — natural key; idempotent last-write-wins on re-export
--
-- Wide model: contains ALL downloaded account prefixes (6421*, 6422*, and future cashflow
-- accounts 111*, 131*, 331*, etc.). No filtering here — each downstream intermediate model
-- selects the accounts relevant to its domain (overhead, cashflow, revenue, etc.).
--
-- Net cost rule (§5 design doc):
--   net_cost = debit − credit_excl_911
--   credit_excl_911 excludes offset_account='911' (kết chuyển cuối kỳ).
--   Rationale: 642 is a cost account (Nợ = expense incurred; Có = rebate reversal OR year-end
--   transfer to 911 for P&L closing). Blindly subtracting Có when 911 is present yields net≈0.
--   The 911 exclusion isolates genuine cost reductions (hoàn nhập) while ignoring the closing entry.
-- =================================================================================================

SELECT
    -- Grain dimensions
    account,
    account_group,
    DATE_TRUNC('month', posting_date::DATE)     AS period_month,

    -- Rollup aggregates
    SUM(debit)                                  AS debit,
    SUM(
        CASE WHEN offset_account <> '911'
             THEN credit
             ELSE 0
        END
    )                                           AS credit_excl_911,

    -- Net overhead cost: Nợ − Có(excluding kết chuyển 911)
    SUM(debit) - SUM(
        CASE WHEN offset_account <> '911'
             THEN credit
             ELSE 0
        END
    )                                           AS net_cost,

    -- Line count for audit / anomaly detection
    COUNT(*)                                    AS line_count,

    -- Provenance
    'misa'                  AS source_system,
    'account_ledger_v1'     AS source_version

FROM {{ ref('src_misa_account_ledger') }}
GROUP BY account, account_group, DATE_TRUNC('month', posting_date::DATE)

{{ config(
    tags=['mart', 'fact', 'misa', 'finance'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- FACT: CASH MOVEMENT (operational cashflow, direct method)
-- =================================================================================================
-- Grain: 1 row per journal line hitting a cash/bank account (111x / 112x).
-- Source: src_misa_account_ledger (full-ledger export; cash accounts filtered here).
--
-- Direction (cash account is an asset, normal debit side):
--   debit  > 0  → tiền VÀO  (inflow)   e.g. Nợ 112 / Có 131 = thu tiền khách
--   credit > 0  → tiền RA    (outflow)  e.g. Có 112 / Nợ 334 = chi lương
--
-- is_internal_transfer: counterpart is itself a cash account (111x/112x) → a move between our
--   own cash accounts, NOT real external cash flow. Kept for traceability but must be excluded
--   (net to zero) when measuring true thu/chi. Downstream/report filters WHERE NOT is_internal_transfer.
--
-- running_balance: per-line closing balance straight from MISA (col 'Dư Nợ' − 'Dư Có');
--   authoritative — do not recompute. opening_balance = period-opening anchor per account.
-- =================================================================================================

WITH cash_lines AS (
    SELECT
        l.posting_date,
        DATE_TRUNC('month', l.posting_date::DATE)   AS period_month,
        l.account                                   AS cash_account,
        l.offset_account,
        l.voucher_no,
        l.description,
        l.debit,
        l.credit,
        l.debit_balance,
        l.credit_balance,
        l.opening_balance,
        (l.debit_balance - l.credit_balance)        AS running_balance,
        (l.debit - l.credit)                        AS signed_amount,   -- +inflow / −outflow
        CASE WHEN l.debit > 0 THEN 'inflow' ELSE 'outflow' END AS direction,
        CASE WHEN l.debit > 0 THEN l.debit ELSE l.credit END  AS amount,
        (l.offset_account LIKE '111%' OR l.offset_account LIKE '112%') AS is_internal_transfer
    FROM {{ ref('src_misa_account_ledger') }} l
    WHERE (l.account LIKE '111%' OR l.account LIKE '112%')
      AND COALESCE(l.debit, 0) + COALESCE(l.credit, 0) > 0   -- drop zero-movement rows
)

SELECT
    c.posting_date,
    c.period_month,
    c.cash_account,
    ca.account_name                     AS cash_account_name,
    c.offset_account,
    off.account_name                    AS offset_account_name,
    off.cashflow_line,
    c.direction,
    c.is_internal_transfer,
    CAST(c.amount AS BIGINT)             AS amount,
    CAST(c.signed_amount AS BIGINT)      AS signed_amount,
    CAST(c.running_balance AS BIGINT)    AS running_balance,
    CAST(c.opening_balance AS BIGINT)    AS opening_balance,
    c.voucher_no,
    c.description,
    'misa'  AS source_system
FROM cash_lines c
LEFT JOIN {{ ref('dim_gl_account') }} ca  ON ca.account_code = c.cash_account
LEFT JOIN {{ ref('dim_gl_account') }} off ON off.account_code = c.offset_account

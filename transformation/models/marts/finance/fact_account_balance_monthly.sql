{{ config(
    tags=['mart', 'fact', 'misa', 'finance'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- FACT: ACCOUNT BALANCE MONTHLY
-- =================================================================================================
-- Grain: (account_code, period_month) — 1 row per account × calendar month.
-- Purpose: opening + Σdebit + Σcredit + closing for ALL accounts in the ledger. Foundation for
--   số dư quỹ (cash balance), balance-sheet, and P&L reporting.
--
-- Balances (authoritative, from MISA — do NOT recompute):
--   opening_balance = "Số dư đầu kỳ" row (parser forward-fills to all detail rows; MAX is safe).
--   closing_balance = running balance (Dư Nợ − Dư Có) of the LAST journal line in the period.
--
-- Known gap: accounts with an opening balance but ZERO movement in a period emit no ledger rows
--   → absent here for that period (e.g. 11219). A calendar date-spine + carry-forward would close
--   this; deferred. Cash accounts of interest generally have monthly activity.
--
-- Note: pre-full-ledger partitions (642-only, before the parser balance-column enhancement) have
--   opening_balance/debit_balance = NULL. Filter WHERE opening_balance IS NOT NULL for clean data.
-- =================================================================================================

WITH raw AS (
    SELECT
        account,
        DATE_TRUNC('month', posting_date::DATE)         AS period_month,
        debit,
        credit,
        (debit_balance - credit_balance)                AS running_balance,
        opening_balance,
        ROW_NUMBER() OVER (
            PARTITION BY account, DATE_TRUNC('month', posting_date::DATE)
            ORDER BY posting_date DESC, voucher_no DESC
        )                                               AS rn_last
    FROM {{ ref('src_misa_account_ledger') }}
    WHERE posting_date IS NOT NULL
),

movements AS (
    SELECT
        account                                         AS account_code,
        period_month,
        SUM(debit)                                      AS period_debit,
        SUM(credit)                                     AS period_credit,
        COUNT(*)                                        AS line_count
    FROM raw
    GROUP BY account, period_month
),

opening AS (
    SELECT
        account                                         AS account_code,
        period_month,
        MAX(opening_balance)                            AS opening_balance
    FROM raw
    WHERE opening_balance IS NOT NULL
    GROUP BY account, period_month
),

closing AS (
    SELECT
        account                                         AS account_code,
        period_month,
        running_balance                                 AS closing_balance
    FROM raw
    WHERE rn_last = 1
)

SELECT
    m.account_code,
    a.account_name,
    a.account_class,
    a.is_cash,
    m.period_month,
    o.opening_balance,
    m.period_debit,
    m.period_credit,
    c.closing_balance,
    m.line_count,
    'misa'  AS source_system
FROM movements m
LEFT JOIN opening  o ON o.account_code = m.account_code AND o.period_month = m.period_month
LEFT JOIN closing  c ON c.account_code = m.account_code AND c.period_month = m.period_month
LEFT JOIN {{ ref('dim_gl_account') }} a ON a.account_code = m.account_code

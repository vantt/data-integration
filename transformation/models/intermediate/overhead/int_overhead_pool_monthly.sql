{{ config(
    tags=['int', 'overhead'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- INT: OVERHEAD POOL MONTHLY
-- =================================================================================================
-- Grain:   (pool_id, period_month) — one row per overhead pool × calendar month
-- Purpose: Aggregate MISA account-ledger cost into named overhead pools, using the
--          classification gsheet to decide which accounts are pooled and by what base metric.
--
-- Pool definition:
--   pool_net  = Σ net_cost for ALL accounts in the pool with treatment LIKE 'keep_%'.
--   drop_*    accounts are excluded — they are either directly traceable costs
--              (drop_traceable) or promotion-goods counted once globally (drop_promo_count_once).
--   base_metric drives the allocation denominator in the next model:
--              'net_revenue'  → allocate ∝ order net revenue
--              'order_count'  → allocate ∝ 1 per order (equal share)
--              'gross_profit' → allocate ∝ order gross profit
--
-- Effective-dating: the classification gsheet is SCD2 — each classification row is valid
--   during [effective_from, effective_to] (effective_to IS NULL = open-ended / currently active).
--   A single MISA account may change pool_id or treatment over time; we match each
--   ledger period_month to the classification row active in that month.
-- =================================================================================================

WITH ledger AS (
    SELECT
        account,
        account_group,
        period_month,
        net_cost
    FROM {{ ref('std_misa_account_ledger') }}
),

classification AS (
    SELECT
        account,
        treatment,
        pool_id,
        base_metric,
        effective_from,
        effective_to
    FROM {{ ref('stg_overhead_account_classification') }}
    -- Only keep_* treatments enter the allocation pool; drop_* are excluded at this stage
    WHERE treatment LIKE 'keep_%'
),

-- Effective-dated join: each ledger month joined to the classification row active in that month.
-- A single account may have multiple classification rows in SCD2 — the date predicate ensures
-- exactly one matching row per (account, period_month) as long as ranges don't overlap.
-- Overlapping ranges in the source sheet would cause double-counting here (a data quality issue
-- caught by assert_overhead_accounts_classified, not suppressed here — fail loudly).
ledger_classified AS (
    SELECT
        m.account,
        m.account_group,
        m.period_month,
        m.net_cost,
        c.pool_id,
        c.base_metric
    FROM ledger m
    INNER JOIN classification c
        ON  m.account = c.account
        AND m.period_month >= c.effective_from
        AND (c.effective_to IS NULL OR m.period_month <= c.effective_to)
)

SELECT
    pool_id,
    base_metric,
    period_month,

    -- Pool total: sum of all keep_* net_cost for this pool × month.
    -- net_cost = Nợ − Có(excl-911); see std_misa_account_ledger for the 911-exclusion rationale.
    -- pool_net can theoretically be negative (e.g. if credit reversals dominate a month).
    SUM(net_cost)                   AS pool_net,

    COUNT(DISTINCT account)         AS n_accounts

FROM ledger_classified
GROUP BY pool_id, base_metric, period_month

{{ config(
    tags=['mart', 'dim', 'misa'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- DIM: GL ACCOUNT (MISA chart of accounts)
-- =================================================================================================
-- Grain: 1 row per distinct account_code seen in the ledger (as posting account OR counterpart).
-- Self-populating from src_misa_account_ledger so new accounts appear automatically;
-- ref_gl_accounts.csv only enriches names (code falls back when absent).
--
-- cashflow_line groups counterpart accounts into human-readable cash in/out lines — legacy
-- bucket grain, kept for one_off/reserve pseudo-lines and multi-parent buckets (e.g. "Doanh
-- thu & thu nhập" spans 511+515+71, no single real parent represents it).
--
-- parent_account_code/parent_account_name: nearest REAL named ancestor (walks prefixes from
-- longest to shortest, floor length 3) — used by the budget sheet to offer a "cha" rollup
-- option per account family. NOT a fixed 3-digit truncation: 642172 (Chi phí bán hàng) and
-- 642273/642282 (Chi phí quản lý DN) all start with "642" but split into 2 different real
-- parents (6421 vs 6422) at digit 4 — LEFT(code,3) would wrongly merge them. See
-- plans/260709-1415-budget-account-level-remap/phase-01-account-taxonomy-and-join.md.
--
-- is_cash flags real cash/bank accounts (111/112) used to filter fact_cash_movement.
-- =================================================================================================

WITH account_universe AS (
    -- Every code that appears as a posting account or a counterpart
    SELECT account AS account_code FROM {{ ref('src_misa_account_ledger') }} WHERE account IS NOT NULL
    UNION
    SELECT offset_account AS account_code FROM {{ ref('src_misa_account_ledger') }} WHERE offset_account IS NOT NULL
),

distinct_accounts AS (
    SELECT DISTINCT account_code FROM account_universe
),

names AS (
    SELECT account_code, account_name FROM {{ ref('ref_gl_accounts') }}
),

ancestor_candidates AS (
    SELECT
        d.account_code,
        n2.account_code AS candidate_code,
        n2.account_name AS candidate_name
    FROM distinct_accounts d
    JOIN names n2
      ON  n2.account_code != d.account_code
      AND d.account_code LIKE n2.account_code || '%'
      AND LENGTH(n2.account_code) >= 3
),

nearest_ancestor AS (
    SELECT account_code, candidate_code, candidate_name
    FROM (
        SELECT
            account_code, candidate_code, candidate_name,
            ROW_NUMBER() OVER (PARTITION BY account_code ORDER BY LENGTH(candidate_code) DESC) AS rn
        FROM ancestor_candidates
    )
    WHERE rn = 1
)

SELECT
    a.account_code,
    COALESCE(n.account_name, 'TK ' || a.account_code)   AS account_name,
    LEFT(a.account_code, 1)                             AS account_class,
    pa.candidate_code                                   AS parent_account_code,
    pa.candidate_name                                   AS parent_account_name,

    -- Real cash/bank accounts drive the cashflow report
    (a.account_code LIKE '111%' OR a.account_code LIKE '112%') AS is_cash,

    -- Operational cashflow line — classify a counterpart account into a thu/chi bucket
    CASE
        WHEN a.account_code LIKE '111%' OR a.account_code LIKE '112%' THEN 'Chuyển nội bộ tiền'
        WHEN a.account_code LIKE '131%'                               THEN 'Bán hàng & phải thu KH'
        WHEN a.account_code LIKE '331%'                               THEN 'Thanh toán nhà cung cấp'
        WHEN a.account_code LIKE '334%'                               THEN 'Chi lương'
        WHEN a.account_code LIKE '335%' OR a.account_code LIKE '336%'
          OR a.account_code LIKE '338%'                              THEN 'Phải trả khác & bảo hiểm'
        WHEN a.account_code LIKE '133%' OR a.account_code LIKE '333%' THEN 'Thuế'
        WHEN a.account_code LIKE '141%'                               THEN 'Tạm ứng'
        WHEN a.account_code LIKE '15%'                                THEN 'Hàng tồn kho'
        WHEN a.account_code LIKE '21%' OR a.account_code LIKE '24%'   THEN 'Đầu tư TSCĐ'
        WHEN a.account_code LIKE '34%' OR a.account_code LIKE '41%'   THEN 'Vay & vốn chủ sở hữu'
        WHEN a.account_code LIKE '511%' OR a.account_code LIKE '515%'
          OR a.account_code LIKE '71%'                               THEN 'Doanh thu & thu nhập'
        WHEN a.account_code LIKE '641%' OR a.account_code LIKE '642%' THEN 'Chi phí bán hàng & QLDN'
        WHEN a.account_code LIKE '81%'                                THEN 'Chi phí khác'
        WHEN a.account_code LIKE '136%' OR a.account_code LIKE '138%' THEN 'Phải thu/trả nội bộ khác'
        ELSE 'Khác'
    END                                                 AS cashflow_line,

    'misa'  AS source_system

FROM distinct_accounts a
LEFT JOIN names n ON n.account_code = a.account_code
LEFT JOIN nearest_ancestor pa ON pa.account_code = a.account_code

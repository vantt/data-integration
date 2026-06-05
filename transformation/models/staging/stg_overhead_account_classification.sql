{{ config(
    materialized='view',
    tags=['staging', 'overhead']
) }}

-- Overhead Account Classification — one row per MISA leaf sub-account.
-- Source sheet defines how each 6421/6422 sub-account is treated in the P&L:
--   keep_*           → pooled and allocated to channels via base_metric
--   drop_traceable   → excluded from pool (directly traceable cost)
--   drop_promo_count_once → promotion cost counted once, not per-channel
-- effective_to NULL = open-ended (currently active row).

WITH raw AS (
    SELECT * FROM {{ source('sapo_v2_raw', 'overhead_account_classification_raw') }}
),

cleaned AS (
    SELECT
        -- account is a MISA code (e.g. 64211, 642172) — keep as VARCHAR, never cast to int
        trim(cast(account        as varchar))       AS account,
        trim(cast(account_group  as varchar))       AS account_group,
        trim(cast(treatment      as varchar))       AS treatment,
        NULLIF(trim(cast(pool_id      as varchar)), '')   AS pool_id,
        NULLIF(trim(cast(base_metric  as varchar)), '')   AS base_metric,
        NULLIF(trim(cast(channel      as varchar)), '')   AS channel,
        TRY_CAST(effective_from as date)            AS effective_from,
        TRY_CAST(effective_to   as date)            AS effective_to,
        NULLIF(trim(cast(note         as varchar)), '')   AS note,
        cast(ingest_method       as varchar)        AS ingest_method

    FROM raw
    WHERE account IS NOT NULL
      AND trim(cast(account as varchar)) != ''
      AND treatment IS NOT NULL
)

SELECT
    account,
    account_group,
    treatment,
    pool_id,
    base_metric,
    channel,
    effective_from,
    effective_to,
    note,
    ingest_method
FROM cleaned

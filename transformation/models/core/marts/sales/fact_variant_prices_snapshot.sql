{{ config(
    tags=['mart', 'fact', 'products', 'prices'],
    location="{{ get_rolling_location() }}"
) }}

-- Materialization: default `external` parquet via get_rolling_location() — each
-- dbt run writes a timestamped parquet file; historical snapshots accumulate
-- naturally because the serving view UNIONs all parquets via glob pattern.

-- =================================================================================================
-- FACT: VARIANT PRICES SNAPSHOT (daily)
-- =================================================================================================
-- Grain: 1 row per (variant_id × price_list_id × snapshot_date).
-- Only non-zero prices stored — value=0 means "channel not configured for this SKU".
--
-- Incremental: appends today's snapshot. Never overwrites historical prices.
-- Run daily after Sapo product batch_sync completes.
--
-- Use cases:
--   1. Price change detection   — compare today vs yesterday for same (variant_id, price_list_id)
--   2. GIANHAP cost trend       — track import price over time (is_cost = true)
--   3. Channel margin baseline  — BANLE vs GIANHAP spread per variant
--   4. Pricing compliance       — flag is_below_cost = true for any non-cost price list
--
-- Caveats:
--   - snapshot_date = dbt run date (CURRENT_DATE), NOT the Sapo product modified_on timestamp.
--     Price changes within a day may be missed if dbt runs once/day.
--   - 17 price lists × ~682 variants × 365 days ≈ 4.2M rows/year — acceptable for parquet.
--   - GIANHAP (is_cost=true) is the only cost price list in Sapo. Usable as alternative COGS
--     proxy for the ~10% of SKUs without a MISA invoice match.
--   - implied_gross_margin_pct and is_below_cost are NULL when GIANHAP=0 (unset for that SKU).
--   - included_tax_price equals price_value when variant.tax_included=false (no VAT on top).
--     For taxable variants (8% VAT), included_tax_price = price_value * 1.08.
-- =================================================================================================

WITH prices AS (
    SELECT
        variant_id::BIGINT              AS variant_id,
        sku,
        product_id::BIGINT              AS product_id,
        price_list_id::BIGINT           AS price_list_id,
        price_list_code,
        price_list_name,
        is_cost_price                   AS is_cost,
        price_value::DECIMAL(18,2)      AS price_value,
        price_incl_tax::DECIMAL(18,2)   AS price_incl_tax,
        CURRENT_DATE                    AS snapshot_date
    FROM {{ ref('std_variant_prices') }}
    WHERE price_value IS NOT NULL
      AND price_value::DECIMAL(18,2) > 0   -- exclude unconfigured channels
),

-- Pivot GIANHAP cost onto every row to enable inline margin calcs
-- without a self-join at query time in downstream analysis.
gianhap AS (
    SELECT
        variant_id::BIGINT              AS variant_id,
        price_value::DECIMAL(18,2)      AS gianhap_cost
    FROM {{ ref('std_variant_prices') }}
    WHERE price_list_code = 'GIANHAP'
      AND price_value IS NOT NULL
      AND price_value::DECIMAL(18,2) > 0
)

SELECT
    p.variant_id,
    p.sku,
    p.product_id,
    p.price_list_id,
    p.price_list_code,
    p.price_list_name,
    p.is_cost,
    p.price_value,
    p.price_incl_tax,
    p.snapshot_date,

    -- GIANHAP cost denormalized for margin calcs (NULL when GIANHAP not set for SKU)
    g.gianhap_cost,

    -- Implied gross margin vs import cost; only meaningful for non-cost price lists
    CASE
        WHEN NOT p.is_cost AND g.gianhap_cost > 0
        THEN ROUND(
            (p.price_value - g.gianhap_cost) * 100.0 / NULLIF(p.price_value, 0),
            2
        )
        ELSE NULL
    END                                 AS implied_gross_margin_pct,

    -- Compliance flag: selling below Sapo import cost
    CASE
        WHEN NOT p.is_cost AND g.gianhap_cost > 0
        THEN p.price_value < g.gianhap_cost
        ELSE FALSE
    END                                 AS is_below_cost

FROM prices p
LEFT JOIN gianhap g ON p.variant_id = g.variant_id

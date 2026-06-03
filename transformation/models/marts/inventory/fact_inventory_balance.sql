{{ config(
    tags=['mart', 'fact', 'inventory'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- FACT: INVENTORY BALANCE (Sparse effective-dated stock-balance ledger)
-- =================================================================================================
-- Source:  std_inventory_movements (VIEW)
-- Grain:   1 row per (variant_id, location_id, movement-day) = that day's CLOSING stock balance
-- PK:      (variant_id, location_id, valid_from_date)
--
-- The natural counterpart to fact_inventory_movements: movements (in/out transactions) change the
-- balance, exactly like ledger entries vs. account balance. Materializes ONLY days where the
-- balance actually changed (~17.6k rows) and exposes an effective date range, so any point-in-time
-- query works WITHOUT storing every calendar day (a dense daily snapshot would be ~1.9M rows of
-- which 99.1% were redundant no-movement carry-forward):
--   - Current stock:    WHERE is_current                              (~1,494 pairs; 59 with onhand>0)
--   - Stock on date X:  WHERE X BETWEEN valid_from_date AND valid_to_date
--   - Trend over time:  step-line on (valid_from_date, onhand) per (variant, location)
--
-- Caveats (from analysis, plans/reports/analysis-260604-0001-inventory-v2-data-nature.md):
--   - onhand is authoritative (never recomputed); ~4.4% of pairs have unexplained jumps (Sapo-side
--     corrections without a log entry) — the closing balance is still the correct stock figure.
--   - Negative-balance pairs flagged via is_negative_onhand.
--   - Multiple movements on the same day: day-close = the movement with the latest issued_at.
-- =================================================================================================

WITH std AS (
    SELECT * FROM {{ ref('std_inventory_movements') }}
),

-- Day-closing balance per (variant, location, movement-day): latest movement of the day wins.
daily_close AS (
    SELECT
        variant_id,
        location_id,
        issued_date_key                              AS valid_from_date,
        MAX_BY(sku,             issued_at)           AS sku,
        MAX_BY(variant_name,    issued_at)           AS variant_name,
        MAX_BY(location_label,  issued_at)           AS location_label,
        MAX_BY(onhand,          issued_at)           AS onhand,
        MAX_BY(moving_avg_cost, issued_at)           AS moving_avg_cost,
        MAX_BY(inventory_value, issued_at)           AS inventory_value
    FROM std
    GROUP BY variant_id, location_id, issued_date_key
),

-- Effective range: this balance holds until the day before the next movement-day (open-ended for latest).
ranged AS (
    SELECT
        *,
        LEAD(valid_from_date) OVER (
            PARTITION BY variant_id, location_id
            ORDER BY valid_from_date
        ) AS next_from_date
    FROM daily_close
)

SELECT
    variant_id,
    sku,
    variant_name,
    location_id,
    location_label,
    valid_from_date,
    COALESCE(next_from_date - 1, DATE '9999-12-31')  AS valid_to_date,
    onhand,
    moving_avg_cost,
    inventory_value,
    (next_from_date IS NULL)                         AS is_current,
    (onhand < 0)                                     AS is_negative_onhand
FROM ranged
ORDER BY variant_id, location_id, valid_from_date DESC

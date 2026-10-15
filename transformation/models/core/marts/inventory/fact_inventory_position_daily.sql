{{ config(
    tags=['mart', 'fact', 'inventory', 'history'],
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- FACT: INVENTORY POSITION DAILY (stock position history from the nightly capture)
-- =================================================================================================
-- Grain: 1 row per (variant_id, location_id, as_of_date).
-- as_of_date: ICT day the capture stands for (macro history_as_of_date, var
--   history_day_cutoff_hour): the 03:01 nightly capture of D+1 records the end of day D.
--   Several captures for one day: the latest captured_at wins.
-- Values are what Sapo reported at captured_at: on_hand, available, committed, incoming, onway,
--   min/max thresholds, bin_location, wait_to_pack and the moving average cost (mac), all
--   source-provided. No stock value column (valuation belongs to the finance pack).
-- History starts with the first capture (15/10/2026); a missed night is a missing day. on_hand
--   before that: fact_inventory_balance (inventory ledger, since 2021).
-- Rebuilt in full from raw on every build. Ids are VARCHAR like int_sapo_inventories.
-- =================================================================================================

WITH captures AS (
    SELECT
        variant_id,
        product_id,
        sku,
        location_id,
        {{ history_as_of_date('captured_at') }} AS as_of_date,
        on_hand,
        available,
        committed,
        incoming,
        onway,
        min_value,
        max_value,
        mac,
        bin_location,
        wait_to_pack,
        captured_at,
        capture_run_id
    FROM {{ ref('std_inventory_position_captures') }}
    WHERE variant_id IS NOT NULL
      AND location_id IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY variant_id, location_id, {{ history_as_of_date('captured_at') }}
        ORDER BY captured_at DESC, capture_run_id DESC
    ) = 1
),

locations AS (
    SELECT
        CAST(branch_location_id AS VARCHAR)   AS location_id,
        branch_location_name,
        branch_location_code
    FROM {{ ref('dim_branch_location') }}
    WHERE branch_location_id IS NOT NULL
)

SELECT
    c.variant_id,
    c.location_id,
    c.as_of_date,
    c.product_id,
    c.sku,
    COALESCE(loc.branch_location_name, 'Unknown')  AS location_name,
    COALESCE(loc.branch_location_code, 'UNK')      AS location_code,
    c.on_hand,
    c.available,
    c.committed,
    c.incoming,
    c.onway,
    c.min_value,
    c.max_value,
    c.mac,
    c.bin_location,
    c.wait_to_pack,
    c.captured_at
FROM captures c
LEFT JOIN locations loc
    ON c.location_id = loc.location_id

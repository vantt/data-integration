{{ config(
    materialized='incremental',
    unique_key='fulfillment_id',
    incremental_strategy='delete+insert',
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO FULFILLMENTS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, modified_on + ingest_method priority).
--   3. Extract ALL scalar JSON fields + nested arrays/objects as text columns.
--   4. Business dedup by fulfillment_id (latest modified_on wins; compare new vs existing rows).
--   5. Discard payload → frees memory for downstream models.
--
-- Incremental strategy:
--   - Filters on _dlt_load_id (monotonically increasing) to catch late-arriving data.
--   - New extracted rows are UNIONed with existing rows for the same fulfillment_ids before
--     final dedup, so a later load never overwrites a more-recent record.
-- =================================================================================================

WITH
{% if is_incremental() %}
_cursor AS (
    SELECT COALESCE(MAX(_dlt_load_id), '') AS max_load_id FROM {{ this }}
),
{% endif %}
raw_data AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        _dlt_load_id,
        payload
    FROM {{ source('sapo_raw', 'fulfillment') }}
    {% if is_incremental() %}
    WHERE _dlt_load_id > (SELECT max_load_id FROM _cursor)
    {% endif %}
),

deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                try_cast(json_extract_string(payload, '$.modified_on') AS TIMESTAMPTZ) DESC NULLS LAST,
                CASE
                    WHEN ingest_method = 'webhook' THEN 3
                    WHEN ingest_method = 'history_log' THEN 2
                    ELSE 1
                END DESC
        ) AS rn
    FROM raw_data
),

-- Step 1: Tech dedup + JSON extraction (payload discarded after this CTE)
extracted AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        _dlt_load_id,

        -- IDs & codes
        json_extract_string(payload, '$.id')                                        AS fulfillment_id,
        json_extract_string(payload, '$.modified_on')                               AS modified_on,
        json_extract_string(payload, '$.code')                                      AS fulfillment_code,
        json_extract_string(payload, '$.order_id')                                  AS order_id,

        -- Statuses
        json_extract_string(payload, '$.status')                                    AS fulfillment_status,
        json_extract_string(payload, '$.composite_fulfillment_status')              AS composite_status,
        json_extract_string(payload, '$.payment_status')                            AS payment_status,
        json_extract_string(payload, '$.delivery_type')                             AS delivery_type,

        -- Foreign keys
        json_extract_string(payload, '$.stock_location_id')                         AS location_id,
        json_extract_string(payload, '$.account_id')                                AS account_id,
        json_extract_string(payload, '$.partner_id')                                AS partner_id,

        -- Financials
        try_cast(json_extract_string(payload, '$.total')            AS DECIMAL(18,2)) AS total_amount,
        try_cast(json_extract_string(payload, '$.total_tax')        AS DECIMAL(18,2)) AS total_tax,
        try_cast(json_extract_string(payload, '$.total_discount')   AS DECIMAL(18,2)) AS total_discount,
        try_cast(json_extract_string(payload, '$.total_quantity')   AS INTEGER)        AS total_quantity,

        -- Timestamps
        json_extract_string(payload, '$.packed_on')                                 AS packed_on,
        json_extract_string(payload, '$.shipped_on')                                AS shipped_on,
        json_extract_string(payload, '$.received_on')                               AS received_on,
        json_extract_string(payload, '$.cancel_date')                               AS cancelled_on,
        json_extract_string(payload, '$.created_on')                                AS created_on,

        -- Shipment fields
        json_extract_string(payload, '$.shipment.tracking_code')                    AS tracking_code,
        try_cast(json_extract_string(payload, '$.shipment.cod_amount')    AS DECIMAL(18,2)) AS cod_amount,
        try_cast(json_extract_string(payload, '$.shipment.freight_amount') AS DECIMAL(18,2)) AS freight_amount,
        json_extract_string(payload, '$.shipment.freight_payer')                    AS freight_payer,

        -- Nested JSON arrays/objects (as text for downstream models)
        json_extract_string(payload, '$.fulfillment_line_items')                    AS line_items_json,
        json_extract_string(payload, '$.shipping_address')                          AS shipping_address_json

    FROM deduped
    WHERE rn = 1
)

-- Step 2: Business dedup by fulfillment_id — compare new vs existing before overwriting
SELECT * FROM (
    SELECT * FROM extracted
    {% if is_incremental() %}
    UNION ALL
    SELECT existing.* FROM {{ this }} existing
    INNER JOIN (SELECT DISTINCT fulfillment_id FROM extracted) new_keys
        ON existing.fulfillment_id = new_keys.fulfillment_id
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY fulfillment_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method
            WHEN 'webhook' THEN 1
            WHEN 'history_log' THEN 2
            ELSE 3
        END
) = 1

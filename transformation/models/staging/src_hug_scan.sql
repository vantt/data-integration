{{ config(
    materialized='incremental',
    unique_key='entity_id',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    tags=['source', 'hug']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: HUG SCAN EVENTS
-- =================================================================================================
-- Purpose:
--   1. Read raw parquet from hug_raw/scan/ (dlt hug_webhook_consumer output).
--   2. Technical dedup by entity_id (= token — one row per most-recent ingest per token).
--   3. Extract scalar fields from inner payload; discard payload blob to keep memory low.
--
-- Grain: one row per token (latest event wins; a token may be re-scanned multiple times,
-- each scan is a new message, but we keep the freshest snapshot here).
-- Identity: entity_id = token (Hug events carry no numeric 'id' field).
-- =================================================================================================

{% set existing_cols = (adapter.get_columns_in_relation(this) | map(attribute='name') | list) if is_incremental() else [] %}

WITH
{% if is_incremental() %}
_cursor AS (
    {% if '_dlt_load_id' in existing_cols %}
    SELECT COALESCE(MAX(_dlt_load_id), '') AS max_load_id FROM {{ this }}
    {% else %}
    SELECT '' AS max_load_id
    {% endif %}
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
    FROM {{ source('hug_raw', 'scan') }}
    -- Exclude the empty-source sentinel (see ensure_hug_safety_placeholder.py).
    WHERE entity_id <> '_safety_placeholder'
    {% if is_incremental() %}
    AND _dlt_load_id > (SELECT max_load_id FROM _cursor)
    {% endif %}
),

deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                try_cast(event_timestamp AS TIMESTAMPTZ) DESC NULLS LAST
        ) AS rn
    FROM raw_data
),

extracted AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        _dlt_load_id,

        -- Hug scan payload fields (token-keyed; no numeric id)
        json_extract_string(payload, '$.token')         AS token,
        json_extract_string(payload, '$.customer_id')   AS customer_id,
        json_extract_string(payload, '$.op_type')       AS op_type,
        json_extract_string(payload, '$.channel')       AS channel,
        json_extract_string(payload, '$.campaign_id')   AS campaign_id,
        json_extract_string(payload, '$.tier')          AS tier,
        -- scanned_at is the edge-recorded timestamp (UTC ISO string from Worker)
        json_extract_string(payload, '$.scanned_at')    AS scanned_at_raw

    FROM deduped
    WHERE rn = 1
)

SELECT * FROM (
    SELECT * FROM extracted
    {% if is_incremental() and '_dlt_load_id' in existing_cols %}
    UNION ALL
    SELECT
        entity_id, entity_type, event_timestamp, ingest_method, _dlt_load_id,
        token, customer_id, op_type, channel, campaign_id, tier, scanned_at_raw
    FROM {{ this }}
    WHERE entity_id IN (SELECT DISTINCT entity_id FROM extracted)
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY try_cast(event_timestamp AS TIMESTAMPTZ) DESC NULLS LAST
) = 1

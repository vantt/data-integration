{{ config(
    materialized='incremental',
    unique_key='entity_id',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    tags=['source', 'hug']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: HUG OPT-IN EVENTS
-- =================================================================================================
-- Purpose:
--   1. Read raw parquet from hug_raw/optin_event/ (dlt hug_webhook_consumer output).
--   2. Technical dedup by entity_id (= token).
--   3. Extract scalar fields from inner payload; discard payload blob.
--
-- Grain: one row per token (latest opt-in event per token).
-- The landing page (built in a later task) POSTs to /webhook/hug/optin/created,
-- which the edge enqueues with entity_type='optin'. The consumer maps this to
-- table 'optin_event', so this source reads from hug_raw/optin_event/.
--
-- Payload contract:
--   token, buyer_customer_id, phone?, zalo_uid?, name?, consent{}, ts, campaign_id?
-- All nullable fields are extracted with COALESCE to empty string where downstream
-- logic requires non-null; consent is kept as raw JSON string for flexibility.
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
    FROM {{ source('hug_raw', 'optin_event') }}
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

        -- Opt-in payload fields; phone/zalo_uid/name are nullable by design
        json_extract_string(payload, '$.token')              AS token,
        json_extract_string(payload, '$.buyer_customer_id')  AS buyer_customer_id,
        json_extract_string(payload, '$.phone')              AS phone,
        json_extract_string(payload, '$.zalo_uid')           AS zalo_uid,
        json_extract_string(payload, '$.name')               AS name,
        -- consent is a nested object; keep as JSON string for identity bridge
        json_extract_string(payload, '$.consent')            AS consent_json,
        -- ts = opt-in timestamp as recorded by the landing page
        json_extract_string(payload, '$.ts')                 AS opted_in_at_raw,
        -- campaign attribution: set by landing page when ?hug_campaign= param is present
        json_extract_string(payload, '$.campaign_id')        AS campaign_id

    FROM deduped
    WHERE rn = 1
)

SELECT * FROM (
    SELECT * FROM extracted
    {% if is_incremental() and '_dlt_load_id' in existing_cols %}
    UNION ALL
    SELECT
        entity_id, entity_type, event_timestamp, ingest_method, _dlt_load_id,
        token, buyer_customer_id, phone, zalo_uid, name, consent_json, opted_in_at_raw,
        {% if 'campaign_id' in existing_cols %}campaign_id{% else %}NULL{% endif %} AS campaign_id
    FROM {{ this }}
    WHERE entity_id IN (SELECT DISTINCT entity_id FROM extracted)
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY entity_id
    ORDER BY try_cast(event_timestamp AS TIMESTAMPTZ) DESC NULLS LAST
) = 1

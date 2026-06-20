{{ config(
    materialized='view',
    tags=['staging', 'hug']
) }}

-- =================================================================================================
-- STAGING: HUG SCAN EVENTS
-- =================================================================================================
-- Purpose:
--   Cast timestamps to TIMESTAMPTZ (UTC) per project convention.
--   All dedup and JSON extraction already done in src_hug_scan.
--   No enrichment joins required at this layer — resolution happens downstream
--   in the identity bridge (I2-resolve, later task).
-- =================================================================================================

WITH src AS (
    SELECT * FROM {{ ref('src_hug_scan') }}
)

SELECT
    entity_id                                                   AS scan_token,
    token,
    customer_id,
    op_type,
    channel,
    campaign_id,
    tier,
    -- Cast edge-recorded timestamp to TIMESTAMPTZ; keep NULL if unparseable
    try_cast(scanned_at_raw AS TIMESTAMPTZ)                     AS scanned_at,
    try_cast(event_timestamp AS TIMESTAMPTZ)                    AS ingested_at,
    ingest_method,
    _dlt_load_id

FROM src

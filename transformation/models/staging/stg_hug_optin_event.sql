{{ config(
    materialized='view',
    tags=['staging', 'hug']
) }}

-- =================================================================================================
-- STAGING: HUG OPT-IN EVENTS
-- =================================================================================================
-- Purpose:
--   Cast timestamps to TIMESTAMPTZ (UTC) per project convention.
--   All dedup and JSON extraction already done in src_hug_optin_event.
--   Downstream identity resolution (I2-resolve) reads from this view to link
--   scanner phone/zalo_uid → buyer_customer_id → crm_identity_link.
-- =================================================================================================

WITH src AS (
    SELECT * FROM {{ ref('src_hug_optin_event') }}
)

SELECT
    entity_id                                               AS optin_token,
    token,
    buyer_customer_id,
    phone,
    zalo_uid,
    name,
    consent_json,
    -- opted_in_at: timestamp from landing page (UTC); fallback to ingest time
    COALESCE(
        try_cast(opted_in_at_raw AS TIMESTAMPTZ),
        try_cast(event_timestamp AS TIMESTAMPTZ)
    )                                                       AS opted_in_at,
    try_cast(event_timestamp AS TIMESTAMPTZ)                AS ingested_at,
    ingest_method,
    _dlt_load_id,
    -- campaign attribution (null for pre-campaign opt-ins)
    campaign_id

FROM src

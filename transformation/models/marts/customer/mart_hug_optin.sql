{{ config(
    materialized='table',
    tags=['mart', 'hug']
) }}

-- =================================================================================================
-- MART: HUG OPT-IN (latest opt-in state per token+phone pair)
-- =================================================================================================
-- Purpose:
--   Expose deduplicated opt-in events for the LOCAL identity resolver (I2-resolve).
--   Grain: one row per (token, phone) — latest opt-in wins when the same scanner
--   re-opts-in on the same token. NULL phone rows (Zalo-only) are kept 1:1 per token.
--
--   The resolver reads NEW rows since its last watermark (event_ts > last_processed_ts),
--   resolves identity, and writes crm_identity_link + updates crm_party_identity.
--
-- Columns match the stg_hug_optin_event fields the resolver needs.
-- buyer_customer_id, phone, zalo_uid, name are all nullable (§8 design).
-- =================================================================================================

WITH latest_per_pair AS (
    SELECT
        token,
        buyer_customer_id,
        phone,
        zalo_uid,
        name,
        consent_json,
        campaign_id,
        opted_in_at        AS event_ts,
        ingested_at,
        -- Dedup: for the same (token, phone) keep the most recent opt-in.
        -- NULL phone (Zalo-only) is kept once per token via ROW_NUMBER.
        ROW_NUMBER() OVER (
            PARTITION BY token, phone
            ORDER BY opted_in_at DESC NULLS LAST
        ) AS rn
    FROM {{ ref('stg_hug_optin_event') }}
    WHERE token IS NOT NULL
)

SELECT
    token,
    buyer_customer_id,
    phone,
    zalo_uid,
    name,
    consent_json,
    campaign_id,
    event_ts,
    ingested_at
FROM latest_per_pair
WHERE rn = 1

{{ config(
    materialized='incremental',
    unique_key='entity_id',
    incremental_strategy='delete+insert',
    tags=['staging', 'orders']
) }}

-- =================================================================================================
-- STAGING: SAPO ORDERS
-- =================================================================================================
-- OOM PREVENTION: "2-Scan + No GROUP BY"
--
--   Scan 1 (keys only): Lightweight technical dedup. Payload NOT read.
--   Scan 2 (payload):   INNER JOIN with winner_keys → extract JSON inline → output.
--                        NO GROUP BY — eliminates hash table (~1-2GB savings).
--                        Exact duplicates handled by ROW_NUMBER in business dedup step.
--
--   DuckDB sort operator can spill to disk efficiently (merge sort).
--   Hash aggregation (GROUP BY) cannot spill as effectively → removed.
-- =================================================================================================

WITH meta_keys AS (
    SELECT
        entity_id,
        event_timestamp,
        ingest_method
    FROM {{ source('sapo_raw', 'order') }}
    {% if is_incremental() %}
    WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{ this }})
    {% endif %}
),

deduped_keys AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                event_timestamp DESC,
                CASE
                    WHEN ingest_method = 'webhook' THEN 3
                    WHEN ingest_method = 'history_log' THEN 2
                    ELSE 1
                END DESC
        ) AS rn
    FROM meta_keys
),

winner_keys AS (
    SELECT entity_id, event_timestamp, ingest_method
    FROM deduped_keys
    WHERE rn = 1
),

-- Single payload scan: extract all fields, NO GROUP BY, NO ANY_VALUE
-- Exact duplicates (if any) are handled by ROW_NUMBER below
extracted AS (
    SELECT
        s.entity_id,
        s.entity_type,
        s.event_timestamp,
        s.ingest_method,

        json_extract_string(s.payload, '$.id') as order_id,
        json_extract_string(s.payload, '$.modified_on') as modified_on,
        json_extract_string(s.payload, '$.code') as order_code,
        json_extract_string(s.payload, '$.status') as order_status,
        json_extract_string(s.payload, '$.financial_status') as financial_status,
        json_extract_string(s.payload, '$.fulfillment_status') as fulfillment_status,
        json_extract_string(s.payload, '$.packed_status') as packed_status,
        json_extract_string(s.payload, '$.received_status') as received_status,

        try_cast(json_extract_string(s.payload, '$.total') as DECIMAL(18,2)) as total_amount,
        try_cast(json_extract_string(s.payload, '$.total_discount') as DECIMAL(18,2)) as total_discount,
        try_cast(json_extract_string(s.payload, '$.total_tax') as DECIMAL(18,2)) as tax_amount,

        json_extract_string(s.payload, '$.customer_id') as customer_id,
        json_extract_string(s.payload, '$.source_id') as source_id,
        json_extract_string(s.payload, '$.location_id') as location_id,

        json_extract_string(s.payload, '$.assignee_id') as assignee_id,
        json_extract_string(s.payload, '$.assignee.name') as assignee_name,
        json_extract_string(s.payload, '$.assignee.full_name') as assignee_full_name,
        json_extract_string(s.payload, '$.assignee.email') as assignee_email,
        json_extract_string(s.payload, '$.account_id') as account_id,
        json_extract_string(s.payload, '$.account.name') as account_name,
        json_extract_string(s.payload, '$.account.full_name') as account_full_name,
        json_extract_string(s.payload, '$.account.email') as account_email,
        json_extract_string(s.payload, '$.user_name') as user_name,

        json_extract_string(s.payload, '$.customer_data.name') as customer_name,
        json_extract_string(s.payload, '$.customer_data.phone_number') as customer_phone,
        json_extract_string(s.payload, '$.customer_data.email') as customer_email,

        json_extract_string(s.payload, '$.billing_address') as billing_address_json,
        json_extract_string(s.payload, '$.shipping_address') as shipping_address_json,

        coalesce(json_extract_string(s.payload, '$.shipping_address.province'), json_extract_string(s.payload, '$.shipping_address.city')) as shipping_province,
        json_extract_string(s.payload, '$.shipping_address.district') as shipping_district,
        json_extract_string(s.payload, '$.shipping_address.ward') as shipping_ward,
        json_extract_string(s.payload, '$.shipping_address.address1') as shipping_address1,
        json_extract_string(s.payload, '$.shipping_address.address2') as shipping_address2,
        json_extract_string(s.payload, '$.shipping_address.city') as shipping_city,
        json_extract_string(s.payload, '$.shipping_address.zip') as shipping_zip,
        json_extract_string(s.payload, '$.shipping_address.country') as shipping_country,
        json_extract_string(s.payload, '$.shipping_address.phone') as shipping_phone,
        json_extract_string(s.payload, '$.shipping_address.name') as shipping_name,

        coalesce(json_extract_string(s.payload, '$.billing_address.province'), json_extract_string(s.payload, '$.billing_address.city')) as billing_province,
        json_extract_string(s.payload, '$.billing_address.district') as billing_district,
        json_extract_string(s.payload, '$.billing_address.ward') as billing_ward,
        json_extract_string(s.payload, '$.billing_address.address1') as billing_address1,
        json_extract_string(s.payload, '$.billing_address.address2') as billing_address2,
        json_extract_string(s.payload, '$.billing_address.city') as billing_city,
        json_extract_string(s.payload, '$.billing_address.zip') as billing_zip,
        json_extract_string(s.payload, '$.billing_address.country') as billing_country,
        json_extract_string(s.payload, '$.billing_address.company') as billing_company,
        json_extract_string(s.payload, '$.billing_address.phone') as billing_phone,
        json_extract_string(s.payload, '$.billing_address.tax_code') as billing_tax_code,

        json_extract_string(s.payload, '$.note') as note,
        json_extract_string(s.payload, '$.tags') as tags,
        json_extract_string(s.payload, '$.discount_codes') as discount_codes,
        json_extract_string(s.payload, '$.client_details') as client_details,

        json_extract_string(s.payload, '$.created_on') as created_on,
        json_extract_string(s.payload, '$.issued_on') as issued_on,
        json_extract_string(s.payload, '$.finalized_on') as finalized_on,
        json_extract_string(s.payload, '$.cancelled_on') as cancelled_on,
        json_extract_string(s.payload, '$.completed_on') as completed_on,

        json_extract_string(s.payload, '$.channel') as channel_name,
        json_extract_string(s.payload, '$.expected_payment_method_id') as payment_method_id

    FROM {{ source('sapo_raw', 'order') }} s
    INNER JOIN winner_keys k
        ON s.entity_id = k.entity_id
        AND s.event_timestamp = k.event_timestamp
        AND s.ingest_method = k.ingest_method
),

-- Business dedup + exact duplicate handling — all on lightweight extracted strings
json_parsed AS (
    SELECT *
    FROM extracted
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY order_id
        ORDER BY event_timestamp DESC, modified_on DESC
    ) = 1
),

mapped_tags AS (
    SELECT id, mapping_tag
    FROM {{ ref('ref_order_sources') }}
    WHERE mapping_tag IS NOT NULL
)

SELECT
    o.*,
    coalesce(cast(mt.id as string), cast(o.source_id as string)) as final_source_id,
    pm.name as payment_method_name,
    s.name as source_name,
    l.name as location_name

FROM json_parsed o
LEFT JOIN mapped_tags mt
    ON o.tags IS NOT NULL
    AND o.tags LIKE '%' || mt.mapping_tag || '%'
LEFT JOIN {{ ref('ref_payment_methods') }} pm ON try_cast(o.payment_method_id as BIGINT) = pm.id
LEFT JOIN {{ ref('ref_order_sources') }} s ON coalesce(cast(mt.id as string), cast(o.source_id as string)) = cast(s.id as string)
LEFT JOIN {{ ref('ref_branch_locations') }} l ON try_cast(o.location_id as BIGINT) = l.id

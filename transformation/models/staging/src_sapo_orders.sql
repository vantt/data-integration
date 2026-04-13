{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='delete+insert',
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO ORDERS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, modified_on + ingest_method priority).
--   3. Extract ALL scalar JSON fields + 3 nested arrays as text columns.
--   4. Business dedup by order_id (latest modified_on wins; compare new vs existing rows).
--   5. Discard payload → frees memory for downstream models.
--
-- Incremental strategy:
--   - Filters on _dlt_load_id (monotonically increasing) to catch late-arriving data.
--   - New extracted rows are UNIONed with existing rows for the same order_ids before
--     final dedup, so a later load never overwrites a more-recent record.
--
-- OOM-safe:
--   - Tech dedup ROW_NUMBER sorts on lightweight keys (entity_id, modified_on).
--     Payload carried in memory during sort but not used as sort key.
--   - JSON extraction runs on tech-deduped rows only.
--   - Biz dedup ROW_NUMBER runs on flat extracted data — NO payload, negligible memory.
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
    FROM {{ source('sapo_raw', 'order') }}
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

        -- Order IDs & codes
        json_extract_string(payload, '$.id') as order_id,
        json_extract_string(payload, '$.modified_on') as modified_on,
        json_extract_string(payload, '$.code') as order_code,

        -- Statuses
        json_extract_string(payload, '$.status') as order_status,
        json_extract_string(payload, '$.financial_status') as financial_status,
        json_extract_string(payload, '$.fulfillment_status') as fulfillment_status,
        json_extract_string(payload, '$.packed_status') as packed_status,
        json_extract_string(payload, '$.received_status') as received_status,

        -- Financials
        try_cast(json_extract_string(payload, '$.total') as DECIMAL(18,2)) as total_amount,
        try_cast(json_extract_string(payload, '$.total_discount') as DECIMAL(18,2)) as total_discount,
        try_cast(json_extract_string(payload, '$.total_tax') as DECIMAL(18,2)) as tax_amount,

        -- Foreign keys
        json_extract_string(payload, '$.customer_id') as customer_id,
        json_extract_string(payload, '$.source_id') as source_id,
        json_extract_string(payload, '$.location_id') as location_id,

        -- Assignee & Account
        json_extract_string(payload, '$.assignee_id') as assignee_id,
        json_extract_string(payload, '$.assignee.name') as assignee_name,
        json_extract_string(payload, '$.assignee.full_name') as assignee_full_name,
        json_extract_string(payload, '$.assignee.email') as assignee_email,
        json_extract_string(payload, '$.account_id') as account_id,
        json_extract_string(payload, '$.account.name') as account_name,
        json_extract_string(payload, '$.account.full_name') as account_full_name,
        json_extract_string(payload, '$.account.email') as account_email,
        json_extract_string(payload, '$.user_name') as user_name,

        -- Customer data
        json_extract_string(payload, '$.customer_data.name') as customer_name,
        json_extract_string(payload, '$.customer_data.phone_number') as customer_phone,
        json_extract_string(payload, '$.customer_data.email') as customer_email,

        -- Addresses (full JSON)
        json_extract_string(payload, '$.billing_address') as billing_address_json,
        json_extract_string(payload, '$.shipping_address') as shipping_address_json,

        -- Shipping address fields
        coalesce(json_extract_string(payload, '$.shipping_address.province'), json_extract_string(payload, '$.shipping_address.city')) as shipping_province,
        json_extract_string(payload, '$.shipping_address.district') as shipping_district,
        json_extract_string(payload, '$.shipping_address.ward') as shipping_ward,
        json_extract_string(payload, '$.shipping_address.address1') as shipping_address1,
        json_extract_string(payload, '$.shipping_address.address2') as shipping_address2,
        json_extract_string(payload, '$.shipping_address.city') as shipping_city,
        json_extract_string(payload, '$.shipping_address.zip') as shipping_zip,
        json_extract_string(payload, '$.shipping_address.country') as shipping_country,
        json_extract_string(payload, '$.shipping_address.phone') as shipping_phone,
        json_extract_string(payload, '$.shipping_address.name') as shipping_name,

        -- Billing address fields
        coalesce(json_extract_string(payload, '$.billing_address.province'), json_extract_string(payload, '$.billing_address.city')) as billing_province,
        json_extract_string(payload, '$.billing_address.district') as billing_district,
        json_extract_string(payload, '$.billing_address.ward') as billing_ward,
        json_extract_string(payload, '$.billing_address.address1') as billing_address1,
        json_extract_string(payload, '$.billing_address.address2') as billing_address2,
        json_extract_string(payload, '$.billing_address.city') as billing_city,
        json_extract_string(payload, '$.billing_address.zip') as billing_zip,
        json_extract_string(payload, '$.billing_address.country') as billing_country,
        json_extract_string(payload, '$.billing_address.company') as billing_company,
        json_extract_string(payload, '$.billing_address.phone') as billing_phone,
        json_extract_string(payload, '$.billing_address.tax_code') as billing_tax_code,

        -- Misc
        json_extract_string(payload, '$.note') as note,
        json_extract_string(payload, '$.tags') as tags,
        json_extract_string(payload, '$.discount_codes') as discount_codes,
        json_extract_string(payload, '$.client_details') as client_details,

        -- Timestamps
        json_extract_string(payload, '$.created_on') as created_on,
        json_extract_string(payload, '$.issued_on') as issued_on,
        json_extract_string(payload, '$.finalized_on') as finalized_on,
        json_extract_string(payload, '$.cancelled_on') as cancelled_on,
        json_extract_string(payload, '$.completed_on') as completed_on,

        -- Channel & Payment
        json_extract_string(payload, '$.channel') as channel_name,
        json_extract_string(payload, '$.expected_payment_method_id') as payment_method_id,

        -- Nested JSON arrays (as text for downstream unnest models)
        json_extract_string(payload, '$.order_line_items') as order_line_items_json,
        json_extract_string(payload, '$.payments') as payments_json,
        json_extract_string(payload, '$.fulfillments') as fulfillments_json

    FROM deduped
    WHERE rn = 1
)

-- Step 2: Business dedup by order_id — compare new vs existing before overwriting
SELECT * FROM (
    SELECT * FROM extracted
    {% if is_incremental() %}
    UNION ALL
    SELECT existing.* FROM {{ this }} existing
    INNER JOIN (SELECT DISTINCT order_id FROM extracted) new_keys
        ON existing.order_id = new_keys.order_id
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY order_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method
            WHEN 'webhook' THEN 1
            WHEN 'history_log' THEN 2
            ELSE 3
        END
) = 1

{{ config(
    materialized='incremental',
    unique_key='order_id',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
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
    FROM {{ source('sapo_v2_raw', 'order') }}
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
                -- Priority: webhook=1 (highest) > history_log=2 > other=3 (ASC → lowest wins).
                -- Matches biz dedup encoding below (QUALIFY block) — keep both in sync.
                CASE
                    WHEN ingest_method = 'webhook' THEN 1
                    WHEN ingest_method = 'history_log' THEN 2
                    ELSE 3
                END ASC
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
        json_extract_string(payload, '$.payment_status') as financial_status,
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
        -- Human-readable coupon code on the order (e.g. OFF100, HUG50). Drives Hug redeem-matching:
        -- match (customer_id + order_coupon_code) back to an issued hug_voucher row.
        -- NOTE: $.order_coupon_code is a JSON OBJECT ({coupon_code, coupon_promotion_id,
        -- order_total_required, discount_amount, ...}); the code string is the nested .coupon_code.
        json_extract_string(payload, '$.order_coupon_code.coupon_code') as order_coupon_code,
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
        -- Sapo API returns payment records under 'prepayments', not 'payments'
        -- ($.payments does not exist in any order payload; verified across all ingest methods)
        json_extract_string(payload, '$.prepayments') as payments_json,
        json_extract_string(payload, '$.fulfillments') as fulfillments_json,
        json_extract_string(payload, '$.discount_items') as discount_items_json

    FROM deduped
    WHERE rn = 1
)

-- Step 2: Business dedup by order_id — compare new vs existing before overwriting
-- NOTE: Use explicit column names (not SELECT *) to prevent positional mismatch
-- when schema evolves between incremental runs (e.g., new columns added to extracted).
-- union_cols_base: stable columns always present in the materialized {{ this }} table.
-- New columns (e.g. discount_items_json) are appended separately with NULL fallback
-- so that incremental runs don't fail when the column hasn't been added to {{ this }} yet.
{% set union_cols_base = 'entity_id, entity_type, event_timestamp, ingest_method, _dlt_load_id, order_id, modified_on, order_code, order_status, financial_status, fulfillment_status, packed_status, received_status, total_amount, total_discount, tax_amount, customer_id, source_id, location_id, assignee_id, assignee_name, assignee_full_name, assignee_email, account_id, account_name, account_full_name, account_email, user_name, customer_name, customer_phone, customer_email, billing_address_json, shipping_address_json, shipping_province, shipping_district, shipping_ward, shipping_address1, shipping_address2, shipping_city, shipping_zip, shipping_country, shipping_phone, shipping_name, billing_province, billing_district, billing_ward, billing_address1, billing_address2, billing_city, billing_zip, billing_country, billing_company, billing_phone, billing_tax_code, note, tags, discount_codes, client_details, created_on, issued_on, finalized_on, cancelled_on, completed_on, channel_name, payment_method_id, order_line_items_json, payments_json, fulfillments_json' %}
{% set union_cols = union_cols_base + ', discount_items_json, order_coupon_code' %}
SELECT * FROM (
    SELECT {{ union_cols }} FROM extracted
    {% if is_incremental() and '_dlt_load_id' in existing_cols %}
    UNION ALL
    SELECT {{ union_cols_base }},
        {% if 'discount_items_json' in existing_cols %}discount_items_json{% else %}NULL{% endif %} AS discount_items_json,
        {% if 'order_coupon_code' in existing_cols %}order_coupon_code{% else %}NULL{% endif %} AS order_coupon_code
    FROM {{ this }}
    WHERE order_id IN (SELECT DISTINCT order_id FROM extracted)
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY order_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        -- Priority: webhook=1 (highest) > history_log=2 > other=3 (ASC → lowest wins).
        -- Matches tech dedup encoding above (deduped CTE) — keep both in sync.
        CASE ingest_method
            WHEN 'webhook' THEN 1
            WHEN 'history_log' THEN 2
            ELSE 3
        END ASC
) = 1

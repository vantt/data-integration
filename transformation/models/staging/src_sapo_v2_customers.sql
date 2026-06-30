{{ config(
    materialized='incremental',
    unique_key='sapo_customer_id',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    tags=['source', 'sapo']
) }}

-- =================================================================================================
-- SOURCE EXTRACTION: SAPO CUSTOMERS
-- =================================================================================================
-- Purpose:
--   1. Read raw Parquet from Data Lake (dlt pipeline output).
--   2. Technical dedup by entity_id (ROW_NUMBER, modified_on + ingest_method priority).
--   3. Extract ALL scalar JSON fields from payload.
--   4. Business dedup by sapo_customer_id (latest modified_on wins; compare new vs existing rows).
--   5. Discard payload -> frees memory for downstream models.
--
-- Incremental strategy:
--   - Filters on _dlt_load_id (monotonically increasing) to catch late-arriving data.
--   - New extracted rows are UNIONed with existing rows for the same customer_ids before
--     final dedup, so a later load never overwrites a more-recent record.
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
    FROM {{ source('sapo_v2_raw', 'customer') }}
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

        -- Customer IDs
        json_extract_string(payload, '$.id') as sapo_customer_id,
        json_extract_string(payload, '$.modified_on') as modified_on,
        json_extract_string(payload, '$.code') as customer_code,

        -- Personal info
        json_extract_string(payload, '$.name') as full_name,
        json_extract_string(payload, '$.phone_number') as phone_number,
        json_extract_string(payload, '$.email') as email,
        json_extract_string(payload, '$.status') as status,

        -- Date of birth
        json_extract_string(payload, '$.birthday') as birthday,
        json_extract_string(payload, '$.dob') as dob,

        -- Gender (consolidate sex/gender)
        coalesce(json_extract_string(payload, '$.sex'), json_extract_string(payload, '$.gender')) as sex,

        -- Group
        json_extract_string(payload, '$.customer_group') as customer_group,

        -- Address
        json_extract_string(payload, '$.addresses[0].city') as city,
        coalesce(json_extract_string(payload, '$.addresses[0].province'), json_extract_string(payload, '$.addresses[0].city')) as province,
        json_extract_string(payload, '$.addresses[0].district') as district,
        json_extract_string(payload, '$.addresses[0].ward') as ward,
        json_extract_string(payload, '$.addresses[0].address1') as address1,
        json_extract_string(payload, '$.addresses[0].country') as country,
        json_extract_string(payload, '$.addresses[0].address2') as address2,
        json_extract_string(payload, '$.addresses[0].zip') as zip,
        json_extract_string(payload, '$.addresses[0].company') as company,
        json_extract_string(payload, '$.addresses[0].phone') as address_phone,

        -- Financials
        try_cast(json_extract_string(payload, '$.total_expense') as DECIMAL(18,2)) as total_expense,
        try_cast(json_extract_string(payload, '$.order_count') as INTEGER) as orders_count,
        try_cast(json_extract_string(payload, '$.loyalty_point') as INTEGER) as loyalty_point,
        try_cast(json_extract_string(payload, '$.debt') as DECIMAL(18,2)) as debt,

        -- B2B / misc scalars
        json_extract_string(payload, '$.assignee_id') as assignee_id,
        json_extract_string(payload, '$.tax_number') as tax_number,
        json_extract_string(payload, '$.website') as website,
        json_extract_string(payload, '$.description') as description,
        try_cast(json_extract_string(payload, '$.default_discount_rate') as REAL) as default_discount_rate,
        json_extract_string(payload, '$.default_price_list_id') as default_price_list_id,

        -- Timestamps
        json_extract_string(payload, '$.created_on') as created_on,

        -- JSON arrays as text: bridge tables (tags/notes/contacts/addresses) read from stg;
        -- loyalty_customer_json and social_customers_json also flow through to dim_customers.
        json_extract_string(payload, '$.tags') as tags_json,
        json_extract_string(payload, '$.notes') as notes_json,
        json_extract_string(payload, '$.contacts') as contacts_json,
        json_extract_string(payload, '$.social_customers') as social_customers_json,
        json_extract_string(payload, '$.addresses') as addresses_json,
        json_extract_string(payload, '$.loyalty_customer') as loyalty_customer_json

    FROM deduped
    WHERE rn = 1
)

-- Step 2: Business dedup by sapo_customer_id — compare new vs existing before overwriting
-- NOTE: Use explicit column names (not SELECT *) to prevent positional mismatch
{% set union_cols = 'entity_id, entity_type, event_timestamp, ingest_method, _dlt_load_id, sapo_customer_id, modified_on, customer_code, full_name, phone_number, email, status, birthday, dob, sex, customer_group, city, province, district, ward, address1, country, address2, zip, company, address_phone, total_expense, orders_count, loyalty_point, debt, assignee_id, tax_number, website, description, default_discount_rate, default_price_list_id, created_on, tags_json, notes_json, contacts_json, social_customers_json, addresses_json, loyalty_customer_json' %}
SELECT * FROM (
    SELECT {{ union_cols }} FROM extracted
    {% if is_incremental() and '_dlt_load_id' in existing_cols %}
    UNION ALL
    SELECT {{ union_cols }} FROM {{ this }}
    WHERE sapo_customer_id IN (SELECT DISTINCT sapo_customer_id FROM extracted)
    {% endif %}
)
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY sapo_customer_id
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method
            WHEN 'webhook' THEN 1
            WHEN 'history_log' THEN 2
            ELSE 3
        END
) = 1

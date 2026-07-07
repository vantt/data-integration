{{ config(
    materialized='view',
    tags=['staging', 'customers']
) }}

-- =================================================================================================
-- STAGING: SAPO CUSTOMERS
-- =================================================================================================
-- Purpose:
--   Reads from src_sapo_customers (already extracted & deduped).
--   Cleaning, formatting (phone, email, dates).
--   Exception: customer_group is NOT flat — src_ only extracts it as a stringified JSON
--   sub-object ({"id":..,"code":..,"name":..}), since one Sapo customer can only carry
--   one group and a bridge table wasn't warranted. Extract the 3 scalar fields here
--   (single parse point for the whole warehouse — see plans/260619-0830-crm-tag-acl-sync/).
--   json_extract_string returns NULL on non-JSON input (handles the legacy 'Unknown' literal).
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('src_sapo_v2_customers') }}
)

SELECT
    entity_id,
    sapo_customer_id,
    customer_code,

    -- Personal info
    full_name,
    phone_number,
    email,
    status,

    -- Date of birth: consolidate birthday/dob
    coalesce(dob, birthday) as dob,
    sex,
    customer_group,  -- raw JSON blob, kept for reference; use the 3 columns below instead

    -- customer_group parsed (ACL data contract — see plans/260619-0830-crm-tag-acl-sync/).
    -- id is the ONLY stable key: Sapo has renamed a group's code/name mid-flight while
    -- keeping the same id (e.g. BANLE -> TYPE_RETAIL). NULL for the legacy 'Unknown' literal.
    json_extract_string(customer_group, '$.id')   as customer_group_id,
    json_extract_string(customer_group, '$.code') as customer_group_code,
    json_extract_string(customer_group, '$.name') as customer_group_name,

    -- Address
    city,
    province,
    district,
    ward,
    address1,
    country,
    address2,
    zip,
    company,
    address_phone,

    -- Financials
    total_expense,
    orders_count,
    loyalty_point,
    debt,

    -- B2B / misc scalars
    assignee_id,
    tax_number,
    website,
    description,
    default_discount_rate,
    default_price_list_id,

    -- Timestamps
    created_on,
    modified_on,
    event_timestamp,

    -- JSON arrays (bridge tables read from here; loyalty+social also flow to dim_customers)
    tags_json,
    notes_json,
    contacts_json,
    social_customers_json,
    addresses_json,
    loyalty_customer_json

FROM source_data

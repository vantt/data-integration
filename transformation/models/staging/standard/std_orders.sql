{{ config(
    materialized='view',
    tags=['standard', 'orders']
) }}

-- =================================================================================================
-- HOP 5: STANDARD ORDERS (GOLD STANDARD) - v2.0
-- =================================================================================================
-- Changelog v2.0:
-- - Added address snapshots (billing_address, shipping_address)
-- - Added detailed lifecycle timestamps (issued, finalized, completed)
-- - Added financial status and fulfillment status mapping
-- =================================================================================================

WITH source_data AS (
    SELECT * FROM {{ ref('stg_sapo_orders') }}
)

SELECT
    -- ID & Codes
    order_id,
    order_code,
    source_id,
    'sapo' as source_system,
    
    -- Foreign Keys
    customer_id,
    location_id,
    account_id as salesperson_id,
    
    -- Timestamps - Lifecycle
    try_cast(created_on as TIMESTAMP) as created_at,
    try_cast(modified_on as TIMESTAMP) as updated_at,
    try_cast(issued_on as TIMESTAMP) as issued_at,
    try_cast(finalized_on as TIMESTAMP) as finalized_at,
    try_cast(completed_on as TIMESTAMP) as completed_at,
    try_cast(cancelled_on as TIMESTAMP) as cancelled_at,
    
    -- Status Mapping
    CASE 
        WHEN order_status = 'cancelled' THEN 'CANCELLED'
        WHEN order_status = 'completed' THEN 'COMPLETED'
        WHEN order_status = 'archived' THEN 'ARCHIVED'
        WHEN order_status = 'draft' THEN 'DRAFT'
        ELSE 'OPEN'
    END as status,
    
    CASE 
        WHEN financial_status = 'paid' THEN 'PAID'
        WHEN financial_status = 'partially_paid' THEN 'PARTIALLY_PAID'
        WHEN financial_status = 'refunded' THEN 'REFUNDED'
        WHEN financial_status = 'voided' THEN 'VOIDED'
        WHEN financial_status = 'pending' THEN 'PENDING'
        ELSE 'UNPAID' 
    END as payment_status,
    
    CASE 
        WHEN fulfillment_status = 'fulfilled' THEN 'FULFILLED'
        WHEN fulfillment_status = 'partial' THEN 'PARTIALLY_FULFILLED'
        WHEN fulfillment_status = 'restocked' THEN 'RETURNED'
        WHEN fulfillment_status = 'shipping' THEN 'SHIPPING'
        ELSE 'UNFULFILLED'
    END as fulfillment_status,
    
    -- Financials
    total_amount,
    total_discount as total_discount_amount,
    tax_amount as total_tax_amount,
    'VND' as currency_code,
    
    -- Address Snapshots (JSON)
    -- DuckDB maintains JSON type, useful for downstream parsing if needed.
    billing_address_json as billing_address,
    shipping_address_json as shipping_address,

    shipping_province,
    shipping_district,
    shipping_ward,
    shipping_address1,
    shipping_address2,
    shipping_city,
    shipping_zip,
    shipping_country,
    shipping_phone,
    shipping_name,

    billing_province,
    billing_district,
    billing_ward,
    billing_address1,
    billing_address2,
    billing_city,
    billing_zip,
    billing_country,
    billing_company,
    billing_phone,
    billing_tax_code,
    discount_codes_json as discount_codes,
    
    tags,
    note as note,
    
    -- Metadata
    coalesce(channel_name, 'online') as channel -- Default to online if null
    
FROM source_data

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
    SELECT * FROM {{ ref('stg_sapo_v2_orders') }}
)

SELECT
    -- ID & Codes
    order_id,
    order_code,
    -- Enriched source_id: if order.tags matches a mapping_tag in ref_order_sources,
    -- stg_sapo_orders resolved to the composite child id (e.g. '3988158_1'
    -- = "Shopee - JPC OFFICIAL"); otherwise falls back to raw generic id (e.g. '3988158' = "Shopee").
    -- This makes downstream fact_orders.channel_key resolve to the right tier-4 storefront
    -- when mapping_tag coverage exists, or to the "(Unspecified)" parent row otherwise.
    final_source_id as source_id,
    'sapo_v2' as source_system,
    'v2'   as source_version,
    
    -- Foreign Keys
    customer_id,
    location_id,

    -- Sales attribution: Sapo has TWO distinct user fields per order.
    -- seller_* (from Sapo `assignee`) = người được giao đơn → primary for team attribution & commission
    -- creator_* (from Sapo `account`)  = người tạo đơn trên Sapo → operational, fallback only
    -- See docs/context/sales-segmentation-guide.md § 3.4 for business rationale.
    assignee_id as seller_user_id,
    coalesce(assignee_full_name, assignee_name) as seller_name,
    assignee_email as seller_email,

    account_id as creator_user_id,
    coalesce(account_full_name, account_name, user_name) as creator_name,
    account_email as creator_email,
    
    -- Timestamps - Lifecycle
    try_cast(created_on as TIMESTAMPTZ) as created_at,
    try_cast(modified_on as TIMESTAMPTZ) as updated_at,
    try_cast(issued_on as TIMESTAMPTZ) as issued_at,
    try_cast(finalized_on as TIMESTAMPTZ) as finalized_at,
    try_cast(completed_on as TIMESTAMPTZ) as completed_at,
    try_cast(cancelled_on as TIMESTAMPTZ) as cancelled_at,
    
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
        WHEN financial_status = 'partial' THEN 'PARTIALLY_PAID'
        WHEN financial_status = 'refunded' THEN 'REFUNDED'
        WHEN financial_status = 'pending' THEN 'PENDING'
        ELSE 'UNPAID'
    END as payment_status,
    
    CASE 
        -- =========================================================================================
        -- HYBRID FULFILLMENT LOGIC
        -- =========================================================================================
        -- Combines Sapo's "Logistics Status" with Internal "Financial Status".
        -- Goal: 'COMPLETED' must mean Money In + Goods Out.
        
        -- 1. Order Lifecycle (Top Priority)
        WHEN order_status = 'cancelled' THEN 'CANCELLED'
        
        -- 2. Sapo Specific Logistics Status
        WHEN fulfillment_status = 'restocked' THEN 'RETURNED'
        WHEN fulfillment_status = 'partial' THEN 'PARTIALLY_FULFILLED'
        
        -- 3. Legacy Composite Logic (Most Important for Revenue Recog)
        -- Completed = Paid + Packed + Received
        WHEN financial_status = 'paid' AND packed_status = 'packed' AND received_status = 'received' THEN 'COMPLETED'
        
        -- 4. In-Transit States
        -- Shipped (Paid) = Paid + Packed -> Good to go
        WHEN financial_status = 'paid' AND packed_status = 'packed' THEN 'SHIPPED_PAID'
        
        -- Shipped (Unpaid/COD) = Packed (but not paid) -> COD Order
        WHEN packed_status = 'packed' THEN 'SHIPPED_COD'
        
        -- Paid (Processing) = Paid (but not packed) -> Pre-order or Backlog
        WHEN financial_status = 'paid' THEN 'PAID_PROCESSING'
        
        -- 5. Fallback
        ELSE 'IN_PROGRESS'
    END as fulfillment_status,
    
    -- Financials
    total_amount,
    total_discount as total_discount_amount,
    tax_amount as vat_amount,
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
    shipping_zip AS shipping_postal_code,
    shipping_country,
    shipping_phone,
    shipping_name,

    billing_province,
    billing_district,
    billing_ward,
    billing_address1,
    billing_address2,
    billing_city,
    billing_zip AS billing_postal_code,
    billing_country,
    billing_company,
    billing_phone,
    billing_tax_code,
    discount_codes,
    client_details AS client_info,
    
    tags,
    note as note,
    
    -- Metadata
    coalesce(channel_name, 'online') as channel -- Default to online if null
    
FROM source_data

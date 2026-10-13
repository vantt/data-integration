{{ config(materialized='view', tags=['stg', 'shopee']) }}

-- Shopee order × product line items: thin view, just casts + key columns.

SELECT
    order_code,
    product_code,
    product_name,
    source_file,
    ingested_at
FROM {{ ref('src_shopee_order_revenue_items') }}

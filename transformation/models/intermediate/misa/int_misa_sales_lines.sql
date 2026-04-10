{{ config(
    tags=['int', 'misa'],
    materialized='table',
    location="{{ get_rolling_location() }}"
) }}

-- MISA per-invoice-line with COGS, margin, and channel enrichment.
-- Intermediate enrichment layer — NOT a primary fact (all orders exist in Sapo fact_orders).
-- Rolling location for P0 Metabase access; P1 joins into fact_order_economics.

SELECT
    {{ dbt_utils.generate_surrogate_key(['voucher_no', 'line_no']) }} AS misa_sales_line_sk,

    -- Business keys
    voucher_no,
    line_no,

    -- Temporal
    posting_date,
    voucher_date,
    invoice_date,
    invoice_no,

    -- Product
    product_code,
    product_name,
    product_name_on_document,
    unit_of_measure,
    is_promo_line,

    -- Customer
    customer_code,
    customer_name,

    -- Quantity & amounts
    quantity,
    unit_price,
    revenue_gross,
    discount_amount,
    total_payment,
    cogs_amount,
    revenue_net_of_discount,
    gross_profit,
    gross_margin_pct,

    -- Accounting accounts
    debit_account,
    credit_account,
    discount_account,
    cogs_account,

    -- Channel & salesperson
    channel_code,
    channel_name,
    channel_group,
    voucher_source_hint,
    salesperson_name,

    -- Raw description
    description,

    -- Lineage
    source_file,
    ingested_at

FROM {{ ref('stg_misa_sales_lines') }}

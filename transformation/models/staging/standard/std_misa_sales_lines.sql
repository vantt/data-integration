{{ config(
    materialized='view',
    tags=['standard', 'misa']
) }}

-- =================================================================================================
-- STD: MISA SALES LINES
-- =================================================================================================
-- Source:  stg_misa_sales_lines
-- Grain:   1 row per (voucher_no, line_no) — 1 row per invoice line
-- PK:      (voucher_no, line_no) — natural key; surrogate key misa_sales_line_sk lives in int_
--
-- Faithful pass-through: all stg output columns reproduced verbatim (no re-cast, no drop,
-- no rename). cogs_amount and gross_profit retain the MIXED 632+642 total on purpose;
-- downstream int_misa_sales_lines and fact models apply the 632-only filter.
--
-- Appended columns (std-gate derived / provenance):
--   cost_account_group  — bucket derived from cogs_account prefix (632 / 642 / other)
--   source_system       — literal 'misa'
--   source_version      — MISA report-format version tag; bump when parser/report changes
-- =================================================================================================

SELECT
    -- Natural key
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

    -- Derived margin fields (from stg; mixed 632+642, unfiltered — see header note)
    revenue_net_of_discount,
    gross_profit,
    gross_margin_pct,

    -- Accounting accounts
    debit_account,
    credit_account,
    discount_account,
    cogs_account,

    -- Channel (enriched from stg via ref_misa_channel_codes)
    channel_code,
    channel_name,
    channel_group,

    -- Voucher source hint
    voucher_source_hint,

    -- Salesperson & description
    salesperson_name,
    description,

    -- Lineage
    source_file,
    ingested_at,

    -- Std-gate derived: account bucket (NOT filtered here — faithful pass-through)
    CASE
        WHEN cogs_account LIKE '632%' THEN '632'
        WHEN cogs_account LIKE '642%' THEN '642'
        ELSE 'other'
    END AS cost_account_group,

    -- Provenance
    'misa'           AS source_system,
    'sales_lines_v1' AS source_version

FROM {{ ref('stg_misa_sales_lines') }}

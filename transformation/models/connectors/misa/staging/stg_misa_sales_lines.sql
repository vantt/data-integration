{{ config(materialized='view', tags=['stg', 'misa']) }}

-- MISA sales lines: type casting, channel enrichment, margin derivation.

SELECT
    s.voucher_no,
    s.line_no,

    -- Temporal
    CAST(s.posting_date AS DATE)    AS posting_date,
    CAST(s.voucher_date AS DATE)    AS voucher_date,
    CAST(s.invoice_date AS DATE)    AS invoice_date,
    s.invoice_no,

    -- Product
    s.product_code,
    s.product_name,
    s.product_name_on_document,
    s.unit_of_measure,
    s.is_promo_line,

    -- Customer
    s.customer_code,
    s.customer_name,

    -- Quantity & amounts
    CAST(s.quantity AS BIGINT)              AS quantity,
    CAST(s.unit_price AS DECIMAL(18, 4))    AS unit_price,
    CAST(s.revenue_gross AS BIGINT)         AS revenue_gross,
    CAST(s.discount_amount AS BIGINT)       AS discount_amount,
    CAST(s.total_payment AS BIGINT)         AS total_payment,
    CAST(s.cogs_amount AS BIGINT)           AS cogs_amount,

    -- Derived margin fields
    COALESCE(CAST(s.revenue_gross AS BIGINT), 0)
        - COALESCE(CAST(s.discount_amount AS BIGINT), 0)
        AS revenue_net_of_discount,

    COALESCE(CAST(s.revenue_gross AS BIGINT), 0)
        - COALESCE(CAST(s.discount_amount AS BIGINT), 0)
        - COALESCE(CAST(s.cogs_amount AS BIGINT), 0)
        AS gross_profit,

    CASE
        WHEN (COALESCE(CAST(s.revenue_gross AS BIGINT), 0) - COALESCE(CAST(s.discount_amount AS BIGINT), 0)) = 0
        THEN NULL
        ELSE (
            COALESCE(CAST(s.revenue_gross AS BIGINT), 0)
            - COALESCE(CAST(s.discount_amount AS BIGINT), 0)
            - COALESCE(CAST(s.cogs_amount AS BIGINT), 0)
        )::DOUBLE / (
            COALESCE(CAST(s.revenue_gross AS BIGINT), 0)
            - COALESCE(CAST(s.discount_amount AS BIGINT), 0)
        )
    END AS gross_margin_pct,

    -- Accounting accounts
    s.debit_account,
    s.credit_account,
    s.discount_account,
    s.cogs_account,

    -- Channel (from source + seed enrichment)
    COALESCE(s.channel_code, 'UNKNOWN') AS channel_code,
    COALESCE(ch.channel_name, 'Chưa phân loại') AS channel_name,
    COALESCE(ch.channel_group, 'UNKNOWN') AS channel_group,

    -- Voucher source hint (heuristic classification for cross-source join)
    CASE
        WHEN s.voucher_no LIKE 'SON%' THEN 'SAPO_DEALER'
        WHEN regexp_matches(s.voucher_no, '^2[0-9]{5}[A-Z0-9]{8,}$') THEN 'SHOPEE'
        WHEN regexp_matches(s.voucher_no, '^58[0-9]{11,}$') THEN 'AEON'
        ELSE 'OTHER'
    END AS voucher_source_hint,

    -- Salesperson & description
    s.salesperson_name,
    s.description,

    -- Lineage
    s.source_file,
    s.ingested_at

FROM {{ ref('src_misa_sales_lines') }} s
LEFT JOIN {{ ref('ref_misa_channel_codes') }} ch
    ON COALESCE(s.channel_code, 'UNKNOWN') = ch.channel_code

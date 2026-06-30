{{ config(
    tags=['mart', 'cogs'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- Order-grain COGS reconciliation summary.
-- Grain: one row per order_code.
-- Aggregates int_order_cogs_reconciled (order × SKU grain) to order level.
-- Purpose: pre-compute COGS variance totals consumed by CRM order detail panel.

SELECT
    order_code,
    SUM(cogs_goods_sapo)                                            AS sapo_total,
    SUM(cogs_goods_misa)                                            AS misa_total,
    SUM(cogs_goods_sapo) - SUM(cogs_goods_misa)                    AS cogs_variance,
    CASE
        WHEN SUM(cogs_goods_misa) IS NOT NULL AND SUM(cogs_goods_misa) != 0
        THEN (SUM(cogs_goods_sapo) - SUM(cogs_goods_misa))::DOUBLE
             / SUM(cogs_goods_misa)
        ELSE NULL
    END                                                             AS cogs_variance_pct,
    CASE
        WHEN SUM(cogs_goods_misa) IS NOT NULL AND SUM(cogs_goods_misa) != 0
        THEN ABS((SUM(cogs_goods_sapo) - SUM(cogs_goods_misa))::DOUBLE
             / SUM(cogs_goods_misa)) > 0.10
        ELSE NULL
    END                                                             AS is_high_variance,
    COUNT(*)                                                        AS sku_count
FROM {{ ref('int_order_cogs_reconciled') }}
GROUP BY order_code

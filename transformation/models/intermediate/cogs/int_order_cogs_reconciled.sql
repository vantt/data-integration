{{ config(
    tags=['int', 'cogs'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

-- =================================================================================================
-- INT: ORDER COGS RECONCILED
-- =================================================================================================
-- Grain:   (order_code, sku) — one row per order × SKU combination
-- Purpose: Reconcile Sapo-MAC COGS (authoritative, from inventory movements) against
--          MISA TK632 COGS (accounting) per order × SKU.
--
-- Join strategy: FULL OUTER JOIN on (order_code, sku).
--   ~4% of MISA 632 product codes have no matching Sapo SKU (service/cost lines mapped
--   differently); these surface as cogs_source='misa' rows and are accepted, NOT dropped.
--
-- cogs_goods_primary:
--   Var-driven (default 'sapo_mac'). This is the ONLY column downstream COGS totals may use.
--   Set var('cogs_primary_source', 'misa') in dbt_project.yml or --vars to switch.
--
-- Aggregation rule: NEVER sum cogs_goods_sapo + cogs_goods_misa. They measure the same cost
--   from different systems; summing would double-count.
--
-- Sapo return legs (trans_type=350, movement_direction='IN') are included in the netting
--   formula for correctness, but currently contribute 0 because 350 rows carry cogs_amount=0
--   (returns use import_amount, not export_amount). No-op today — kept for future correctness.
-- =================================================================================================

WITH sapo_cogs AS (
    -- Sapo-MAC COGS per order × SKU, derived from inventory movement export legs.
    -- trans_type 301 = sale fulfillment (OUT legs carry non-zero cogs_amount = export_amount).
    -- trans_type 350 = return receipt (IN legs, cogs_amount = 0 today — no-op, kept for clarity).
    -- quantity_delta != 0 excludes catalog/cost-adjust rows that carry no quantity change.
    SELECT
        document_code                                               AS order_code,
        sku,
        MAX(variant_id)                                             AS variant_id,

        -- Net signed quantity (+ received, − shipped)
        SUM(quantity_delta)                                         AS qty_sapo,

        -- MAC COGS: sum OUT-301 export amounts, minus IN-350 export amounts (0 today)
        SUM(cogs_amount) FILTER (
            WHERE movement_direction = 'OUT' AND trans_type = 301
        )
        -- COALESCE the return term: SUM FILTER over zero matching rows is NULL, and
        -- (value - NULL) = NULL would wipe cogs_goods_sapo for every order without a return.
        - COALESCE(SUM(cogs_amount) FILTER (
            WHERE movement_direction = 'IN'  AND trans_type = 350   -- 350 legs carry 0 today (no-op)
        ), 0)                                                       AS cogs_goods_sapo

    FROM {{ ref('std_inventory_movements') }}
    WHERE trans_type IN (301, 350)
      AND quantity_delta != 0
    GROUP BY document_code, sku
),

misa_cogs AS (
    -- MISA TK632 COGS per order × SKU.
    -- cost_account_group = '632' isolates cost-of-goods lines only (excludes 642 selling expenses).
    -- Service-line filter removes DV% / CPBH% product codes that are fees, not physical goods.
    SELECT
        voucher_no                                                  AS order_code,
        product_code                                                AS sku,
        SUM(quantity)                                               AS qty_misa,
        SUM(cogs_amount)                                            AS cogs_goods_misa

    FROM {{ ref('std_misa_sales_lines') }}
    WHERE cost_account_group = '632'
      AND NOT (product_code LIKE 'DV%' OR product_code LIKE 'CPBH%')
    GROUP BY voucher_no, product_code
)

SELECT
    -- Business key (COALESCE for FULL OUTER JOIN — one or both sides may be absent)
    COALESCE(s.order_code, m.order_code)                            AS order_code,
    COALESCE(s.sku,        m.sku)                                   AS sku,

    -- Variant (Sapo-side only; NULL for misa-only rows)
    s.variant_id,

    -- Quantities from each system
    s.qty_sapo,
    m.qty_misa,

    -- COGS from each system (both kept; summing them would double-count)
    s.cogs_goods_sapo,
    m.cogs_goods_misa,

    -- Reconciliation: absolute and relative variance (NULL if either side absent)
    s.cogs_goods_sapo - m.cogs_goods_misa                          AS cogs_variance,
    (s.cogs_goods_sapo - m.cogs_goods_misa)
        / NULLIF(m.cogs_goods_misa, 0)                             AS cogs_variance_pct,

    -- Flag: variance > 10% of MISA value (NULL when either side absent)
    CASE
        WHEN s.cogs_goods_sapo IS NOT NULL AND m.cogs_goods_misa IS NOT NULL AND m.cogs_goods_misa != 0
        THEN ABS((s.cogs_goods_sapo - m.cogs_goods_misa)::DOUBLE / m.cogs_goods_misa) > 0.10
        ELSE NULL
    END                                                             AS is_high_cogs_variance,

    -- Presence flags (used in cogs_source derivation below)
    s.cogs_goods_sapo IS NOT NULL                                   AS has_sapo_cogs,
    m.cogs_goods_misa IS NOT NULL                                   AS has_misa_cogs,

    -- Source classification: 4-way indicating which system(s) have a COGS figure
    CASE
        WHEN s.cogs_goods_sapo IS NOT NULL AND m.cogs_goods_misa IS NOT NULL THEN 'both'
        WHEN s.cogs_goods_sapo IS NOT NULL AND m.cogs_goods_misa IS     NULL THEN 'sapo_mac'
        WHEN s.cogs_goods_sapo IS     NULL AND m.cogs_goods_misa IS NOT NULL THEN 'misa'
        ELSE 'none'
    END                                                             AS cogs_source,

    -- PRIMARY COGS for downstream consumption (var-driven; default = 'sapo_mac').
    -- cogs_goods_misa is reconciliation-only — NEVER use it for totals.
    -- Override: --vars '{"cogs_primary_source": "misa"}' or dbt_project.yml vars section.
    CASE
        WHEN '{{ var("cogs_primary_source", "sapo_mac") }}' = 'sapo_mac'
            THEN s.cogs_goods_sapo
        ELSE m.cogs_goods_misa
    END                                                             AS cogs_goods_primary

FROM sapo_cogs  s
FULL OUTER JOIN misa_cogs m
    ON  s.order_code = m.order_code
    AND s.sku        = m.sku

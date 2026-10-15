{{ config(materialized='view', tags=['monitoring', 'taxonomy']) }}
-- Parity of the classification engine with the legacy SQL of customer_type, one row per customer
-- and domain (docs/architecture/taxonomy-engine.md §4b). Holds VERBATIM copies of the three legacy
-- blocks (dim_customers: customer_type CASE and is_us_gift_recipient; fact_orders: the
-- customer_group blob CASE), with the same CTE and column names so that their sha256 matches
-- scripts/checks/taxonomy_inventory.yaml: when an original changes, check_taxonomy_inventory.py
-- warns for both. Kept until the legacy path is removed, so parity is still measured after the
-- marts switch to the engine. Read by monitor_taxonomy_parity_log; no core/pack model reads it.

WITH us_channel_customers AS (
    SELECT DISTINCT fo.customer_key
    FROM {{ ref('fact_orders') }}  fo
    JOIN {{ ref('dim_channels') }} ch ON fo.channel_key = ch.channel_key
    WHERE ch.channel_name = 'US'
      AND fo.status != 'CANCELLED'
),

joined_data AS (
    SELECT customer_key, customer_group, customer_group_code, customer_group_name
    FROM {{ ref('dim_customers_base') }}
),

legacy_dim AS (
    SELECT
    customer_key,
    CASE
        WHEN customer_group_code LIKE '%WHOLESALE%' OR customer_group_name LIKE '%WHOLESALE%'
            THEN 'WHOLESALE'                                    -- TYPE_WHOLESALE + legacy BANBUON
        WHEN customer_group_code LIKE '%TYPE_PARTNER%' OR customer_group_name LIKE '%TYPE_PARTNER%'
          OR customer_group_code LIKE '%KY_GUI%' OR customer_group_name LIKE '%KY_GUI%'
            THEN 'PARTNER'  -- + Ký Gửi (consignment/ký gửi)
        WHEN customer_group_code LIKE '%TYPE_STAFF%' OR customer_group_name LIKE '%TYPE_STAFF%'
            THEN 'STAFF'
        WHEN customer_group_code LIKE '%TYPE_KOL%' OR customer_group_name LIKE '%TYPE_KOL%'
            THEN 'KOL'
        WHEN customer_group_code LIKE '%TYPE_CROSSBORDER%' OR customer_group_name LIKE '%TYPE_CROSSBORDER%'
          OR customer_group_code LIKE '%CTN00014%' OR customer_group_name LIKE '%CTN00014%'
          OR EXISTS (SELECT 1 FROM us_channel_customers uc WHERE uc.customer_key = joined_data.customer_key)
            THEN 'CROSSBORDER'  -- US giao hàng hộ (người nhận VN); group-tag OR has US-channel order
        ELSE 'RETAIL'  -- Default: TYPE_RETAIL/BANLE, Selly (end-consumers), untagged
    END as legacy_customer_type,
    (customer_group_code LIKE '%TYPE_CROSSBORDER%' OR customer_group_name LIKE '%TYPE_CROSSBORDER%'
      OR customer_group_code LIKE '%CTN00014%' OR customer_group_name LIKE '%CTN00014%'
      OR EXISTS (SELECT 1 FROM us_channel_customers uc WHERE uc.customer_key = joined_data.customer_key)) AS legacy_is_us_gift_recipient
    FROM joined_data
),

customer_type_info AS (
    SELECT
        customer_key,
        CASE
            WHEN customer_group LIKE '%WHOLESALE%' THEN 'WHOLESALE'
            WHEN customer_group LIKE '%TYPE_PARTNER%' OR customer_group LIKE '%KY_GUI%' THEN 'PARTNER'
            WHEN customer_group LIKE '%TYPE_STAFF%' THEN 'STAFF'
            WHEN customer_group LIKE '%TYPE_KOL%' THEN 'KOL'
            WHEN customer_group LIKE '%TYPE_CROSSBORDER%' OR customer_group LIKE '%CTN00014%' THEN 'CROSSBORDER'
            ELSE 'RETAIL'
        END AS legacy_customer_type_blob
    FROM {{ ref('dim_customers_base') }}
),

rule_rows AS (
    SELECT domain, rule_id, label, feature FROM {{ tenant_ref('taxonomy_rule_tenant') }}
    UNION ALL
    SELECT domain, rule_id, label, feature FROM {{ ref('taxonomy_rule_product') }}
),

-- unconditional rules (no feature on any row): the engine's defaults (RETAIL for Fine Japan)
default_rules AS (
    SELECT domain, rule_id
    FROM rule_rows
    GROUP BY domain, rule_id
    HAVING count(label) > 0 AND count(feature) = 0
),

engine AS (
    SELECT 'customer_type' AS domain, customer_key, customer_type, matched__crossborder AS flag,
           rule_id, ruleset_version
    FROM {{ ref('lbl_customer_type') }}
    UNION ALL
    SELECT 'customer_type__group_blob' AS domain, customer_key, customer_type, CAST(NULL AS BOOLEAN) AS flag,
           rule_id, ruleset_version
    FROM {{ ref('lbl_customer_type__group_blob') }}
),

legacy AS (
    SELECT 'customer_type' AS domain, customer_key, legacy_customer_type AS customer_type,
           legacy_is_us_gift_recipient AS flag
    FROM legacy_dim
    UNION ALL
    SELECT 'customer_type__group_blob' AS domain, customer_key, legacy_customer_type_blob AS customer_type,
           CAST(NULL AS BOOLEAN) AS flag
    FROM customer_type_info
)

SELECT
    COALESCE(e.domain, l.domain) AS domain,
    COALESCE(e.customer_key, l.customer_key) AS customer_key,
    e.customer_type AS engine_label,
    l.customer_type AS legacy_label,
    e.flag AS engine_flag,
    l.flag AS legacy_flag,
    e.rule_id AS engine_rule_id,
    e.ruleset_version,
    e.customer_type IS DISTINCT FROM l.customer_type AS is_label_diff,
    e.flag IS DISTINCT FROM l.flag AS is_flag_diff,
    (e.customer_type IS DISTINCT FROM l.customer_type) OR (e.flag IS DISTINCT FROM l.flag) AS is_diff,
    -- the legacy blocks give RETAIL only in their ELSE branch
    l.customer_type = 'RETAIL' AS is_legacy_else,
    dr.rule_id IS NOT NULL AS is_engine_default
FROM engine e
FULL JOIN legacy l ON l.domain = e.domain AND l.customer_key = e.customer_key
LEFT JOIN default_rules dr ON dr.domain = e.domain AND dr.rule_id = e.rule_id

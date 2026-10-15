{{ config(
    materialized='table',
    tags=['monitoring', 'capabilities']
) }}

{#-
  What data this deployment has, per capability, at three levels (report-product-design §4 ②):
    declared  - an enabled connector (var enabled_connectors) declares it (seeds/capabilities/connector_capabilities.csv)
    needed    - core or an enabled pack (var enabled_packs) requires it (seeds/capabilities/capability_catalog.csv)
    observed  - the probe relation below has rows
  Grain: one row per capability of the catalog. No build timestamp: the result depends only on the
  data, the seeds and the vars. Table in the warehouse, not on serving.

  Probes read only connector and cdm models (never a pack: a pack can be off). One entry per
  capability of the catalog; a capability without probe fails the build (checked at execute).
    model: relation to count, where: optional filter, date: optional expression for last_observed_date
  Design and status meanings: transformation/seeds/capabilities/README.md.
-#}
{%- set probes = {
    'orders':            {'model': 'std_orders',                    'date': 'created_at'},
    'order_items':       {'model': 'std_order_items'},
    'customers':         {'model': 'std_customers',                 'date': 'created_at'},
    'products':          {'model': 'std_variants'},
    'returns':           {'model': 'std_order_returns',             'date': 'created_at'},
    'payments':          {'model': 'std_payments',                  'date': 'paid_at'},
    'fulfillments':      {'model': 'std_fulfillments',              'date': 'created_at'},
    'staff':             {'model': 'std_accounts'},
    'inventory':         {'model': 'std_inventory_movements',       'date': 'issued_date_key'},
    'cogs_moving_avg':   {'model': 'std_inventory_movements',       'date': 'issued_date_key', 'where': 'cogs_amount IS NOT NULL'},
    'purchase_price':    {'model': 'std_variant_prices',            'where': "price_list_code = 'GIANHAP'"},
    'marketplace_fees':  {'model': 'stg_shopee_order_service_fees'},
    'platform_discount': {'model': 'stg_shopee_order_revenue',      'date': 'order_placed_at', 'where': 'product_subsidy_from_shopee IS NOT NULL'},
    'gl':                {'model': 'std_misa_account_ledger',       'date': 'period_month'},
    'cogs_accounting':   {'model': 'std_misa_sales_lines',          'date': 'posting_date', 'where': 'cogs_amount IS NOT NULL'},
    'targets':           {'model': 'std_targets',                   'date': 'cycle_start_date'},
    'marketing_spend':   {'model': 'std_marketing_spend'},
    'teams':             {'model': 'std_teams'},
    'hug_scans':         {'model': 'src_hug_scan'},
} -%}

{%- if execute -%}
  {%- set catalog = run_query("SELECT DISTINCT capability FROM " ~ ref('capability_catalog')).columns[0].values() -%}
  {%- set missing = catalog | reject('in', probes) | list -%}
  {%- if missing -%}
    {{ exceptions.raise_compiler_error("mart_capabilities: no probe for capabilities " ~ missing | join(', ') ~ " of capability_catalog") }}
  {%- endif -%}
{%- endif -%}

{%- set enabled_connectors = var('enabled_connectors', []) -%}
{%- set enabled_packs = var('enabled_packs', []) %}

WITH observed AS (
    {%- for capability, p in probes.items() %}
    SELECT
        '{{ capability }}'                                    AS capability,
        COUNT(*)                                              AS observed_rows,
        {{ 'MAX(' ~ p['date'] ~ ')::DATE' if p.get('date') else 'CAST(NULL AS DATE)' }} AS last_observed_date
    FROM {{ ref(p['model']) }}
    {%- if p.get('where') %}
    WHERE {{ p['where'] }}
    {%- endif %}
    {{ 'UNION ALL' if not loop.last }}
    {%- endfor %}
),

catalog AS (
    SELECT
        capability,
        STRING_AGG(required_by, ',' ORDER BY required_by)     AS required_by,
        BOOL_OR(required_by = 'core'
            {%- for p in enabled_packs %} OR required_by = '{{ p }}'{% endfor %}) AS is_pack_enabled
    FROM {{ ref('capability_catalog') }}
    GROUP BY capability
),

declared AS (
    SELECT
        capability,
        STRING_AGG(connector_id, ',' ORDER BY connector_id)   AS declared_by
    FROM {{ ref('connector_capabilities') }}
    WHERE connector_id IN ({% for c in enabled_connectors %}'{{ c }}'{{ ', ' if not loop.last }}{% else %}NULL{% endfor %})
    GROUP BY capability
)

SELECT
    c.capability,
    c.required_by,
    d.declared_by,
    (d.declared_by IS NOT NULL)                               AS is_declared,
    c.is_pack_enabled,
    o.observed_rows,
    o.last_observed_date,
    (o.observed_rows > 0)                                     AS is_observed,
    CASE
        WHEN c.is_pack_enabled AND d.declared_by IS NOT NULL AND o.observed_rows > 0 THEN 'OK'
        WHEN c.is_pack_enabled AND d.declared_by IS NOT NULL                         THEN 'DECLARED_NO_DATA'
        WHEN c.is_pack_enabled                                                       THEN 'PACK_ON_NO_SOURCE'
        WHEN d.declared_by IS NULL AND o.observed_rows > 0                           THEN 'DATA_NOT_DECLARED'
        ELSE 'NOT_NEEDED'
    END                                                       AS status
FROM catalog c
LEFT JOIN declared d ON d.capability = c.capability
LEFT JOIN observed o ON o.capability = c.capability
ORDER BY c.capability

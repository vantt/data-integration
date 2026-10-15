{#
  taxonomy_rules_ctes(d, tenant_rules): CTEs of the effective rules of domain `d`
  (a dict from taxonomy_domain). Emitted inside a WITH clause, ends without a trailing comma.

    rule_rows   every row of both layers for the domain, with source_layer ('tenant' | 'product')
                and layer_rank (tenant 0, product 1: the tenant layer is evaluated first)
    rules       one row per effective rule: definition rows (label set) whose rule_id has no
                enabled = false row in any layer of the domain
    conditions  the condition rows (feature set) of the effective rules
    ruleset     ruleset_version: md5 of every row of the domain in both layers, disable rows
                included, sorted (one value per domain; changes when any rule row changes)

  `tenant_rules` is the relation tenant_ref('taxonomy_rule_tenant'), passed by the model so that
  the model's own SQL calls tenant_ref literally (check_boundaries.py rule dbt-seed).
#}
{% macro taxonomy_rules_ctes(d, tenant_rules) %}
rule_rows AS (
    SELECT 'tenant' AS source_layer, 0 AS layer_rank,
           rule_id, priority, label, feature, op, value, value_to, enabled
    FROM {{ tenant_rules }}
    WHERE domain = {{ taxonomy_literal(d.name) }}
    UNION ALL
    SELECT 'product' AS source_layer, 1 AS layer_rank,
           rule_id, priority, label, feature, op, value, value_to, enabled
    FROM {{ ref('taxonomy_rule_product') }}
    WHERE domain = {{ taxonomy_literal(d.name) }}
),
rules AS (
    SELECT DISTINCT source_layer, layer_rank, rule_id, priority, label
    FROM rule_rows
    WHERE label IS NOT NULL
      AND rule_id NOT IN (
          SELECT rule_id FROM rule_rows WHERE enabled = FALSE AND rule_id IS NOT NULL
      )
),
conditions AS (
    SELECT rr.rule_id, rr.feature, rr.op, rr.value, rr.value_to
    FROM rule_rows rr
    JOIN rules r ON r.source_layer = rr.source_layer AND r.rule_id = rr.rule_id
    WHERE rr.feature IS NOT NULL
),
ruleset AS (
    SELECT md5(COALESCE(string_agg(row_text, chr(30) ORDER BY row_text), '')) AS ruleset_version
    FROM (
        SELECT concat_ws(chr(31), source_layer, COALESCE(rule_id, ''),
                         COALESCE(CAST(priority AS VARCHAR), ''), COALESCE(label, ''),
                         COALESCE(feature, ''), COALESCE(op, ''), COALESCE(value, ''),
                         COALESCE(value_to, ''), COALESCE(CAST(enabled AS VARCHAR), '')) AS row_text
        FROM rule_rows
    ) t
)
{% endmacro %}

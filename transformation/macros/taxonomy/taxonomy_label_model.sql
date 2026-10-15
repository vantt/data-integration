{#
  taxonomy_label_model(domain, tenant_rules, labels): the whole body of model lbl_<domain> of the
  classification engine. Semantics: docs/architecture/taxonomy-engine.md §4b.

    {{ taxonomy_label_model('customer_type', tenant_ref('taxonomy_rule_tenant'), tenant_ref('taxonomy_label')) }}

  The model passes both tenant seeds so that its own SQL calls tenant_ref literally
  (check_boundaries.py rules dbt-seed, tenant-seed-contract); the product layer is read here
  with ref('taxonomy_rule_product').

  1. Subjects: the keys of the first feature model of the domain; the other feature models are
     LEFT JOINed on the shared key. A list feature of a joined model is [] (not NULL) for a
     subject missing from that model: "has no row there" means "the list is empty", like the
     EXISTS it replaces.
  2. Each condition row evaluates to TRUE / FALSE / NULL like its SQL predicate
     (taxonomy_condition). 3. A rule is FALSE if one condition is FALSE, else NULL if one is
     NULL, else TRUE (three-valued AND, not bool_and); a rule without condition is TRUE.
  4. Effective rules and order: taxonomy_rules_ctes (tenant layer, then priority, then rule_id).
  5. Only TRUE counts as a match. FIRST: first match. UNIQUE: same, plus n_hits. COLLECT: one
     row per matched label, rule_id of the first matching rule of that label.
  6. A NULL required feature gives UNKNOWN without evaluating rules; no match gives UNMAPPED
     (rule_id NULL). Both are their own <label>_std.
     A product-layer rule assigns a canonical code (taxonomy_canonical), its own <label>_std;
     a tenant-layer rule assigns a tenant label, anchored through taxonomy_label.
  7. matched__<x> per label of matched_flags: TRUE if a rule of label x is TRUE, else NULL if
     one is NULL, else FALSE, whatever the priority; NULL for an UNKNOWN subject.
  8. Columns: <key>, <label column>, <label column>_std, rule_id, source_layer,
     ruleset_version, matched__*, n_hits (UNIQUE only). The label column is the domain name
     before '__'; <label column>_std comes from `labels` (taxonomy_label) for the label_set, and
     is UNMAPPED for a tenant label not anchored there (a product-rule label is
     already canonical and is its own <label>_std).
#}
{% macro taxonomy_label_model(domain, tenant_rules, labels) %}
{%- set d = taxonomy_domain(domain) -%}
{%- set k = d.key -%}
{%- set col = d.label_column -%}
{%- set aliases = {} -%}
{%- for fm in d.feature_models -%}{%- do aliases.update({fm: 'f' ~ loop.index0}) -%}{%- endfor -%}
WITH subjects AS (
    SELECT
        f0.{{ k }},
        {%- for c, typ in d.columns.items() %}
        {%- set a = aliases[d.column_model[c]] %}
        {%- if a != 'f0' and taxonomy_type_family(typ) == 'list' %}
        COALESCE({{ a }}.{{ c }}, CAST([] AS {{ typ }})) AS {{ c }},
        {%- else %}
        {{ a }}.{{ c }},
        {%- endif %}
        {%- endfor %}
        {% if d.required_features | length > 0 -%}
        ({% for c in d.required_features %}{{ aliases[d.column_model[c]] }}.{{ c }} IS NULL{% if not loop.last %} OR {% endif %}{% endfor %})
        {%- else -%}
        FALSE
        {%- endif %} AS tx_unknown
    FROM {{ ref(d.feature_models[0]) }} f0
    {%- for fm in d.feature_models[1:] %}
    LEFT JOIN {{ ref(fm) }} {{ aliases[fm] }} ON {{ aliases[fm] }}.{{ k }} = f0.{{ k }}
    {%- endfor %}
),
{{ taxonomy_rules_ctes(d, tenant_rules) }},
cond_eval AS (
    SELECT s.{{ k }}, c.rule_id,
        {{ taxonomy_condition(d, 's', 'c') | indent(8) }} AS ok
    FROM subjects s
    CROSS JOIN conditions c
    WHERE NOT s.tx_unknown
),
cond_agg AS (
    SELECT {{ k }}, rule_id,
        count_if(ok = FALSE) AS n_false,
        count_if(ok IS NULL) AS n_null
    FROM cond_eval
    GROUP BY {{ k }}, rule_id
),
rule_eval AS (
    -- three-valued AND over the conditions of each rule
    SELECT s.{{ k }}, r.source_layer, r.layer_rank, r.priority, r.rule_id, r.label,
        CASE WHEN COALESCE(a.n_false, 0) > 0 THEN FALSE
             WHEN COALESCE(a.n_null, 0) > 0 THEN NULL
             ELSE TRUE END AS hit
    FROM subjects s
    CROSS JOIN rules r
    LEFT JOIN cond_agg a ON a.{{ k }} = s.{{ k }} AND a.rule_id = r.rule_id
    WHERE NOT s.tx_unknown
),
{%- if d.hit_policy == 'COLLECT' %}
hits AS (
    SELECT {{ k }}, label, rule_id, source_layer
    FROM rule_eval
    WHERE hit
    QUALIFY row_number() OVER (PARTITION BY {{ k }}, label ORDER BY layer_rank, priority, rule_id) = 1
),
{%- else %}
hits AS (
    SELECT {{ k }}, label, rule_id, source_layer,
        count(*) OVER (PARTITION BY {{ k }}) AS n_hits
    FROM rule_eval
    WHERE hit
    QUALIFY row_number() OVER (PARTITION BY {{ k }} ORDER BY layer_rank, priority, rule_id) = 1
),
{%- endif %}
flags AS (
    SELECT s.{{ k }}
        {%- for x in d.matched_flags %},
        CASE WHEN bool_or(e.hit) FILTER (WHERE e.label = {{ taxonomy_literal(x) }}) THEN TRUE
             WHEN count(*) FILTER (WHERE e.label = {{ taxonomy_literal(x) }} AND e.hit IS NULL) > 0 THEN NULL
             ELSE FALSE END AS {{ taxonomy_flag_column(x) }}
        {%- endfor %}
    FROM subjects s
    LEFT JOIN rule_eval e ON e.{{ k }} = s.{{ k }}
    GROUP BY s.{{ k }}
),
resolved AS (
    SELECT s.{{ k }}, s.tx_unknown,
        COALESCE(h.label, IF(s.tx_unknown, 'UNKNOWN', 'UNMAPPED')) AS label_value,
        h.rule_id,
        h.source_layer
        {%- if d.hit_policy == 'UNIQUE' %},
        COALESCE(h.n_hits, 0) AS n_hits
        {%- endif %}
    FROM subjects s
    LEFT JOIN hits h ON h.{{ k }} = s.{{ k }}
),
anchored AS (
    SELECT r.*,
        CASE WHEN r.label_value IN ('UNMAPPED', 'UNKNOWN') THEN r.label_value
             -- a product rule assigns a canonical code: it is its own canonical code
             WHEN r.source_layer = 'product' THEN r.label_value
             ELSE COALESCE(l.label_std, 'UNMAPPED') END AS label_std_value
    FROM resolved r
    LEFT JOIN (
        SELECT label, label_std
        FROM {{ labels }}
        WHERE domain = {{ taxonomy_literal(d.label_set) }}
    ) l ON l.label = r.label_value
)
SELECT
    a.{{ k }},
    a.label_value AS {{ col }},
    a.label_std_value AS {{ col }}_std,
    a.rule_id,
    a.source_layer,
    rs.ruleset_version
    {%- for x in d.matched_flags %},
    IF(a.tx_unknown, NULL, fl.{{ taxonomy_flag_column(x) }}) AS {{ taxonomy_flag_column(x) }}
    {%- endfor %}
    {%- if d.hit_policy == 'UNIQUE' %},
    a.n_hits
    {%- endif %}
FROM anchored a
LEFT JOIN flags fl ON fl.{{ k }} = a.{{ k }}
CROSS JOIN ruleset rs
{% endmacro %}

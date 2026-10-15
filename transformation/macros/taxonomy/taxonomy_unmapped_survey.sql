{#
  taxonomy_unmapped_survey(tenant_rules): body of monitor_taxonomy_unmapped. For every domain of
  vars.taxonomy with a `survey` (selftest domains excluded): the raw values of its survey features
  for the subjects that no specific rule classified, i.e. labelled UNMAPPED or UNKNOWN or given by
  an unconditional (default) rule, with the number of subjects and their order count and revenue
  from survey.metrics_model, sorted by revenue. The onboarding list "what is not classified yet and
  how much it weighs" (docs/architecture/taxonomy-engine.md §4b).

  Columns: domain, label, reason (unmapped | unknown | default_rule), raw_values (JSON object of
  the survey features), n_entities, order_count, revenue.
  `tenant_rules` is tenant_ref('taxonomy_rule_tenant'), passed by the model (check_boundaries.py).
#}
{% macro taxonomy_unmapped_survey(tenant_rules) %}
{%- set domains = (var('taxonomy', {}) or {}).get('domains') or {} -%}
{%- set names = [] -%}
{%- for name in taxonomy_domain_names() -%}
  {%- if (domains[name] or {}).get('survey') -%}{%- do names.append(name) -%}{%- endif -%}
{%- endfor -%}
{%- if names | length == 0 %}
SELECT
    CAST(NULL AS VARCHAR) AS domain,
    CAST(NULL AS VARCHAR) AS label,
    CAST(NULL AS VARCHAR) AS reason,
    CAST(NULL AS VARCHAR) AS raw_values,
    CAST(NULL AS BIGINT) AS n_entities,
    CAST(NULL AS DOUBLE) AS order_count,
    CAST(NULL AS DOUBLE) AS revenue
WHERE FALSE
{%- else %}
WITH rule_rows AS (
    SELECT domain, rule_id, label, feature FROM {{ tenant_rules }}
    UNION ALL
    SELECT domain, rule_id, label, feature FROM {{ ref('taxonomy_rule_product') }}
),
default_rules AS (
    SELECT domain, rule_id
    FROM rule_rows
    GROUP BY domain, rule_id
    HAVING count(label) > 0 AND count(feature) = 0
),
{%- for name in names %}
{%- set d = taxonomy_domain(name) %}
{%- set survey = domains[name].get('survey') %}
{%- set feats = survey.get('features') or [] %}
{%- set models = [] %}
{%- for c in feats %}
  {%- if c not in d.columns -%}
    {{ exceptions.raise_compiler_error("taxonomy: survey feature '" ~ c ~ "' is not a feature of domain '" ~ name ~ "'") }}
  {%- endif -%}
  {%- if d.column_model[c] not in models %}{% do models.append(d.column_model[c]) %}{% endif %}
{%- endfor %}
survey_{{ loop.index }} AS (
    SELECT
        {{ taxonomy_literal(name) }} AS domain,
        l.{{ d.label_column }} AS label,
        IF(l.{{ d.label_column }} IN ('UNMAPPED', 'UNKNOWN'), lower(l.{{ d.label_column }}), 'default_rule') AS reason,
        {% if feats | length > 0 -%}
        CAST(to_json(struct_pack(
            {%- for c in feats %}{{ c }} := sv{{ models.index(d.column_model[c]) }}.{{ c }}{% if not loop.last %}, {% endif %}{% endfor -%}
        )) AS VARCHAR)
        {%- else -%}
        CAST(NULL AS VARCHAR)
        {%- endif %} AS raw_values,
        count(*) AS n_entities,
        {% if survey.get('metrics_model') -%}
        CAST(sum(m.{{ survey.get('order_count') }}) AS DOUBLE) AS order_count,
        CAST(sum(m.{{ survey.get('revenue') }}) AS DOUBLE) AS revenue
        {%- else -%}
        CAST(NULL AS DOUBLE) AS order_count,
        CAST(NULL AS DOUBLE) AS revenue
        {%- endif %}
    FROM {{ ref('lbl_' ~ name) }} l
    {%- for fm in models %}
    LEFT JOIN {{ ref(fm) }} sv{{ loop.index0 }} ON sv{{ loop.index0 }}.{{ d.key }} = l.{{ d.key }}
    {%- endfor %}
    {%- if survey.get('metrics_model') %}
    LEFT JOIN {{ ref(survey.get('metrics_model')) }} m ON m.{{ d.key }} = l.{{ d.key }}
    {%- endif %}
    LEFT JOIN default_rules dr ON dr.domain = {{ taxonomy_literal(name) }} AND dr.rule_id = l.rule_id
    WHERE l.{{ d.label_column }} IN ('UNMAPPED', 'UNKNOWN') OR dr.rule_id IS NOT NULL
    GROUP BY ALL
){% if not loop.last %},{% endif %}
{%- endfor %}
{%- for name in names %}
SELECT * FROM survey_{{ loop.index }}
{%- if not loop.last %}
UNION ALL
{%- endif %}
{%- endfor %}
ORDER BY revenue DESC NULLS LAST, n_entities DESC
{%- endif %}
{% endmacro %}

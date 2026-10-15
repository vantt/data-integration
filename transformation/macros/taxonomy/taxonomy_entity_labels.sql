{#
  taxonomy_entity_labels(): body of the entity_labels view, the long table of every label the
  engine produces: UNION ALL of lbl_<domain> for every domain of vars.taxonomy that is not a
  selftest domain, columns subject, entity_id, domain, label, label_std, rule_id, source_layer,
  ruleset_version. For monitoring and explanation only: no mart may ref it (it depends on every
  lbl_*). With no domain it is an empty relation with the same columns.
#}
{% macro taxonomy_entity_labels() %}
{%- set names = taxonomy_domain_names() -%}
{%- if names | length == 0 %}
SELECT
    CAST(NULL AS VARCHAR) AS subject,
    CAST(NULL AS VARCHAR) AS entity_id,
    CAST(NULL AS VARCHAR) AS domain,
    CAST(NULL AS VARCHAR) AS label,
    CAST(NULL AS VARCHAR) AS label_std,
    CAST(NULL AS VARCHAR) AS rule_id,
    CAST(NULL AS VARCHAR) AS source_layer,
    CAST(NULL AS VARCHAR) AS ruleset_version
WHERE FALSE
{%- else %}
{%- for name in names %}
{%- set d = taxonomy_domain(name) %}
SELECT
    {{ taxonomy_literal(d.subject) }} AS subject,
    CAST({{ d.key }} AS VARCHAR) AS entity_id,
    {{ taxonomy_literal(d.name) }} AS domain,
    {{ d.label_column }} AS label,
    {{ d.label_column }}_std AS label_std,
    rule_id,
    source_layer,
    ruleset_version
FROM {{ ref('lbl_' ~ name) }}
{%- if not loop.last %}
UNION ALL
{%- endif %}
{%- endfor %}
{%- endif %}
{% endmacro %}

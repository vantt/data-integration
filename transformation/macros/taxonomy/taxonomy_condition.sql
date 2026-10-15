{#
  taxonomy_condition(d, s='s', c='c'): boolean expression evaluating condition row `c`
  (columns feature, op, value, value_to) on subject row `s`, TRUE / FALSE / NULL exactly like the
  SQL predicate it stands for (docs/architecture/taxonomy-engine.md §4b).

  One WHEN branch per (feature column of the domain, operator allowed for its type); any other
  (feature, op) pair raises a DuckDB error at run time instead of evaluating to NULL silently.
  `value` / `value_to` are cast to the declared type of the feature.
#}
{% macro taxonomy_op_sql(op, f, typ, c) %}
  {%- set t = typ | string | trim -%}
  {%- if op == 'like' -%}
    ({{ f }} LIKE {{ c }}.value)
  {%- elif op == 'eq' -%}
    ({{ f }} = CAST({{ c }}.value AS {{ t }}))
  {%- elif op == 'in' -%}
    (CASE WHEN {{ f }} IS NULL THEN NULL
          ELSE list_contains(CAST(string_split({{ c }}.value, '|') AS {{ t }}[]), {{ f }}) END)
  {%- elif op == 'not_in' -%}
    (CASE WHEN {{ f }} IS NULL THEN NULL
          ELSE NOT list_contains(CAST(string_split({{ c }}.value, '|') AS {{ t }}[]), {{ f }}) END)
  {%- elif op == 'between' -%}
    (({{ c }}.value IS NULL OR {{ f }} >= CAST({{ c }}.value AS {{ t }}))
     AND ({{ c }}.value_to IS NULL OR {{ f }} < CAST({{ c }}.value_to AS {{ t }})))
  {%- elif op == 'starts_with' -%}
    starts_with({{ f }}, {{ c }}.value)
  {%- elif op == 'contains' -%}
    contains({{ f }}, {{ c }}.value)
  {%- elif op == 'regex' -%}
    regexp_matches({{ f }}, {{ c }}.value)
  {%- elif op == 'is_null' -%}
    (CASE WHEN lower({{ c }}.value) = 'false' THEN {{ f }} IS NOT NULL ELSE {{ f }} IS NULL END)
  {%- elif op == 'has' -%}
    (CASE WHEN {{ f }} IS NULL THEN NULL
          ELSE list_contains({{ f }}, CAST({{ c }}.value AS {{ t[:-2] }})) END)
  {%- else -%}
    {{ exceptions.raise_compiler_error("taxonomy: unknown operator '" ~ op ~ "'") }}
  {%- endif -%}
{% endmacro %}

{% macro taxonomy_condition(d, s='s', c='c') %}
  {%- if d.columns | length == 0 -%}
    {{ exceptions.raise_compiler_error("taxonomy: domain '" ~ d.name ~ "' has no feature column") }}
  {%- endif -%}
CASE
  {%- for col, typ in d.columns.items() %}
    {%- for op in taxonomy_ops(taxonomy_type_family(typ)) %}
    WHEN {{ c }}.feature = {{ taxonomy_literal(col) }} AND {{ c }}.op = {{ taxonomy_literal(op) }}
        THEN {{ taxonomy_op_sql(op, s ~ '.' ~ col, typ, c) }}
    {%- endfor %}
  {%- endfor %}
    ELSE error('taxonomy: domain {{ d.name }}: feature ' || COALESCE({{ c }}.feature, 'NULL')
               || ' with op ' || COALESCE({{ c }}.op, 'NULL') || ' is not allowed')
END
{%- endmacro %}

{#
  Registry of the classification engine: vars.taxonomy in dbt_project.yml (features, domains),
  read at compile time. Schema: docs/architecture/taxonomy-engine.md §4b.
  scripts/checks/check_taxonomy_rules.py checks the same file before load; the compiler errors
  here catch what reaches dbt anyway.
#}

{#- Family of a DuckDB type name: string | number | temporal | boolean | list, or none. -#}
{% macro taxonomy_type_family(duckdb_type) %}
  {%- set t = (duckdb_type | string | trim | upper) -%}
  {%- if t.endswith('[]') -%}{{ return('list') }}
  {%- elif t in ['TINYINT', 'SMALLINT', 'INTEGER', 'INT', 'BIGINT', 'HUGEINT', 'UTINYINT', 'USMALLINT',
                 'UINTEGER', 'UBIGINT', 'DOUBLE', 'FLOAT', 'REAL']
         or t.startswith('DECIMAL') or t.startswith('NUMERIC') -%}{{ return('number') }}
  {%- elif t in ['DATE', 'TIMESTAMP', 'TIMESTAMPTZ', 'TIMESTAMP WITH TIME ZONE'] -%}{{ return('temporal') }}
  {%- elif t == 'BOOLEAN' -%}{{ return('boolean') }}
  {%- elif t in ['VARCHAR', 'TEXT', 'STRING'] -%}{{ return('string') }}
  {%- else -%}{{ return(none) }}
  {%- endif -%}
{% endmacro %}

{#- Operators allowed per type family (same table as check_taxonomy_rules.py OPS_BY_FAMILY). -#}
{% macro taxonomy_ops(family) %}
  {%- set ops = {
      'string': ['like', 'eq', 'in', 'not_in', 'starts_with', 'contains', 'regex', 'is_null'],
      'number': ['eq', 'in', 'not_in', 'between', 'is_null'],
      'temporal': ['eq', 'in', 'not_in', 'between', 'is_null'],
      'boolean': ['eq', 'is_null'],
      'list': ['has', 'is_null'],
  } -%}
  {{ return(ops.get(family, [])) }}
{% endmacro %}

{#- All non-selftest domains, sorted. -#}
{% macro taxonomy_domain_names(include_selftest=false) %}
  {%- set domains = (var('taxonomy', {}) or {}).get('domains') or {} -%}
  {%- set out = [] -%}
  {%- for name in domains | sort -%}
    {%- if include_selftest or not (domains[name] or {}).get('selftest', false) -%}{%- do out.append(name) -%}{%- endif -%}
  {%- endfor -%}
  {{ return(out) }}
{% endmacro %}

{#-
  taxonomy_domain(domain) -> dict:
    name, subject, cardinality, hit_policy, label_set, selftest,
    feature_models  [model, ...]   (first one = full set of subjects)
    key             key column shared by the feature models
    columns         {feature column: DuckDB type} over all feature models of the domain
    column_model    {feature column: feature model}
    required_features, matched_flags
    label_column    output column name: the domain name before '__' (customer_type__group_blob -> customer_type)
-#}
{% macro taxonomy_domain(domain) %}
  {%- set reg = var('taxonomy', {}) or {} -%}
  {%- set domains = reg.get('domains') or {} -%}
  {%- set features = reg.get('features') or {} -%}
  {%- if domain not in domains -%}
    {{ exceptions.raise_compiler_error("taxonomy: domain '" ~ domain ~ "' is not declared in vars.taxonomy.domains (dbt_project.yml)") }}
  {%- endif -%}
  {%- set spec = domains[domain] or {} -%}
  {%- set hit = spec.get('hit_policy') -%}
  {%- set card = spec.get('cardinality') -%}
  {%- if hit not in ['FIRST', 'UNIQUE', 'COLLECT'] -%}
    {{ exceptions.raise_compiler_error("taxonomy: domain '" ~ domain ~ "' has hit_policy '" ~ hit ~ "' (FIRST, UNIQUE or COLLECT)") }}
  {%- endif -%}
  {%- if (hit == 'COLLECT') != (card == 'multi') or card not in ['single', 'multi'] -%}
    {{ exceptions.raise_compiler_error("taxonomy: domain '" ~ domain ~ "': COLLECT needs cardinality multi, FIRST/UNIQUE single") }}
  {%- endif -%}
  {%- if not spec.get('label_set') -%}
    {{ exceptions.raise_compiler_error("taxonomy: domain '" ~ domain ~ "' has no label_set") }}
  {%- endif -%}
  {%- set fmodels = spec.get('features') or [] -%}
  {%- if fmodels | length == 0 -%}
    {{ exceptions.raise_compiler_error("taxonomy: domain '" ~ domain ~ "' declares no feature model") }}
  {%- endif -%}
  {%- set columns = {} -%}
  {%- set column_model = {} -%}
  {%- set key = (features.get(fmodels[0]) or {}).get('key') -%}
  {%- for fm in fmodels -%}
    {%- if fm not in features -%}
      {{ exceptions.raise_compiler_error("taxonomy: domain '" ~ domain ~ "' uses feature model '" ~ fm ~ "' not declared in vars.taxonomy.features") }}
    {%- endif -%}
    {%- set f = features[fm] -%}
    {%- if f.get('key') != key or not key -%}
      {{ exceptions.raise_compiler_error("taxonomy: feature models of domain '" ~ domain ~ "' must share one key column") }}
    {%- endif -%}
    {%- for col, typ in (f.get('columns') or {}).items() -%}
      {%- if col in columns -%}
        {{ exceptions.raise_compiler_error("taxonomy: feature column '" ~ col ~ "' declared twice for domain '" ~ domain ~ "'") }}
      {%- endif -%}
      {%- if taxonomy_type_family(typ) is none -%}
        {{ exceptions.raise_compiler_error("taxonomy: feature column '" ~ col ~ "' has unsupported type '" ~ typ ~ "'") }}
      {%- endif -%}
      {%- do columns.update({col: typ}) -%}
      {%- do column_model.update({col: fm}) -%}
    {%- endfor -%}
  {%- endfor -%}
  {%- for col in spec.get('required_features') or [] -%}
    {%- if col not in columns -%}
      {{ exceptions.raise_compiler_error("taxonomy: required feature '" ~ col ~ "' is not a feature of domain '" ~ domain ~ "'") }}
    {%- endif -%}
  {%- endfor -%}
  {{ return({
      'name': domain,
      'subject': spec.get('subject'),
      'cardinality': card,
      'hit_policy': hit,
      'label_set': spec.get('label_set'),
      'selftest': spec.get('selftest', false),
      'feature_models': fmodels,
      'key': key,
      'columns': columns,
      'column_model': column_model,
      'required_features': spec.get('required_features') or [],
      'matched_flags': spec.get('matched_flags') or [],
      'label_column': domain.split('__')[0],
  }) }}
{% endmacro %}

{#- SQL string literal. -#}
{% macro taxonomy_literal(value) %}
  {{- return("'" ~ (value | string | replace("'", "''")) ~ "'") -}}
{% endmacro %}

{#- Column name matched__<label> for a matched flag (lower case, non-alphanumerics -> _). -#}
{% macro taxonomy_flag_column(label) %}
  {{- return('matched__' ~ modules.re.sub('[^a-z0-9]+', '_', label | lower)) -}}
{% endmacro %}

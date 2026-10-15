{#
  tenant_ref(seed): the only way core reads a tenant seed (docs/architecture/modules.md §10).

  - var('tenant') set (Fine Japan: 'fine_japan'): ref('<seed>'), the tenant's own
    seeds/tenants/<tenant>/<seed>.csv. Compiles to exactly what ref('<seed>') did.
  - var('tenant') empty: ref('<seed>__default'), the core default
    seeds/defaults/<seed>__default.csv: same columns and types, 0 rows.

  Write it literally: tenant_ref('<seed>'). check_boundaries.py accepts a core -> tenant seed edge
  only for that spelling and checks that the default and the tenant's seed have the same columns
  (rule tenant-seed-contract).
#}
{% macro tenant_ref(seed) %}
  {%- if var('tenant', '') -%}
    {{ return(ref(seed)) }}
  {%- else -%}
    {{ return(ref(seed ~ '__default')) }}
  {%- endif -%}
{% endmacro %}

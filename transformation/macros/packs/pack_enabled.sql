{#
  Pack switch (docs/architecture/modules.md §8).

  pack_ids()          every pack that has a folder under models/packs/ (enabled or not). Kept equal
                      to that folder list by check_boundaries.py rule `module-config`.
  pack_enabled(pack)  true when `pack` is in the dbt variable `enabled_packs`. An id that is not a
                      pack folder is a compilation error, so a typo cannot silently turn a hook off.

  Decisions use var() only (no run_query, no graph), so lineage is static and a change of
  --vars re-parses the project.
#}
{% macro pack_ids() %}
  {{ return(['crm', 'hug', 'finance', 'sales_playbook', 'marketplace', 'facebook_ads', 'facebook_messenger']) }}
{% endmacro %}

{% macro pack_enabled(pack) %}
  {%- if pack not in pack_ids() -%}
    {{ exceptions.raise_compiler_error("pack_enabled: unknown pack '" ~ pack ~ "' (known: " ~ pack_ids() | join(', ') ~ ")") }}
  {%- endif -%}
  {{ return(pack in var('enabled_packs', [])) }}
{% endmacro %}

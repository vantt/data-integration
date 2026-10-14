{#
  pack_ref(pack, model, columns=none): the only way core reads a pack model.

  - Pack enabled: returns ref(model), so the compiled SQL is exactly what ref() produced and
    lineage keeps the core -> pack edge.
  - Pack disabled: returns `(SELECT CAST(NULL AS <type>) AS <column>, ... WHERE FALSE)`, an empty
    relation with the contract's columns and types. ref() is not called, so dbt records no edge
    and the disabled pack model is not needed.

  `model` must have an entry in pack_contracts() whose pack is `pack`. `columns` (optional) is a
  subset of the contract, with the same types, for a core model that reads only some columns;
  omitted, the whole contract is used. Write the call literally as
  pack_ref('<pack>', '<model>'...) — check_boundaries.py accepts a core -> pack edge only for that
  form (transformation/AGENTS.md).
#}
{% macro pack_ref(pack, model, columns=none) %}
  {%- set contracts = pack_contracts() -%}
  {%- if model not in contracts -%}
    {{ exceptions.raise_compiler_error("pack_ref: no contract for '" ~ model ~ "' in pack_contracts()") }}
  {%- endif -%}
  {%- set contract = contracts[model] -%}
  {%- if contract['pack'] != pack -%}
    {{ exceptions.raise_compiler_error("pack_ref: '" ~ model ~ "' belongs to pack '" ~ contract['pack'] ~ "' in pack_contracts(), not '" ~ pack ~ "'") }}
  {%- endif -%}
  {%- set cols = contract['columns'] if columns is none else columns -%}
  {%- for name, type in cols.items() -%}
    {%- if contract['columns'].get(name) != type -%}
      {{ exceptions.raise_compiler_error("pack_ref: column '" ~ name ~ " " ~ type ~ "' of '" ~ model ~ "' is not in its contract") }}
    {%- endif -%}
  {%- endfor -%}
  {%- if pack_enabled(pack) -%}
    {{ return(ref(model)) }}
  {%- endif -%}
  {%- if cols | length == 0 -%}
    {{ exceptions.raise_compiler_error("pack_ref: empty column list for '" ~ model ~ "'") }}
  {%- endif -%}
  {%- set select = [] -%}
  {%- for name, type in cols.items() -%}
    {%- do select.append('CAST(NULL AS ' ~ type ~ ') AS ' ~ name) -%}
  {%- endfor -%}
  {{ return('(SELECT ' ~ select | join(', ') ~ ' WHERE FALSE)') }}
{% endmacro %}

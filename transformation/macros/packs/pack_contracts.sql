{#
  Column contracts between core and packs: the only place that declares which columns core reads
  from a pack model, and their DuckDB types.

    { '<pack model>': {'pack': '<pack id>', 'columns': {'<column>': '<duckdb type>', ...}}, ... }

  pack_ref() builds the empty relation of a disabled pack from it; the generic test
  `pack_contract` (tests/generic/pack_contract.sql), attached to the pack model, proves the real
  model still has these columns with these types. check_boundaries.py reads the model -> pack
  pairs from this file with a regex, so keep one entry per model in the literal form
  `'<model>': {'pack': '<pack>', 'columns': {...}}`.
#}
{% macro pack_contracts() %}
  {{ return({}) }}
{% endmacro %}

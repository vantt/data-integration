{#- Error-level check that a pack model still offers the columns core reads from it, with the
    contracted types (pack_contracts(), macros/packs/pack_contracts.sql). Attach it to the pack model
    in the pack's properties file:

      - name: int_customer_economics
        data_tests:
          - pack_contract

    `model_name` defaults to the relation name; set it (under `arguments:`) when the model has an
    alias. Column names
    and types are compared case-insensitively and without spaces; extra columns on the model are
    allowed (the contract lists only what core reads). Returns one row per missing column or
    type mismatch. -#}
{% test pack_contract(model, model_name=none) %}
{#- At parse time `model` is not the model's relation yet: validate only when executing. #}
{%- if not execute -%}
SELECT NULL AS column_name WHERE FALSE
{%- else -%}
{%- set name = model_name or model.identifier -%}
{%- set contracts = pack_contracts() -%}
{%- if name not in contracts -%}
  {{ exceptions.raise_compiler_error("pack_contract: no contract for '" ~ name ~ "' in pack_contracts()") }}
{%- endif -%}
{%- set columns = contracts[name]['columns'] -%}
{%- if columns | length == 0 -%}
  {{ exceptions.raise_compiler_error("pack_contract: empty contract for '" ~ name ~ "'") }}
{%- endif %}

WITH expected (column_name, data_type) AS (
    VALUES
    {%- for col, type in columns.items() %}
    ('{{ col | lower }}', '{{ type | upper | replace(" ", "") }}'){{ ',' if not loop.last }}
    {%- endfor %}
),

actual AS (
    SELECT LOWER(column_name) AS column_name, REPLACE(UPPER(data_type), ' ', '') AS data_type
    FROM information_schema.columns
    WHERE table_catalog = '{{ model.database }}'
      AND table_schema = '{{ model.schema }}'
      AND table_name = '{{ model.identifier }}'
)

SELECT
    e.column_name,
    e.data_type AS expected_type,
    a.data_type AS actual_type
FROM expected e
LEFT JOIN actual a ON e.column_name = a.column_name
WHERE a.data_type IS DISTINCT FROM e.data_type
{%- endif %}
{% endtest %}

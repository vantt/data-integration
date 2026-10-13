{#- Warn-level check that a std model exposes exactly the documented columns, types and order.
    `columns` is an ordered list of {name, type} pairs taken from the warehouse. Returns one row per mismatch. -#}
{% test std_column_contract(model, columns) %}
{{ config(severity='warn') }}

WITH expected (ordinal_position, column_name, data_type) AS (
    VALUES
    {%- for c in columns %}
    ({{ loop.index }}, '{{ c.name }}', '{{ c.type }}'){{ ',' if not loop.last }}
    {%- endfor %}
),

actual AS (
    SELECT ordinal_position, column_name, data_type
    FROM information_schema.columns
    WHERE table_catalog = '{{ model.database }}'
      AND table_schema = '{{ model.schema }}'
      AND table_name = '{{ model.identifier }}'
)

SELECT
    COALESCE(e.column_name, a.column_name) AS column_name,
    e.ordinal_position AS expected_position,
    a.ordinal_position AS actual_position,
    e.data_type AS expected_type,
    a.data_type AS actual_type
FROM expected e
FULL OUTER JOIN actual a ON e.column_name = a.column_name
WHERE e.ordinal_position IS DISTINCT FROM a.ordinal_position
   OR e.data_type IS DISTINCT FROM a.data_type
{% endtest %}

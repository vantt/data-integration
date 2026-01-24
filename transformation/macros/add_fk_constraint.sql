{% macro add_fk_constraint(table, column, parent_table, parent_column) %}
  {% if target.type == 'duckdb' %}
    -- Use a statement to ensure it runs as DDL
    {% call statement('add_fk', fetch_result=False) %}
      ALTER TABLE {{ this }} ADD CONSTRAINT fk_{{ column }}_{{ parent_table.identifier }} 
      FOREIGN KEY ({{ column }}) REFERENCES {{ parent_table }} ({{ parent_column }});
    {% endcall %}
  {% endif %}
{% endmacro %}

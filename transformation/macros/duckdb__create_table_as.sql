  {%- if language == 'sql' -%}
    {% set contract_config = config.get('contract') %}
    {% if contract_config.enforced %}
      {{ get_assert_columns_equivalent(compiled_code) }}
    {% endif %}
    {%- set sql_header = config.get('sql_header', none) -%}

    {{ sql_header if sql_header is not none }}

    create {% if temporary: -%}temporary{%- endif %} table
      {{ relation.include(database=(not temporary), schema=(not temporary)) }}
    {% if contract_config.enforced and not temporary %}
      (
          {% set user_columns = model['columns'] %}
          {% for col_name, col_def in user_columns.items() %}
              {{ col_name }} {{ col_def['data_type'] }}{{ "," if not loop.last }}
          {% endfor %}
          
          {# Inject Foreign Keys manually from constraints #}
          {% set constraints = model['constraints'] %}
          {{ log("DEBUG: Constraints for " ~ relation ~ ": " ~ constraints, info=True) }}
          {% if constraints %}
            {% for constraint in constraints %}
              {{ log("DEBUG: Processing constraint: " ~ constraint, info=True) }}
              {% if constraint['type'] == 'foreign_key' %}
                , FOREIGN KEY ({{ constraint['columns'][0] }}) REFERENCES {{ constraint['expression'] }}
              {% elif constraint['type'] == 'primary_key' %}
                , PRIMARY KEY ({{ constraint['columns'] | join(', ') }})
              {% endif %}
            {% endfor %}
          {% endif %}
      );
      
      insert into {{ relation }} (
          {% for col_name in user_columns %}
              {{ col_name }}{{ "," if not loop.last }}
          {% endfor %}
      )
      {{ get_select_subquery(compiled_code) }}
      ;
    {% else %}
      as (
        {{ compiled_code }}
      );
    {% endif %}
  {%- elif language == 'python' -%}
    {{ py_write_table(temporary=temporary, relation=relation, compiled_code=compiled_code) }}
  {%- else -%}
      {% do exceptions.raise_compiler_error("duckdb__create_table_as macro didn't get supported language, it got %s" % language) %}
  {%- endif -%}
{% endmacro %}

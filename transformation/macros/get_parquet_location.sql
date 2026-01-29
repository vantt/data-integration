{% macro get_parquet_location() %}
    {{ env_var('DBT_EXPORT_PATH') ~ "/" ~ this.name ~ ".parquet" }}
{% endmacro %}

{% macro get_rolling_location() %}{{ env_var('DBT_EXPORT_PATH') }}/rolling/{{ this.name }}/{{ this.name }}_{{ run_started_at.strftime('%Y%m%d%H%M%S') }}.parquet{% endmacro %}

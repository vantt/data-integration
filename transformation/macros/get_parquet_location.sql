{% macro get_parquet_location() %}
    {{ "D:/_1.FWG_PARA/1.Projects/dev/dataware_house/data-integration2/data_lake/export/marts/" ~ this.name ~ ".parquet" }}
{% endmacro %}

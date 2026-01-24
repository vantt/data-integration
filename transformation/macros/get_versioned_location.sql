{% macro get_versioned_location() %}
    {%- set export_root = var('external_root', 'target') -%}
    {%- set batch_id = var('batch_id', run_started_at.strftime('%Y%m%d_%H%M%S')) -%}
    {{ export_root ~ '/' ~ this.name ~ '_' ~ batch_id ~ '.parquet' }}
{% endmacro %}

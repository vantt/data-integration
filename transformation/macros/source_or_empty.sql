{#-
  source_or_empty(source_name, table_name, columns)

  A source whose files may not exist yet. Returns source(source_name, table_name) when its
  external_location glob matches at least one file, otherwise an empty relation with the given
  typed columns, so models still build on a lake that has never received the table (shadow,
  fresh install, disaster-recovery rebuild).

  columns: list of [name, type] pairs, e.g. [['entity_id', 'VARCHAR'], ['captured_at', 'TIMESTAMPTZ']].
  Must list every column the caller selects from the source.

  source() is always called, also while parsing, so the lineage edge (dbt DAG, module boundary
  check, Dagster asset dependency through DBT_SOURCE_KEYS) is the same as a plain source().
-#}
{% macro source_or_empty(source_name, table_name, columns) -%}
  {%- set rel = source(source_name, table_name) -%}
  {%- if not execute -%}
    {{ rel }}
  {%- else -%}
    {%- set match = modules.re.search("read_parquet\\(\\s*'([^']+)'", rel | string) -%}
    {%- if match is none -%}
      {{ exceptions.raise_compiler_error("source_or_empty: cannot find a read_parquet glob in the external_location of " ~ source_name ~ "." ~ table_name ~ ": " ~ (rel | string)) }}
    {%- endif -%}
    {%- set found = run_query("SELECT count(*) FROM glob('" ~ match.group(1) ~ "')").columns[0].values()[0] -%}
    {%- if found > 0 -%}
      {{ rel }}
    {%- else -%}
      {{ log("source_or_empty: no file for " ~ source_name ~ "." ~ table_name ~ ", using an empty relation", info=True) }}
      (SELECT
      {%- for col in columns %}
        CAST(NULL AS {{ col[1] }}) AS {{ col[0] }}{{ "," if not loop.last }}
      {%- endfor %}
      WHERE false)
    {%- endif -%}
  {%- endif -%}
{%- endmacro %}

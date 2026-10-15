{{ config(
    materialized='incremental',
    full_refresh=false,
    tags=['monitoring', 'taxonomy']
) }}
-- One row per run and domain: how far the classification engine is from the legacy customer_type
-- SQL (monitor_taxonomy_parity). Append-only history (full_refresh=false: a --full-refresh does not
-- wipe it) read to count the consecutive nights without difference before the marts switch to
-- the engine, and for 30 days after. Every dbt build that selects it appends rows; read one row per
-- run_date and domain (e.g. the last run of the night). docs/architecture/taxonomy-engine.md §4b.
SELECT
    current_timestamp AS run_at,
    CAST(timezone('Asia/Ho_Chi_Minh', current_timestamp) AS DATE) AS run_date,
    p.domain,
    max(p.ruleset_version) AS ruleset_version,
    count(*) AS n_entities,
    count(*) FILTER (WHERE p.is_label_diff) AS n_label_diff,
    count(*) FILTER (WHERE p.is_flag_diff) AS n_flag_diff,
    count(*) FILTER (WHERE p.is_legacy_else) AS n_legacy_else,
    count(*) FILTER (WHERE p.is_engine_default) AS n_engine_default,
    count(*) FILTER (WHERE p.engine_label = 'UNMAPPED') AS n_unmapped,
    count(*) FILTER (WHERE p.engine_label = 'UNKNOWN') AS n_unknown
FROM {{ ref('monitor_taxonomy_parity') }} p
GROUP BY p.domain

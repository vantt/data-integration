{{ config(materialized='view', tags=['monitoring', 'taxonomy']) }}
-- One row per night (run_date, Asia/Ho_Chi_Minh) and domain over monitor_taxonomy_parity_log, which
-- gains a row on every dbt build. A night passes (is_pass) when EVERY run of that day had no label
-- and no flag difference and the rule set did not change during the day; the counters are those of
-- the day's last run. This is the table the prod parallel run is counted on
-- (docs/architecture/taxonomy-engine.md §4b).
WITH runs AS (
    SELECT
        *,
        row_number() OVER (PARTITION BY run_date, domain ORDER BY run_at DESC) AS rn_last
    FROM {{ ref('monitor_taxonomy_parity_log') }}
)
SELECT
    run_date,
    domain,
    count(*) AS n_runs,
    min(run_at) AS first_run_at,
    max(run_at) AS last_run_at,
    max(n_label_diff) AS max_label_diff,
    max(n_flag_diff) AS max_flag_diff,
    count(DISTINCT ruleset_version) AS n_ruleset_versions,
    max(ruleset_version) FILTER (WHERE rn_last = 1) AS ruleset_version,
    max(n_entities) FILTER (WHERE rn_last = 1) AS n_entities,
    max(n_legacy_else) FILTER (WHERE rn_last = 1) AS n_legacy_else,
    max(n_engine_default) FILTER (WHERE rn_last = 1) AS n_engine_default,
    max(n_unmapped) FILTER (WHERE rn_last = 1) AS n_unmapped,
    max(n_unknown) FILTER (WHERE rn_last = 1) AS n_unknown,
    max(n_label_diff) = 0 AND max(n_flag_diff) = 0 AND count(DISTINCT ruleset_version) = 1 AS is_pass
FROM runs
GROUP BY run_date, domain

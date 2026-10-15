{{ config(enabled=var('taxonomy_selftest'), materialized='table', tags=['taxonomy_selftest']) }}
-- Feature model of the engine selftest domains: empty and typed; unit tests give the rows.
SELECT
    CAST(NULL AS VARCHAR) AS s_key,
    CAST(NULL AS VARCHAR) AS s_text,
    CAST(NULL AS VARCHAR) AS s_text2,
    CAST(NULL AS DOUBLE) AS s_num,
    CAST(NULL AS VARCHAR[]) AS s_list
WHERE FALSE

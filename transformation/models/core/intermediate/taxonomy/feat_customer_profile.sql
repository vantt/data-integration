{{ config(materialized='table', tags=['taxonomy']) }}
-- Customer profile features of the classification engine (feature catalog: vars.taxonomy in
-- dbt_project.yml; docs/architecture/taxonomy-engine.md §4b). One row per customer of
-- dim_customers_base, sentinel 'Unknown' included. Raw values, not normalized: the rules keep the
-- exact LIKE semantics of the SQL they replace (case-sensitive, '_' is a wildcard).
SELECT
    customer_key,
    customer_group AS group_blob,
    customer_group_code AS group_code,
    customer_group_name AS group_name
FROM {{ ref('dim_customers_base') }}

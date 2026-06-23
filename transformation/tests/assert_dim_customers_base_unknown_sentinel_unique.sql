-- Test: dim_customers_base must contain exactly one 'Unknown' sentinel row.
-- The UNION ALL outside the incremental filter always appends the sentinel; the
-- delete+insert unique_key dedup should prevent duplicates. This test catches any
-- regression where the sentinel appears more than once (e.g. incremental strategy change).
SELECT COUNT(*) AS unknown_count
FROM {{ ref('dim_customers_base') }}
WHERE customer_id = 'Unknown'
HAVING COUNT(*) <> 1

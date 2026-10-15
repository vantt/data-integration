-- Price intervals of one (variant, price list) never overlap and at most one is current:
-- each interval ends (valid_to_at, exclusive) no later than the next one starts.
WITH ordered AS (
    SELECT
        variant_id,
        price_list_id,
        valid_from_at,
        valid_to_at,
        is_current,
        LEAD(valid_from_at) OVER (PARTITION BY variant_id, price_list_id ORDER BY valid_from_at) AS next_valid_from_at
    FROM {{ ref('fact_variant_price_changes') }}
)

SELECT variant_id, price_list_id, valid_from_at, 'overlaps the next interval' AS problem
FROM ordered
WHERE next_valid_from_at IS NOT NULL
  AND (valid_to_at IS NULL OR valid_to_at > next_valid_from_at)

UNION ALL

SELECT variant_id, price_list_id, MIN(valid_from_at), 'more than one current interval' AS problem
FROM ordered
WHERE is_current
GROUP BY variant_id, price_list_id
HAVING COUNT(*) > 1

-- Rankable population count sanity check.
-- Expects roughly 939 customers with benchmark_status = 'ranked' (±100 for snapshot drift).
-- Returns rows (= test failure) if count falls outside the [800, 1100] band.
-- Adjust bounds if the real customer base changes significantly.
SELECT COUNT(*) AS ranked_count
FROM {{ ref('int_customer_benchmarks') }}
WHERE benchmark_status = 'ranked'
HAVING COUNT(*) NOT BETWEEN 800 AND 1100

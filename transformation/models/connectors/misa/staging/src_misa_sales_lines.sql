{{ config(materialized='view', tags=['src', 'misa']) }}

-- Dedup MISA sales lines by (voucher_no, line_no), keep latest ingested_at.
-- View materialization: file-drop sources are small (~500 rows), full-scan dedup is cheap.

WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY voucher_no, line_no
            ORDER BY ingested_at DESC
        ) AS rn
    FROM {{ source('misa_raw', 'sales_lines') }}
)

SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1

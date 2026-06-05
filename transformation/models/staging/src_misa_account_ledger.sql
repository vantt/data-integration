{{ config(materialized='view', tags=['src', 'misa']) }}

-- Dedup MISA account-ledger lines by (account, voucher_no, posting_date, offset_account, debit, credit).
-- No surrogate line_no in the raw parquet (account-ledger is not a sales-line report),
-- so dedup key uses the full business grain per journal entry.
-- View materialization: file-drop source is small (~600 rows/export), full-scan dedup is cheap.

WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY account, voucher_no, posting_date, offset_account, debit, credit
            ORDER BY ingested_at DESC
        ) AS rn
    FROM {{ source('misa_raw', 'account_ledger') }}
)

SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1

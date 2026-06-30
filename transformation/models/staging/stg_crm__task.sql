{{ config(materialized='view', tags=['staging', 'crm']) }}

-- Incremental source: multiple parquet batches per task (updated_at watermark).
-- Dedup to latest snapshot per task_id before joining downstream.
WITH ranked AS (
    SELECT
        task_id,
        party_id,
        customer_id::INTEGER                    AS customer_id,
        title::VARCHAR                          AS title,
        status::VARCHAR                         AS status,
        priority::INTEGER                       AS priority,
        source::VARCHAR                         AS source,
        source_ref::VARCHAR                     AS source_ref,
        assignee_user_id::VARCHAR               AS assignee_user_id,
        created_by::VARCHAR                     AS created_by,
        due_at::TIMESTAMPTZ                     AS due_at,
        completed_at::TIMESTAMPTZ               AS completed_at,
        created_at::TIMESTAMPTZ                 AS created_at,
        updated_at::TIMESTAMPTZ                 AS updated_at,
        ROW_NUMBER() OVER (
            PARTITION BY task_id ORDER BY updated_at DESC
        )                                       AS rn
    FROM {{ source('crm_export', 'crm_task') }}
    WHERE task_id IS NOT NULL
)

SELECT
    task_id, party_id, customer_id, title, status, priority,
    source, source_ref, assignee_user_id, created_by,
    due_at, completed_at, created_at, updated_at
FROM ranked
WHERE rn = 1

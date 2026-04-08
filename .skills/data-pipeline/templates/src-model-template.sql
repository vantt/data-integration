{{"{{"}} config(
    materialized='incremental',
    unique_key='{BIZ_KEY}',
    incremental_strategy='delete+insert',
    tags=['source', '{SOURCE}']
) {{"}}"}}

-- =============================================================================
-- SOURCE EXTRACTION: {SOURCE_UPPER} {ENTITY_UPPER}
-- =============================================================================
-- Purpose:
--   1. Read raw Parquet từ Data Lake (dlt pipeline output).
--   2. Tech dedup theo entity_id (ROW_NUMBER + ingest_method priority).
--   3. Extract scalar JSON fields từ payload.
--   4. Business dedup theo {BIZ_KEY} (latest event_timestamp wins).
--   5. Discard payload → giải phóng memory cho downstream models.
--
-- OOM-safe:
--   - Tech dedup sort trên lightweight keys (entity_id, event_timestamp).
--   - JSON extraction chỉ chạy trên tech-deduped rows.
--   - Biz dedup chạy trên flat data — không có payload.
--   - Incremental filter 7-day window → dataset nhỏ.
-- =============================================================================

WITH raw_data AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        payload
    FROM {{{{ source('{SOURCE}_raw', '{ENTITY}') }}}}
    {{% if is_incremental() %}}
    -- Buffer 7 ngày để catch late-arriving events từ webhook/history_log
    WHERE event_timestamp > (SELECT MAX(event_timestamp) - INTERVAL 7 DAY FROM {{{{ this }}}})
    {{% endif %}}
),

-- Tech dedup: giữ record mới nhất mỗi entity_id
-- Priority: webhook (3) > history_log (2) > batch_sync (1)
deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY entity_id
            ORDER BY
                event_timestamp DESC,
                CASE
                    WHEN ingest_method = 'webhook'      THEN 3
                    WHEN ingest_method = 'history_log'  THEN 2
                    ELSE 1
                END DESC
        ) AS rn
    FROM raw_data
),

-- JSON extraction: payload bị discard sau CTE này
extracted AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,

        -- Business key
        json_extract_string(payload, '$.id')          AS {BIZ_KEY},

        -- Timestamps
        json_extract_string(payload, '$.created_on')  AS created_on,
        json_extract_string(payload, '$.modified_on') AS modified_on,

        -- TODO: thêm các fields cần extract
        -- json_extract_string(payload, '$.status')   AS status,
        -- try_cast(json_extract_string(payload, '$.total') AS DECIMAL(18,2)) AS total_amount,
        -- json_extract_string(payload, '$.nested.field') AS nested_field,

        -- Giữ nested arrays as JSON text cho downstream unnest models nếu cần
        -- json_extract_string(payload, '$.line_items') AS line_items_json,

        -- Metadata
        payload  -- XÓA DÒNG NÀY sau khi đã extract đủ fields (giải phóng memory)

    FROM deduped
    WHERE rn = 1
)

-- Business dedup: giữ bản ghi mới nhất mỗi {BIZ_KEY}
SELECT * FROM extracted
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY {BIZ_KEY}
    ORDER BY
        event_timestamp DESC,
        try_cast(modified_on AS TIMESTAMP) DESC NULLS LAST
) = 1

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
--   4. Business dedup theo {BIZ_KEY} (latest modified_on wins, NOT event_timestamp).
--   5. Discard payload → giải phóng memory cho downstream models.
--
-- OOM-safe:
--   - Tech dedup sort trên lightweight keys (entity_id, _dlt_load_id).
--   - JSON extraction chỉ chạy trên tech-deduped rows.
--   - Biz dedup chạy trên flat data — không có payload.
--   - Incremental filter _dlt_load_id → catch all new loads kể cả late-arriving data.
--
-- Dedup ordering (L28):
--   - PRIMARY: modified_on DESC (entity timestamp = source of truth)
--   - SECONDARY: ingest_method priority (webhook > history_log > batch_sync)
--   - NOT event_timestamp: event_timestamp = log system timestamp, có thể misleading
--
-- Incremental filter (L29):
--   - Dùng _dlt_load_id thay vì event_timestamp
--   - _dlt_load_id tăng đơn điệu theo từng dlt load
--   - event_timestamp filter bỏ sót full-refresh history_log (event_timestamp cũ, _dlt_load_id mới)
-- =============================================================================

WITH raw_data AS (
    SELECT
        entity_id,
        entity_type,
        event_timestamp,
        ingest_method,
        _dlt_load_id,
        payload
    FROM {{{{ source('{SOURCE}_raw', '{ENTITY}') }}}}
    {{% if is_incremental() %}}
    -- _dlt_load_id filter: catch tất cả data từ load mới, kể cả late-arriving events
    WHERE _dlt_load_id > (SELECT COALESCE(MAX(_dlt_load_id), '') FROM {{{{ this }}}})
    {{% endif %}}
),

-- Tech dedup: giữ record mới nhất mỗi entity_id
-- Priority: webhook (3) > history_log (2) > batch_sync/text (1)
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
                    ELSE 1  -- batch_sync; 'text' là legacy alias cũng về đây
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
),

-- Compare-before-overwrite (L30): union với existing rows cho cùng {BIZ_KEY}
-- để đảm bảo chỉ genuinely newer data thắng (tránh stale overwrite)
candidates AS (
    SELECT * FROM extracted
    {{% if is_incremental() %}}
    UNION ALL
    SELECT existing.* FROM {{{{ this }}}} existing
    INNER JOIN (SELECT DISTINCT {BIZ_KEY} FROM extracted) k
        ON existing.{BIZ_KEY} = k.{BIZ_KEY}
    {{% endif %}}
)

-- Business dedup: modified_on làm primary sort (source of truth), KHÔNG phải event_timestamp
SELECT * FROM candidates
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY {BIZ_KEY}
    ORDER BY
        try_cast(modified_on AS TIMESTAMPTZ) DESC NULLS LAST,
        CASE ingest_method WHEN 'webhook' THEN 3 WHEN 'history_log' THEN 2 ELSE 1 END DESC
) = 1

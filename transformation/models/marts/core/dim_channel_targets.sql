{{ config(
    tags=['mart', 'dim', 'targets'],
    location="{{ get_rolling_location() }}"
) }}

-- dim_channel_targets: Channel-level budget targets seeded from seed_channel_targets.csv.
-- Maintained manually until a formal budget process is in place.
-- Join key: channel_key (FK to dim_channels), period_month (month-start DATE), metric_type.
-- metric_type enum: 'NET_REVENUE' (VND), 'NET_MARGIN_PCT' (%), 'ORDER_COUNT' (count).

WITH seed AS (
    SELECT * FROM {{ ref('seed_channel_targets') }}
),

dim_channel AS (
    SELECT channel_key, channel_name FROM {{ ref('dim_channels') }}
)

SELECT
    -- Surrogate key: unique per (channel, month, metric, source)
    {{ dbt_utils.generate_surrogate_key([
        'c.channel_key',
        'CAST(s.period_month AS VARCHAR)',
        's.metric_type',
        's.target_source'
    ]) }}                                   AS channel_target_key,

    -- Dimension FK
    c.channel_key,
    c.channel_name,

    -- Time grain (month-start)
    CAST(s.period_month AS DATE)            AS period_month,

    -- Metric
    s.metric_type,
    CAST(s.target_value AS DOUBLE)          AS target_value,
    s.target_source,
    s.notes,

    current_timestamp                       AS loaded_at

FROM seed s
-- Join by name so the seed CSV stays human-readable; channel_key is derived here
INNER JOIN dim_channel c ON c.channel_name = s.channel_name

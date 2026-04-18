SELECT
    m.spend_key,
    m.spend_code,
    m.campaign_id,
    CAST(strptime(CAST(m.date_key AS VARCHAR), '%Y%m%d') AS DATE) AS spend_date,
    date_trunc('week', strptime(CAST(m.date_key AS VARCHAR), '%Y%m%d')) AS week_start,
    date_trunc('month', strptime(CAST(m.date_key AS VARCHAR), '%Y%m%d')) AS month_start,
    c.channel_name,
    c.channel_category,
    c.channel_format,
    c.platform,
    c.channel_brand,
    c.market,
    c.source_type,
    COALESCE(b.branch_location_name, 'Unknown') AS branch_location_name,
    m.spend_amount,
    m.clicks,
    m.impressions,
    m.clicks > 0 AS has_clicks_flag,
    m.impressions > 0 AS has_impressions_flag,
    -- Renamed from `channel_group` to avoid semantic collision with channel_* taxonomy columns.
    CASE
        WHEN c.channel_format IN ('Social', 'Web', 'Marketplace') THEN 'Paid Digital'
        WHEN c.channel_format = 'Retail' THEN 'Offline'
        ELSE COALESCE(c.channel_format, 'Other')
    END AS marketing_spend_bucket
FROM src_fact_marketing_spend m
LEFT JOIN src_dim_channels c ON m.channel_key = c.channel_key
LEFT JOIN src_dim_branch_location b ON c.location_id = CAST(b.branch_location_id AS VARCHAR)


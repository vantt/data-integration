SELECT
    m.spend_key,
    m.spend_code,
    m.campaign_id,
    CAST(strptime(CAST(m.date_key AS VARCHAR), '%Y%m%d') AS DATE) AS spend_date,
    date_trunc('week', strptime(CAST(m.date_key AS VARCHAR), '%Y%m%d')) AS week_start,
    date_trunc('month', strptime(CAST(m.date_key AS VARCHAR), '%Y%m%d')) AS month_start,
    c.channel_name,
    c.channel_category,
    c.platform_group,
    c.platform,
    c.channel_brand,
    c.market,
    COALESCE(b.branch_location_name, 'Unknown') AS branch_location_name,
    m.spend_amount,
    m.clicks,
    m.impressions,
    m.clicks > 0 AS has_clicks_flag,
    m.impressions > 0 AS has_impressions_flag,
    CASE
        WHEN c.platform_group IN ('Social', 'Web') THEN 'Paid Digital'
        WHEN c.platform_group = 'Retail' THEN 'Offline'
        ELSE COALESCE(c.platform_group, 'Other')
    END AS channel_group
FROM src_fact_marketing_spend m
LEFT JOIN src_dim_channels c ON m.channel_key = c.channel_key
LEFT JOIN src_dim_branch_location b ON c.location_id = CAST(b.branch_location_id AS VARCHAR)


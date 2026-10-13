{{ config(
    tags=['mart', 'fact'],
    location="{{ get_rolling_location() }}"
) }}

WITH items AS (
    SELECT * FROM {{ ref('std_order_items') }}
),
orders AS (
    SELECT * FROM {{ ref('std_orders') }}

),
valid_customers AS (
    SELECT customer_key FROM {{ ref('dim_customers_base') }}
),
source_definitions AS (
    SELECT id, is_generic_source FROM {{ ref('ref_order_sources') }}
),
valid_locations AS (
    SELECT cast(id as varchar) as location_id FROM {{ ref('ref_branch_locations') }}
),

-- Team membership with SCD2 (for member-based attribution)
team_members AS (
    SELECT * FROM {{ ref('stg_team_members') }}
),

teams AS (
    SELECT * FROM {{ ref('stg_teams') }}
)

SELECT
    -- Surrogate Keys (Foreign Keys to Dims)
    CASE 
        WHEN i.product_id IS NULL OR i.product_id = '' THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(["i.product_id || '-' || coalesce(i.variant_id, '')"]) }}
    END as product_key,
    {{ dbt_utils.generate_surrogate_key(["coalesce(i.product_type, 'Unknown')"]) }} as product_type_key,
    COALESCE(vc.customer_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as customer_key,
    -- Validated location: fallback to Unknown if location_id not in ref_branch_locations
    {{ dbt_utils.generate_surrogate_key(["coalesce(vl.location_id, 'Unknown')"]) }} as branch_location_key,

    -- Channel Key Logic (uses validated location for generic sources)
    CASE
        WHEN sd.is_generic_source = true THEN
            {{ dbt_utils.generate_surrogate_key(['cast(o.source_id as string)', "coalesce(vl.location_id, 'Unknown')"]) }}
        ELSE
            {{ dbt_utils.generate_surrogate_key(['cast(o.source_id as string)', "'Unknown'"]) }}
    END as channel_key,

    -- Sales attribution keys (see docs/context/sales-segmentation-guide.md § 3.4)
    COALESCE(dseller.staff_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as seller_staff_key,
    COALESCE(dcreator.staff_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as creator_staff_key,

    -- Team attribution (see docs/context/team-management.md)
    COALESCE(t.team_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as team_key,
    {{ dbt_utils.generate_surrogate_key(['o.status']) }} as status_key,
    -- ICT explicit: AT TIME ZONE ensures 0h–7h ICT orders get correct local date
    -- regardless of session TimeZone setting (matches fact_orders.date_key derivation).
    coalesce(cast(strftime(o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh', '%Y%m%d') as integer), 19000101) as date_key, -- Link to dim_date YYYYMMDD
    (extract(hour from o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') * 100) + extract(minute from o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') as time_key,  -- ICT hour+minute, mirrors date_key TZ conversion
    
    -- Degenerate Keys
    i.order_id,
    i.order_line_id,
    
    -- Metrics
    i.quantity,
    -- Revenue is VAT-EXCLUSIVE: Sapo line prices (line_amount) are VAT-inclusive (giá bán gồm VAT).
    -- Sapo only reports VAT at order level ($.total_tax), so strip the embedded VAT per line using
    -- the order's VAT ratio = (total − tax) / total. Zero-tax orders (exports) keep full line_amount;
    -- 8%/10% items handled automatically via the per-order ratio. Keeps SKU margins on the same
    -- VAT-exclusive basis as MISA COGS. See docs/analytics-handbook/guides/revenue_terminology.md.
    i.line_amount * COALESCE(
        (o.total_amount - COALESCE(o.vat_amount, 0)) / NULLIF(o.total_amount, 0),
        1
    ) as net_revenue,
    i.discount_amount,
    i.distributed_discount_amount,
    i.discount_rate,
    i.is_gift_line,
    i.weight_grams,
    
    -- Addresses
    -- Addresses
    CASE 
        WHEN o.shipping_province IS NULL THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(["coalesce(o.shipping_province,'')", "coalesce(o.shipping_district,'')", "coalesce(o.shipping_ward,'')", "coalesce(o.shipping_country, 'Vietnam')"]) }}
    END as shipping_geography_key,

    CASE 
        WHEN o.billing_province IS NULL THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(["coalesce(o.billing_province,'')", "coalesce(o.billing_district,'')", "coalesce(o.billing_ward,'')", "coalesce(o.billing_country, 'Vietnam')"]) }}
    END as billing_geography_key,
    
    -- Pro-rated amounts (Simple logic for now)
    -- Ideally we'd allocate order-level discount to items here
    
    o.created_at as ordered_at,
    o.updated_at

FROM items i
JOIN orders o ON i.order_id = o.order_id
LEFT JOIN valid_customers vc ON {{ dbt_utils.generate_surrogate_key(['o.customer_id']) }} = vc.customer_key
LEFT JOIN {{ ref('dim_staff') }} dseller ON {{ dbt_utils.generate_surrogate_key(['o.seller_user_id']) }} = dseller.staff_key
LEFT JOIN {{ ref('dim_staff') }} dcreator ON {{ dbt_utils.generate_surrogate_key(['o.creator_user_id']) }} = dcreator.staff_key
LEFT JOIN source_definitions sd ON cast(o.source_id as varchar) = cast(sd.id as varchar)
LEFT JOIN valid_locations vl ON cast(o.location_id as varchar) = vl.location_id
-- Team attribution: seller email → team_members (SCD2) → teams
LEFT JOIN team_members tm ON lower(dseller.email) = tm.staff_email
    AND cast(o.created_at as date) >= tm.effective_from
    AND (tm.effective_to IS NULL OR cast(o.created_at as date) <= tm.effective_to)
LEFT JOIN teams t ON tm.team_code = t.team_code

{{ config(
    tags=['mart', 'fact'],
    options={'format': 'parquet'},
    location="{{ get_rolling_location() }}"
) }}

WITH orders AS (
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

first_shipment AS (
    SELECT order_id, MIN(shipped_at) as first_shipped_at
    FROM {{ ref('std_fulfillments') }}
    WHERE shipped_at IS NOT NULL
    GROUP BY order_id
),

-- Team membership with SCD2 (for member-based attribution)
team_members AS (
    SELECT * FROM {{ ref('stg_team_members') }}
),

teams AS (
    SELECT * FROM {{ ref('stg_teams') }}
),

-- Classify discount items to order-level summary
-- See: docs/architecture/order-pl/discount-classification.md
discount_classified AS (
    SELECT
        d.order_code,
        d.discount_rate,
        d.amount,
        CASE
            WHEN d.reason ILIKE 'voucher seller:%'
                THEN 'voucher_promotional'
            WHEN d.reason = 'Bundle Deal'
                THEN 'bundle'
            WHEN d.reason ILIKE '%sampling%' OR d.reason ILIKE '%mẫu%' OR d.reason ILIKE '%tặng%'
                THEN 'sampling_gift'
            WHEN d.reason ILIKE '%đại lý%' OR d.reason ILIKE '%hợp đồng%' OR d.reason ILIKE '%nhà thuốc%'
                THEN 'wholesale_explicit'
            WHEN LOWER(d.reason) ILIKE '%mỹ%'
                OR TRIM(LOWER(d.reason)) = 'us'
                OR LOWER(d.reason) ILIKE '% us%'
                THEN 'overseas'
            WHEN d.reason ILIKE '%ctkm%' OR d.reason ILIKE '%father%' OR d.reason ILIKE '%mascot%'
                THEN 'campaign'
            WHEN d.reason ILIKE '%nhân viên%' OR d.reason ILIKE '%ctv%' OR d.reason ILIKE '%hoa hồng%'
                THEN 'employee_internal'
            WHEN d.discount_rate < 20
                THEN 'negotiated_micro'
            WHEN d.discount_rate < 40
                THEN 'negotiated_standard'
            ELSE
                'negotiated_deep'
        END AS discount_type
    FROM {{ ref('std_order_discount_items') }} d
),

discount_order_summary AS (
    SELECT
        order_code,
        MAX(discount_rate)              AS max_discount_rate,
        MAX_BY(discount_type, amount)   AS primary_discount_type
    FROM discount_classified
    GROUP BY order_code
),

-- NEW CTE: line-item discount summary per order
-- Max discount_rate across all discounted lines per order.
-- Do NOT confuse with max_discount_rate (order-level discount_items). Separate column.
line_discount_order_summary AS (
    SELECT
        order_id,
        MAX(
            CASE
                WHEN discount_amount > 0 AND unit_price > 0 AND quantity > 0
                THEN discount_amount / NULLIF(unit_price * quantity, 0)
                ELSE NULL
            END
        ) AS max_line_discount_rate
    FROM {{ ref('std_order_items') }}
    WHERE discount_amount > 0
    GROUP BY order_id
),

channel_scope AS (
    SELECT channel_key, is_sales_channel, channel_format
    FROM {{ ref('dim_channels') }}
),

-- Use dim_customers_base (not dim_customers) to avoid cycle: dim_customers → int_customer_metrics → fact_orders
customer_type_info AS (
    SELECT
        customer_key,
        CASE
            WHEN customer_group LIKE '%WHOLESALE%' THEN 'WHOLESALE'
            WHEN customer_group LIKE '%TYPE_PARTNER%' OR customer_group LIKE '%KY_GUI%' THEN 'PARTNER'
            WHEN customer_group LIKE '%TYPE_STAFF%' THEN 'STAFF'
            WHEN customer_group LIKE '%TYPE_KOL%' THEN 'KOL'
            WHEN customer_group LIKE '%TYPE_CROSSBORDER%' OR customer_group LIKE '%CTN00014%' THEN 'CROSSBORDER'
            ELSE 'RETAIL'
        END AS customer_type
    FROM {{ ref('dim_customers_base') }}
)

SELECT
    -- Keys
    orders.order_id,
    orders.order_code,
    COALESCE(vc.customer_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as customer_key,
    CASE 
        WHEN shipping_province IS NULL OR shipping_province = '' OR shipping_province = 'Unknown' THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(["trim(coalesce(shipping_province, ''))", "trim(coalesce(shipping_district, ''))", "trim(coalesce(shipping_ward, ''))", "trim(coalesce(shipping_country, 'Vietnam'))"]) }}
    END as shipping_geography_key,

    CASE 
        WHEN billing_province IS NULL OR billing_province = '' OR billing_province = 'Unknown' THEN {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}
        ELSE {{ dbt_utils.generate_surrogate_key(["trim(coalesce(billing_province, ''))", "trim(coalesce(billing_district, ''))", "trim(coalesce(billing_ward, ''))", "trim(coalesce(billing_country, 'Vietnam'))"]) }}
    END as billing_geography_key,

    -- Full Address Strings
    concat_ws(', ', nullif(shipping_address1, ''), nullif(shipping_ward, ''), nullif(shipping_district, ''), nullif(shipping_province, ''), coalesce(nullif(shipping_country, ''), 'Vietnam')) as shipping_address,
    concat_ws(', ', nullif(billing_address1, ''), nullif(billing_ward, ''), nullif(billing_district, ''), nullif(billing_province, ''), coalesce(nullif(billing_country, ''), 'Vietnam')) as billing_address,
    
    -- Note: Orders can have multiple promotions. To keep 1:1, we might pick the primary one 
    -- or just bridge it later. For now, we leave NULL or specific handling if needed. 
    -- Simplification: Just take the first code if present, or NULL.
    {{ dbt_utils.generate_surrogate_key(["coalesce(json_extract_string(json_extract_string(discount_codes, '$[0]'), '$.code'), 'Unknown')"]) }} as promotion_key,
    -- Validated location: fallback to Unknown if location_id not in ref_branch_locations
    {{ dbt_utils.generate_surrogate_key(["coalesce(vl.location_id, 'Unknown')"]) }} as branch_location_key,

    -- Channel Key Logic (uses validated location for generic sources)
    CASE
        WHEN sd.is_generic_source = true THEN
            {{ dbt_utils.generate_surrogate_key(['cast(source_id as string)', "coalesce(vl.location_id, 'Unknown')"]) }}
        ELSE
            {{ dbt_utils.generate_surrogate_key(['cast(source_id as string)', "'Unknown'"]) }}
    END as channel_key,

    -- Sales attribution keys (see docs/context/sales-segmentation-guide.md § 3.4)
    -- seller_staff_key  = người chốt/được giao đơn → primary for team/commission
    -- creator_staff_key = người tạo đơn trên Sapo → operational/fallback
    COALESCE(dseller.staff_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as seller_staff_key,
    COALESCE(dcreator.staff_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as creator_staff_key,

    -- Team attribution (see docs/context/team-management.md)
    -- Uses seller email → team_members (SCD2) → teams
    COALESCE(t.team_key, {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }}) as team_key,
    {{ dbt_utils.generate_surrogate_key(['status']) }} as status_key,
    -- ICT explicit: AT TIME ZONE ensures 0h–7h ICT orders (which are prior UTC date)
    -- get the correct local date regardless of session TimeZone setting.
    coalesce(cast(strftime(created_at AT TIME ZONE 'Asia/Ho_Chi_Minh', '%Y%m%d') as integer), 19000101) as date_key,
    (extract(hour from created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') * 100) + extract(minute from created_at AT TIME ZONE 'Asia/Ho_Chi_Minh') as time_key,  -- ICT hour+minute, mirrors date_key TZ conversion
    
    -- Status Metrics
    status,
    payment_status,
    fulfillment_status,
    
    -- Financial Metrics (Revenue Waterfall)
    -- See: docs/analytics-handbook/guides/revenue_terminology.md
    -- IMPORTANT: Sapo selling prices (giá bán) are VAT-INCLUSIVE. $.total (total_amount) is the
    -- gross amount with VAT already inside; $.total_tax (vat_amount) is that embedded VAT
    -- (Sapo computes it exactly per-order: 8/108 for 8% items, 10/110 for 10% items, 0 for exports).
    -- Therefore: net revenue = total − tax (VAT-exclusive), and the cash collected from the
    -- customer = total (VAT already inside — do NOT add tax on top, that double-counts VAT).
    total_amount + total_discount_amount as gross_revenue,                 -- Giá bán × SL trước chiết khấu (đã gồm VAT)
    total_discount_amount as discount_amount,                              -- Chiết khấu
    total_amount - COALESCE(vat_amount, 0) as net_revenue,                 -- Doanh thu thuần sau chiết khấu, ĐÃ TRỪ VAT
    vat_amount,                                                            -- VAT nhúng trong giá bán (Sapo $.total_tax)
    total_amount as total_collected,                                       -- Tổng khách trả = giá bán (đã gồm VAT)
    
    -- Performance Metrics
    fs.first_shipped_at,                                     -- Ngày xuất kho đầu tiên
    date_diff('hour', created_at, completed_at) as time_to_complete_hours,
    
    orders.client_info,
    orders.discount_codes,
    orders.order_coupon_code,
    dos.max_discount_rate,
    dos.primary_discount_type,
    ld.max_line_discount_rate,   -- NEW: item-level max rate; separate from order-level max_discount_rate
    orders.note,
    orders.tags,

    created_at as ordered_at,
    updated_at,

    -- Segment scope: pure channel+customer classification, status-independent
    -- (see docs/analytics-handbook/semantic/segments.md)
    COALESCE(ch.is_sales_channel, false)                                       AS scope_sales,
    COALESCE(ch.is_sales_channel, false)
        AND COALESCE(cu2.customer_type, 'RETAIL') = 'RETAIL'
        -- Exclude Đại Lý (B2B channel orders): ~92 dealers are tagged customer_type=RETAIL
        -- due to incomplete migration; channel_format='B2B' identifies their Đại Lý orders.
        -- Consistent with mart_deadstock_target_queue exclusion (acquisition_source='Đại Lý').
        -- Note: orders from these dealers placed on non-B2B channels remain a known residual
        -- leak (cannot resolve without dim_customers — circular dep).
        AND COALESCE(ch.channel_format, '') <> 'B2B'                          AS scope_retail,
    COALESCE(ch.is_sales_channel, false)
        AND (
            COALESCE(cu2.customer_type, 'RETAIL') IN ('WHOLESALE', 'PARTNER')
            OR COALESCE(ch.channel_format, '') = 'B2B'
        )                                                                       AS scope_b2b,
    -- Status gate: use with scope_* for revenue metrics; omit for order counts (includes cancelled/draft)
    orders.status NOT IN ('CANCELLED', 'DRAFT')                                AS is_active_order

FROM orders
LEFT JOIN valid_customers vc ON {{ dbt_utils.generate_surrogate_key(["coalesce(cast(orders.customer_id as varchar), 'Unknown')"]) }} = vc.customer_key
LEFT JOIN {{ ref('dim_staff') }} dseller ON {{ dbt_utils.generate_surrogate_key(['orders.seller_user_id']) }} = dseller.staff_key
LEFT JOIN {{ ref('dim_staff') }} dcreator ON {{ dbt_utils.generate_surrogate_key(['orders.creator_user_id']) }} = dcreator.staff_key
LEFT JOIN source_definitions sd ON cast(orders.source_id as varchar) = cast(sd.id as varchar)
LEFT JOIN valid_locations vl ON cast(orders.location_id as varchar) = vl.location_id
LEFT JOIN first_shipment fs ON orders.order_id = fs.order_id
-- Team attribution: seller email → team_members (SCD2) → teams
LEFT JOIN team_members tm ON lower(dseller.email) = tm.staff_email
    AND cast(orders.created_at as date) >= tm.effective_from
    AND (tm.effective_to IS NULL OR cast(orders.created_at as date) <= tm.effective_to)
LEFT JOIN teams t ON tm.team_code = t.team_code
LEFT JOIN discount_order_summary dos ON orders.order_code = dos.order_code
LEFT JOIN line_discount_order_summary ld ON orders.order_id = ld.order_id
LEFT JOIN channel_scope ch ON (
    CASE
        WHEN sd.is_generic_source = true THEN
            {{ dbt_utils.generate_surrogate_key(['cast(source_id as string)', "coalesce(vl.location_id, 'Unknown')"]) }}
        ELSE
            {{ dbt_utils.generate_surrogate_key(['cast(source_id as string)', "'Unknown'"]) }}
    END
) = ch.channel_key
LEFT JOIN customer_type_info cu2 ON {{ dbt_utils.generate_surrogate_key(["coalesce(cast(orders.customer_id as varchar), 'Unknown')"]) }} = cu2.customer_key

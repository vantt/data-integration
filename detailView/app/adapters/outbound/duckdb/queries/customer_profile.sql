-- Customer profile + behavior + value tier from dim_customers (single serving dimension).
-- Matched on natural key customer_id. customer_key returned for downstream fact joins.
SELECT
    customer_key,
    customer_id,
    full_name,
    phone,
    email,
    dob,
    sex,
    address1,
    ward,
    district,
    province,
    country,
    geo_region,
    loyalty_point,
    customer_type,
    customer_group,
    created_at,
    updated_at,
    -- value / RFM metrics
    lifetime_value,
    order_count,
    value_group,
    recency_days,
    lifecycle_stage,
    channel_preference,
    product_affinity,
    payment_behavior,
    first_order_date,
    last_order_date,
    lifespan_days
FROM dim_customers
WHERE customer_id = ?
LIMIT 1;

{{ config(
    materialized='incremental',
    unique_key='customer_key',
    tags=['mart', 'intermediate']
) }}

WITH orders AS (
    SELECT * FROM {{ ref('fact_orders') }}
),

-- Determine which customers need processing
-- If incremental, only fetch customers who had orders in the incoming batch (plus their full history)
changed_customers AS (
    {% if is_incremental() %}
    SELECT DISTINCT customer_key 
    FROM orders 
    WHERE updated_at >= (SELECT MAX(last_order_date) FROM {{ this }})
    {% else %}
    SELECT DISTINCT customer_key FROM orders
    {% endif %}
),

customer_orders AS (
    SELECT 
        o.customer_key,
        o.order_id,
        o.order_timestamp,
        o.total_collected
    FROM orders o
    {% if is_incremental() %}
    INNER JOIN changed_customers cc ON o.customer_key = cc.customer_key
    {% endif %}
),

aggregated AS (
    SELECT
        customer_key,
        
        -- [METRIC] Acquisition Date
        -- Definition: The timestamp of the very first order placed by the customer.
        MIN(order_timestamp) as first_order_date,
        
        -- [METRIC] Last Active Date
        -- Definition: The timestamp of the most recent order. Used for Recency calculation.
        MAX(order_timestamp) as last_order_date,
        
        -- [METRIC] Frequency
        -- Formula: COUNT(DISTINCT order_id)
        -- Note: We count distinct order_ids to handle potential duplicate rows in raw data (though deduped in staging).
        COUNT(DISTINCT order_id) as frequency,
        
        -- [METRIC] Monetary Value (Lifetime Value component)
        -- Formula: SUM(total_collected)
        -- Definition: Total amount collected from customer (after discounts, including tax).
        SUM(total_collected) as monetary_value
    FROM customer_orders
    GROUP BY customer_key
)

SELECT
    customer_key,
    first_order_date,
    last_order_date,
    
    -- [METRIC] Recency
    -- Formula: Current Date - Last Order Date (in days)
    date_diff('day', CAST(last_order_date AS DATE), current_date) as recency_days,
    
    frequency,
    monetary_value,
    
    -- [METRIC] Lifespan
    -- Formula: Last Order Date - First Order Date (in days)
    -- Meaning: How long the customer has been with us. 0 means they only made one purchase (or multiple on same day).
    date_diff('day', CAST(first_order_date AS DATE), CAST(last_order_date AS DATE)) as lifespan_days,
    
    current_timestamp as metric_calculated_at
FROM aggregated

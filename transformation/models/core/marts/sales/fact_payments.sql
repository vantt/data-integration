{{ config(
    tags=['mart', 'fact'],
    location="{{ get_rolling_location() }}"
) }}

WITH payments AS (
    SELECT * FROM {{ ref('std_payments') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(["coalesce(cast(payment_id as varchar), 'Unknown')"]) }} as payment_key,
    order_id,
    {{ dbt_utils.generate_surrogate_key(["coalesce(cast(payment_method_id as varchar), 'Unknown')"]) }} as payment_method_key,
    amount,
    status,
    created_at as payment_timestamp,
    paid_at as paid_on
FROM payments

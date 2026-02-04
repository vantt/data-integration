{{ config(
    tags=['mart', 'fact'],
    location="{{ get_rolling_location() }}"
) }}

WITH payments AS (
    SELECT * FROM {{ ref('stg_sapo_payments') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['payment_id']) }} as payment_key,
    order_id,
    {{ dbt_utils.generate_surrogate_key(['payment_method_id']) }} as payment_method_key,
    amount,
    status,
    created_on as payment_timestamp,
    paid_on
FROM payments

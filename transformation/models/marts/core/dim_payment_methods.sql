{{ config(
    tags=['mart', 'dim']
) }}

WITH payments AS (
    SELECT * FROM {{ ref('std_payments') }}
)

SELECT DISTINCT
    md5(payment_method_id) as payment_method_key,
    payment_method_id,
    payment_method_type
FROM payments
WHERE payment_method_id IS NOT NULL

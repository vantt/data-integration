{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

WITH payment_methods AS (
    SELECT * FROM {{ ref('ref_payment_methods') }}
)

SELECT DISTINCT
    {{ dbt_utils.generate_surrogate_key(['cast(id as string)']) }} as payment_method_key,
    cast(id as integer) as payment_method_id,
    name as payment_method_name,
    type as payment_method_type
FROM payment_methods
WHERE id IS NOT NULL

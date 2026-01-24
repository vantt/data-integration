

WITH payment_methods AS (
    SELECT * FROM "data_integration2"."main"."ref_payment_methods"
)

SELECT DISTINCT
    md5(cast(id as string)) as payment_method_key,
    cast(id as integer) as payment_method_id,
    name as payment_method_name,
    type as payment_method_type
FROM payment_methods
WHERE id IS NOT NULL
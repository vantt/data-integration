{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

WITH staff_source AS (
    SELECT * FROM {{ ref('stg_sapo_accounts') }}
)

SELECT DISTINCT
    -- Surrogate Key
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(['account_id']) }} as staff_key,
    
    account_id as staff_id,
    
    -- Name and Email from Accounts API
    staff_name as full_name,
    staff_email as email,
    staff_phone as phone_number

FROM staff_source
WHERE account_id IS NOT NULL

UNION ALL

SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as staff_key,
    '-1' as staff_id,
    'Unknown Staff' as full_name,
    'unknown@example.com' as email,
    NULL as phone_number

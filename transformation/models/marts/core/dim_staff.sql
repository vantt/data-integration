{{ config(
    tags=['mart', 'dim'],
    location="{{ get_rolling_location() }}"
) }}

WITH staff_source AS (
    SELECT * FROM {{ ref('std_accounts') }}
),

crm_users AS (
    SELECT crm_user_id, email FROM {{ ref('stg_crm__app_user') }}
    WHERE is_active = TRUE
)

SELECT DISTINCT
    -- Surrogate Key
    {{ dbt_utils.generate_surrogate_key(['account_id']) }} as staff_key,

    account_id as staff_id,

    -- Name and Email from Accounts API
    staff_name as full_name,
    staff_email as email,
    staff_phone as phone_number,

    -- CRM identity bridge (UUID → Sapo staff_id join key for cross-system reporting)
    cu.crm_user_id

FROM staff_source
LEFT JOIN crm_users cu ON lower(trim(cu.email)) = lower(trim(staff_email))
WHERE account_id IS NOT NULL

UNION ALL

SELECT
    {{ dbt_utils.generate_surrogate_key(["'Unknown'"]) }} as staff_key,
    '-1' as staff_id,
    'Unknown Staff' as full_name,
    'unknown@example.com' as email,
    NULL as phone_number,
    NULL as crm_user_id

-- name: GetAppUserByEmail :one
SELECT user_id, staff_id, email, full_name, role, is_active, created_at, updated_at
FROM crm_app_user
WHERE email = ?
LIMIT 1;

-- name: ListActiveAppUsers :many
SELECT user_id, staff_id, email, full_name, role, is_active, created_at, updated_at
FROM crm_app_user
WHERE is_active = 1
ORDER BY full_name;

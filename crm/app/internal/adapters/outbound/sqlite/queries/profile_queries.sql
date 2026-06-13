-- Customer profile queries (crm_customer_profile)

-- name: GetCustomerProfile :one
SELECT party_id, owner_user_id, lifecycle_stage, acquisition_source,
       birthday, address, preferences, custom, consent_contact,
       created_at, updated_at
FROM crm_customer_profile
WHERE party_id = ?
LIMIT 1;

-- name: UpsertCustomerProfile :exec
INSERT INTO crm_customer_profile (
  party_id, owner_user_id, lifecycle_stage, acquisition_source,
  birthday, address, preferences, custom, consent_contact,
  created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (party_id) DO UPDATE SET
  owner_user_id      = excluded.owner_user_id,
  lifecycle_stage    = excluded.lifecycle_stage,
  acquisition_source = excluded.acquisition_source,
  birthday           = excluded.birthday,
  address            = excluded.address,
  preferences        = excluded.preferences,
  custom             = excluded.custom,
  consent_contact    = excluded.consent_contact,
  updated_at         = strftime('%Y-%m-%dT%H:%M:%fZ', 'now');

-- name: UpdateCustomJSON :exec
UPDATE crm_customer_profile
SET custom     = ?,
    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
WHERE party_id = ?;

-- name: GetParty360 :one
SELECT
  party_id, party_type, display_name, primary_phone, primary_email,
  status, is_merged, party_created_at, party_updated_at,
  owner_user_id, lifecycle_stage, acquisition_source, birthday,
  address, preferences, custom, consent_contact, profile_updated_at,
  tags_json
FROM crm_party_360
WHERE party_id = ?
LIMIT 1;

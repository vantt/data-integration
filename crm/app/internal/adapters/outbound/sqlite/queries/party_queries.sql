-- Party golden-record queries

-- name: CreateParty :exec
INSERT INTO crm_party (
  party_id, party_type, display_name, primary_phone, primary_email,
  status, is_merged, merged_into, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

-- name: GetPartyByID :one
SELECT party_id, party_type, display_name, primary_phone, primary_email,
       status, is_merged, merged_into, created_at, updated_at
FROM crm_party
WHERE party_id = ?
LIMIT 1;

-- name: UpdateParty :exec
UPDATE crm_party
SET display_name  = ?,
    primary_phone = ?,
    primary_email = ?,
    status        = ?,
    is_merged     = ?,
    merged_into   = ?
WHERE party_id = ?;

-- name: ListPartiesByPhone :many
SELECT party_id, party_type, display_name, primary_phone, primary_email,
       status, is_merged, merged_into, created_at, updated_at
FROM crm_party
WHERE primary_phone = ?
  AND is_merged = 0;

-- name: ListPartiesByEmail :many
SELECT party_id, party_type, display_name, primary_phone, primary_email,
       status, is_merged, merged_into, created_at, updated_at
FROM crm_party
WHERE primary_email = ?
  AND is_merged = 0;

-- Party identity queries

-- name: UpsertPartyIdentity :exec
INSERT OR IGNORE INTO crm_party_identity (
  identity_id, party_id, source_system, identity_type, identity_value,
  confidence, is_primary, verified_at, source_contact_quality, contact_quality, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

-- name: FindPartyByIdentity :one
SELECT p.party_id, p.party_type, p.display_name, p.primary_phone, p.primary_email,
       p.status, p.is_merged, p.merged_into, p.created_at, p.updated_at
FROM crm_party p
JOIN crm_party_identity i ON i.party_id = p.party_id
WHERE i.identity_type = ?
  AND i.identity_value = ?
LIMIT 1;

-- name: ListIdentitiesByParty :many
SELECT identity_id, party_id, source_system, identity_type, identity_value,
       confidence, is_primary, verified_at, source_contact_quality, contact_quality, created_at
FROM crm_party_identity
WHERE party_id = ?
ORDER BY is_primary DESC, created_at;

-- name: UpdateIdentityContactQuality :exec
UPDATE crm_party_identity
SET contact_quality = ?
WHERE identity_id = ?;

-- name: ReassignIdentity :exec
UPDATE crm_party_identity
SET party_id = ?
WHERE identity_id = ?;

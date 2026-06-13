-- Tag and party-tag queries

-- name: ListTagsByCategory :many
SELECT tag_id, name, category, color
FROM crm_tag
WHERE category = ?
ORDER BY name;

-- name: ListAllTags :many
SELECT tag_id, name, category, color
FROM crm_tag
ORDER BY category, name;

-- name: GetTag :one
SELECT tag_id, name, category, color
FROM crm_tag
WHERE tag_id = ?
LIMIT 1;

-- name: CreateTag :exec
INSERT INTO crm_tag (tag_id, name, category, color)
VALUES (?, ?, ?, ?);

-- name: AttachPartyTag :exec
INSERT OR IGNORE INTO crm_party_tag (party_id, tag_id, tagged_by, tagged_at)
VALUES (?, ?, ?, ?);

-- name: DetachPartyTag :exec
DELETE FROM crm_party_tag
WHERE party_id = ? AND tag_id = ?;

-- name: ListPartyTags :many
SELECT t.tag_id, t.name, t.category, t.color
FROM crm_tag t
JOIN crm_party_tag pt ON pt.tag_id = t.tag_id
WHERE pt.party_id = ?
ORDER BY t.category, t.name;

-- Custom field definition queries

-- name: ListActiveCustomFieldDefs :many
SELECT field_id, entity_type, field_key, label, data_type,
       options, is_required, is_active, sort_order
FROM crm_custom_field_def
WHERE entity_type = ? AND is_active = 1
ORDER BY sort_order, field_key;

-- name: ListAllCustomFieldDefs :many
SELECT field_id, entity_type, field_key, label, data_type,
       options, is_required, is_active, sort_order
FROM crm_custom_field_def
WHERE entity_type = ?
ORDER BY sort_order, field_key;

-- name: GetCustomFieldDef :one
SELECT field_id, entity_type, field_key, label, data_type,
       options, is_required, is_active, sort_order
FROM crm_custom_field_def
WHERE field_id = ?
LIMIT 1;

-- name: InsertCustomFieldDef :exec
INSERT INTO crm_custom_field_def (
  field_id, entity_type, field_key, label, data_type,
  options, is_required, is_active, sort_order
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);

-- name: UpdateCustomFieldDef :exec
UPDATE crm_custom_field_def
SET label       = ?,
    options     = ?,
    is_required = ?,
    is_active   = ?,
    sort_order  = ?
WHERE field_id = ?;

-- Note queries (crm_note)

-- name: InsertNote :exec
INSERT INTO crm_note (note_id, party_id, body, author_user_id, created_at)
VALUES (?, ?, ?, ?, ?);

-- name: ListNotesByParty :many
SELECT note_id, party_id, body, author_user_id, created_at
FROM crm_note
WHERE party_id = ?
ORDER BY created_at DESC;

-- Task queries (crm_task)

-- name: InsertTask :exec
INSERT INTO crm_task (
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

-- name: GetTaskByID :one
SELECT
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
FROM crm_task
WHERE task_id = ?;

-- name: UpdateTask :exec
UPDATE crm_task
SET
  title            = ?,
  description      = ?,
  status           = ?,
  assignee_user_id = ?,
  due_at           = ?,
  completed_at     = ?,
  updated_at       = ?
WHERE task_id = ?;

-- name: ExistsTaskBySourceRef :one
SELECT COUNT(*) FROM crm_task
WHERE source = ? AND source_ref = ?;

-- name: ListTasksByAssigneeAndStatus :many
SELECT
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
FROM crm_task
WHERE assignee_user_id = ? AND status = ?
ORDER BY due_at ASC, priority DESC;

-- name: ListTasksByAssignee :many
SELECT
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
FROM crm_task
WHERE assignee_user_id = ?
ORDER BY due_at ASC, priority DESC;

-- name: ListTasksByStatus :many
SELECT
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
FROM crm_task
WHERE status = ?
ORDER BY due_at ASC, priority DESC;

-- name: ListAllTasks :many
SELECT
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
FROM crm_task
ORDER BY due_at ASC, priority DESC;

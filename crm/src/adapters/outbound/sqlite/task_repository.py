"""SQLite adapter implementing TaskRepository port for CRM.

Mirrors Go adapter (task_repo.go) — exact same SQL, same branching logic
for list_by_assignee_and_status filter combinations.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from domain.entities.task import Task
from adapters.outbound.sqlite.connection import CRMDatabase

# ---------------------------------------------------------------------------
# SQL (ported verbatim from task_queries.sql)
# ---------------------------------------------------------------------------

_INSERT = """
INSERT INTO crm_task (
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at,
  task_kind, channel, value_at_stake_vnd, top_affinity_product
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_GET_BY_ID = """
SELECT
  t.task_id, t.party_id, t.title, t.description, t.due_at, t.priority, t.status,
  t.assignee_user_id, t.source, t.source_ref, t.created_by, t.created_at, t.updated_at, t.completed_at,
  t.task_kind, t.channel, t.value_at_stake_vnd, t.top_affinity_product,
  p.display_name AS party_name,
  u.full_name AS assignee_name
FROM crm_task t
LEFT JOIN crm_party p ON p.party_id = t.party_id
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.task_id = ?
"""

_UPDATE = """
UPDATE crm_task
SET
  title            = ?,
  description      = ?,
  priority         = ?,
  status           = ?,
  assignee_user_id = ?,
  due_at           = ?,
  completed_at     = ?,
  task_kind        = ?,
  channel          = ?
WHERE task_id = ?
"""

_EXISTS_BY_SOURCE_REF = """
SELECT COUNT(*) FROM crm_task
WHERE source = ? AND source_ref = ?
"""

_GET_BY_SOURCE_REF = """
SELECT
  t.task_id, t.party_id, t.title, t.description, t.due_at, t.priority, t.status,
  t.assignee_user_id, t.source, t.source_ref, t.created_by, t.created_at, t.updated_at, t.completed_at,
  t.task_kind, t.channel, t.value_at_stake_vnd, t.top_affinity_product,
  p.display_name AS party_name,
  u.full_name AS assignee_name
FROM crm_task t
LEFT JOIN crm_party p ON p.party_id = t.party_id
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.source = ? AND t.source_ref = ? AND t.status NOT IN ('done', 'cancelled')
LIMIT 1
"""

_GET_CLAIMED_BY_ACTION_IDS = """
SELECT
  t.task_id, t.party_id, t.source_ref, t.assignee_user_id,
  COALESCE(u.full_name, t.assignee_user_id, 'nhân viên') AS assignee_name
FROM crm_task t
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.source = 'action_queue'
  AND t.source_ref IN ({placeholders})
  AND t.status NOT IN ('done', 'cancelled')
"""

_GET_CUSTOMER_CLAIM = """
SELECT
  t.task_id, t.party_id, t.title, t.description, t.due_at, t.priority, t.status,
  t.assignee_user_id, t.source, t.source_ref, t.created_by, t.created_at, t.updated_at, t.completed_at,
  t.task_kind, t.channel, t.value_at_stake_vnd, t.top_affinity_product,
  p.display_name AS party_name,
  COALESCE(u.full_name, t.assignee_user_id, 'nhân viên') AS assignee_name
FROM crm_task t
LEFT JOIN crm_party p ON p.party_id = t.party_id
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.source = 'action_queue_claim'
  AND t.party_id = ?
  AND t.status NOT IN ('done', 'cancelled')
LIMIT 1
"""

_LIST_BY_ASSIGNEE_AND_STATUS = """
SELECT
  t.task_id, t.party_id, t.title, t.description, t.due_at, t.priority, t.status,
  t.assignee_user_id, t.source, t.source_ref, t.created_by, t.created_at, t.updated_at, t.completed_at,
  t.task_kind, t.channel, t.value_at_stake_vnd, t.top_affinity_product,
  p.display_name AS party_name,
  u.full_name AS assignee_name
FROM crm_task t
LEFT JOIN crm_party p ON p.party_id = t.party_id
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.assignee_user_id = ? AND t.status = ?
ORDER BY t.due_at ASC, t.priority DESC
LIMIT ?
"""

_LIST_BY_ASSIGNEE = """
SELECT
  t.task_id, t.party_id, t.title, t.description, t.due_at, t.priority, t.status,
  t.assignee_user_id, t.source, t.source_ref, t.created_by, t.created_at, t.updated_at, t.completed_at,
  t.task_kind, t.channel, t.value_at_stake_vnd, t.top_affinity_product,
  p.display_name AS party_name,
  u.full_name AS assignee_name
FROM crm_task t
LEFT JOIN crm_party p ON p.party_id = t.party_id
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.assignee_user_id = ?
ORDER BY t.due_at ASC, t.priority DESC
LIMIT ?
"""

_LIST_BY_STATUS = """
SELECT
  t.task_id, t.party_id, t.title, t.description, t.due_at, t.priority, t.status,
  t.assignee_user_id, t.source, t.source_ref, t.created_by, t.created_at, t.updated_at, t.completed_at,
  t.task_kind, t.channel, t.value_at_stake_vnd, t.top_affinity_product,
  p.display_name AS party_name,
  u.full_name AS assignee_name
FROM crm_task t
LEFT JOIN crm_party p ON p.party_id = t.party_id
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.status = ?
ORDER BY t.due_at ASC, t.priority DESC
LIMIT ?
"""

_LIST_ALL = """
SELECT
  t.task_id, t.party_id, t.title, t.description, t.due_at, t.priority, t.status,
  t.assignee_user_id, t.source, t.source_ref, t.created_by, t.created_at, t.updated_at, t.completed_at,
  t.task_kind, t.channel, t.value_at_stake_vnd, t.top_affinity_product,
  p.display_name AS party_name,
  u.full_name AS assignee_name
FROM crm_task t
LEFT JOIN crm_party p ON p.party_id = t.party_id
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
ORDER BY t.due_at ASC, t.priority DESC
LIMIT ?
"""

_LIST_UNASSIGNED_BY_STATUS = """
SELECT
  t.task_id, t.party_id, t.title, t.description, t.due_at, t.priority, t.status,
  t.assignee_user_id, t.source, t.source_ref, t.created_by, t.created_at, t.updated_at, t.completed_at,
  t.task_kind, t.channel, t.value_at_stake_vnd, t.top_affinity_product,
  p.display_name AS party_name,
  u.full_name AS assignee_name
FROM crm_task t
LEFT JOIN crm_party p ON p.party_id = t.party_id
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.assignee_user_id IS NULL AND t.status = ?
ORDER BY t.due_at ASC, t.priority DESC
LIMIT ?
"""

_LIST_UNASSIGNED = """
SELECT
  t.task_id, t.party_id, t.title, t.description, t.due_at, t.priority, t.status,
  t.assignee_user_id, t.source, t.source_ref, t.created_by, t.created_at, t.updated_at, t.completed_at,
  t.task_kind, t.channel, t.value_at_stake_vnd, t.top_affinity_product,
  p.display_name AS party_name,
  u.full_name AS assignee_name
FROM crm_task t
LEFT JOIN crm_party p ON p.party_id = t.party_id
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.assignee_user_id IS NULL
ORDER BY t.due_at ASC, t.priority DESC
LIMIT ?
"""

_LIST_BY_PARTY = """
SELECT
  t.task_id, t.party_id, t.title, t.description, t.due_at, t.priority, t.status,
  t.assignee_user_id, t.source, t.source_ref, t.created_by, t.created_at, t.updated_at, t.completed_at,
  t.task_kind, t.channel, t.value_at_stake_vnd, t.top_affinity_product,
  p.display_name AS party_name,
  u.full_name AS assignee_name
FROM crm_task t
LEFT JOIN crm_party p ON p.party_id = t.party_id
LEFT JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.party_id = ?
ORDER BY t.due_at ASC, t.priority DESC
LIMIT ?
"""


# ---------------------------------------------------------------------------
# Row mapper
# ---------------------------------------------------------------------------

def _task_from_row(row: sqlite3.Row) -> Task:
    keys = row.keys()
    return Task(
        task_id=row["task_id"],
        title=row["title"],
        priority=int(row["priority"]),
        status=row["status"],
        source=row["source"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        party_id=row["party_id"],
        description=row["description"],
        due_at=row["due_at"],
        assignee_user_id=row["assignee_user_id"],
        source_ref=row["source_ref"],
        created_by=row["created_by"],
        completed_at=row["completed_at"],
        task_kind=row["task_kind"] if "task_kind" in keys else "contact",
        channel=row["channel"] if "channel" in keys else None,
        # Migration 0036: claim-context fields — None for pre-migration rows
        value_at_stake_vnd=row["value_at_stake_vnd"] if "value_at_stake_vnd" in keys else None,
        top_affinity_product=row["top_affinity_product"] if "top_affinity_product" in keys else None,
        party_name=row["party_name"] if "party_name" in keys else None,
        assignee_name=row["assignee_name"] if "assignee_name" in keys else None,
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class SQLiteTaskRepository:
    """SQLite implementation of TaskRepository.

    Duck-typed against domain.ports.task_repository.TaskRepository.
    """

    def __init__(self, db: CRMDatabase) -> None:
        self._conn = db.conn

    def insert(self, task: Task) -> Task:
        """Store a new task row and return the task."""
        self._conn.execute(_INSERT, (
            task.task_id,
            task.party_id,
            task.title,
            task.description,
            task.due_at,
            task.priority,
            task.status,
            task.assignee_user_id,
            task.source,
            task.source_ref,
            task.created_by,
            task.created_at,
            task.updated_at,
            task.completed_at,
            task.task_kind,
            task.channel,
            task.value_at_stake_vnd,
            task.top_affinity_product,
        ))
        return task

    def get_by_id(self, task_id: str) -> Optional[Task]:
        """Return a task by primary key, or None if not found."""
        row = self._conn.execute(_GET_BY_ID, (task_id,)).fetchone()
        return _task_from_row(row) if row is not None else None

    def update(self, task: Task) -> None:
        """Persist mutable task fields. updated_at is managed by DB trigger."""
        self._conn.execute(_UPDATE, (
            task.title,
            task.description,
            task.priority,
            task.status,
            task.assignee_user_id,
            task.due_at,
            task.completed_at,
            task.task_kind,
            task.channel,
            task.task_id,
        ))

    def list_by_assignee_and_status(
        self,
        assignee_id: str,
        statuses: list[str],
        limit: int = 100,
    ) -> list[Task]:
        """Return tasks filtered by assignee and/or status list.

        Mirrors Go branching: composite index query when both set, single-filter
        queries otherwise, full list when neither given.
        statuses is a list; if more than one status is provided a UNION is used
        (Go port only accepts a single status string; multiple statuses are a
        Python extension for callers that need them).
        """
        rows: list[sqlite3.Row] = []

        if assignee_id and statuses:
            # Use composite-index query per status value (mirrors Go single-status path
            # extended to support a list via iteration).
            for status in statuses:
                rows += self._conn.execute(
                    _LIST_BY_ASSIGNEE_AND_STATUS, (assignee_id, status, limit)
                ).fetchall()
        elif assignee_id:
            rows = self._conn.execute(_LIST_BY_ASSIGNEE, (assignee_id, limit)).fetchall()
        elif statuses:
            for status in statuses:
                rows += self._conn.execute(_LIST_BY_STATUS, (status, limit)).fetchall()
        else:
            rows = self._conn.execute(_LIST_ALL, (limit,)).fetchall()

        return [_task_from_row(r) for r in rows]

    def list_by_no_assignee(self, statuses: list[str], limit: int = 100) -> list[Task]:
        """Return unassigned tasks (assignee_user_id IS NULL) filtered by status list."""
        rows: list[sqlite3.Row] = []
        if statuses:
            for status in statuses:
                rows += self._conn.execute(
                    _LIST_UNASSIGNED_BY_STATUS, (status, limit)
                ).fetchall()
        else:
            rows = self._conn.execute(_LIST_UNASSIGNED, (limit,)).fetchall()
        return [_task_from_row(r) for r in rows]

    def list_by_party(self, party_id: str, limit: int = 100) -> list[Task]:
        """Return all tasks linked to a party, ordered by due date."""
        rows = self._conn.execute(_LIST_BY_PARTY, (party_id, limit)).fetchall()
        return [_task_from_row(r) for r in rows]

    def exists_by_source_ref(self, source: str, source_ref: str) -> bool:
        """Return True when a task with the given source + source_ref already exists."""
        row = self._conn.execute(_EXISTS_BY_SOURCE_REF, (source, source_ref)).fetchone()
        return bool(row[0]) if row is not None else False

    def get_by_source_ref(self, source: str, source_ref: str) -> Optional[Task]:
        """Return the active task matching source+source_ref, or None if not found / already done."""
        row = self._conn.execute(_GET_BY_SOURCE_REF, (source, source_ref)).fetchone()
        return _task_from_row(row) if row is not None else None

    def get_customer_claim(self, party_id: str) -> Optional[Task]:
        """Return the active per-customer claim task (source='action_queue_claim'), or None."""
        row = self._conn.execute(_GET_CUSTOMER_CLAIM, (party_id,)).fetchone()
        if row is None:
            return None
        return _task_from_row(row)

    def get_customer_claim_info(self, party_id: str) -> Optional[dict]:
        """Return {task_id, assignee_user_id, assignee_name} for active customer claim, or None."""
        row = self._conn.execute(_GET_CUSTOMER_CLAIM, (party_id,)).fetchone()
        if row is None:
            return None
        return {
            "task_id": row["task_id"],
            "assignee_user_id": row["assignee_user_id"],
            "assignee_name": row["assignee_name"],
        }

    def get_claimed_tasks_by_action_ids(self, action_ids: list) -> dict:
        """Return {action_id: {task_id, party_id, assignee_user_id, assignee_name}} for active claimed tasks.

        Batch query — one round-trip for all action_ids of a customer.
        """
        if not action_ids:
            return {}
        placeholders = ",".join("?" * len(action_ids))
        sql = _GET_CLAIMED_BY_ACTION_IDS.format(placeholders=placeholders)
        rows = self._conn.execute(sql, action_ids).fetchall()
        return {
            row["source_ref"]: {
                "task_id": row["task_id"],
                "party_id": row["party_id"],
                "assignee_user_id": row["assignee_user_id"],
                "assignee_name": row["assignee_name"],
            }
            for row in rows
        }

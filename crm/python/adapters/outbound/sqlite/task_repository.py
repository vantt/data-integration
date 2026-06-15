"""SQLite adapter implementing TaskRepository port for CRM.

Mirrors Go adapter (task_repo.go) — exact same SQL, same branching logic
for list_by_assignee_and_status filter combinations.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from crm.python.domain.entities.task import Task
from crm.python.adapters.outbound.sqlite.connection import CRMDatabase

# ---------------------------------------------------------------------------
# SQL (ported verbatim from task_queries.sql)
# ---------------------------------------------------------------------------

_INSERT = """
INSERT INTO crm_task (
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_GET_BY_ID = """
SELECT
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
FROM crm_task
WHERE task_id = ?
"""

_UPDATE = """
UPDATE crm_task
SET
  title            = ?,
  description      = ?,
  status           = ?,
  assignee_user_id = ?,
  due_at           = ?,
  completed_at     = ?,
  updated_at       = ?
WHERE task_id = ?
"""

_EXISTS_BY_SOURCE_REF = """
SELECT COUNT(*) FROM crm_task
WHERE source = ? AND source_ref = ?
"""

_LIST_BY_ASSIGNEE_AND_STATUS = """
SELECT
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
FROM crm_task
WHERE assignee_user_id = ? AND status = ?
ORDER BY due_at ASC, priority DESC
LIMIT ?
"""

_LIST_BY_ASSIGNEE = """
SELECT
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
FROM crm_task
WHERE assignee_user_id = ?
ORDER BY due_at ASC, priority DESC
LIMIT ?
"""

_LIST_BY_STATUS = """
SELECT
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
FROM crm_task
WHERE status = ?
ORDER BY due_at ASC, priority DESC
LIMIT ?
"""

_LIST_ALL = """
SELECT
  task_id, party_id, title, description, due_at, priority, status,
  assignee_user_id, source, source_ref, created_by, created_at, updated_at, completed_at
FROM crm_task
ORDER BY due_at ASC, priority DESC
LIMIT ?
"""


# ---------------------------------------------------------------------------
# Row mapper
# ---------------------------------------------------------------------------

def _task_from_row(row: sqlite3.Row) -> Task:
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
        ))
        self._conn.commit()
        return task

    def get_by_id(self, task_id: str) -> Optional[Task]:
        """Return a task by primary key, or None if not found."""
        row = self._conn.execute(_GET_BY_ID, (task_id,)).fetchone()
        return _task_from_row(row) if row is not None else None

    def update(self, task_id: str, **kwargs) -> None:
        """Persist mutable task fields. kwargs override the current row values.

        Requires a prior get_by_id to supply all update fields. Caller must
        pass at minimum: title, description, status, assignee_user_id, due_at,
        completed_at, updated_at.
        """
        self._conn.execute(_UPDATE, (
            kwargs["title"],
            kwargs.get("description"),
            kwargs["status"],
            kwargs.get("assignee_user_id"),
            kwargs.get("due_at"),
            kwargs.get("completed_at"),
            kwargs["updated_at"],
            task_id,
        ))
        self._conn.commit()

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

    def exists_by_source_ref(self, source: str, source_ref: str) -> bool:
        """Return True when a task with the given source + source_ref already exists."""
        row = self._conn.execute(_EXISTS_BY_SOURCE_REF, (source, source_ref)).fetchone()
        return bool(row[0]) if row is not None else False

"""Application service — TaskService: manual task CRUD + auto-generation from wh_action_queue.

Pure domain + ports only; no adapter imports.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from domain.entities.task import (
    Task,
    TASK_STATUS_OPEN,
    TASK_STATUS_DONE,
    TASK_STATUS_CANCELLED,
    VALID_TASK_STATUSES,
    TASK_ALLOWED_TRANSITIONS,
    TASK_SOURCE_MANUAL,
    TASK_SOURCE_ACTION_QUEUE,
)
from domain.ports.task_repository import TaskRepository
from domain.ports.party_repository import PartyRepository
from domain.ports.cache_repository import CacheRepository

log = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskService:
    """Handles task creation, assignment, status transitions,
    and auto-generation from the warehouse action queue."""

    def __init__(
        self,
        task_repo: TaskRepository,
        party_repo: PartyRepository,
        cache_repo: CacheRepository,
    ) -> None:
        self._task_repo = task_repo
        self._party_repo = party_repo
        self._cache_repo = cache_repo

    # ------------------------------------------------------------------
    # Manual CRUD
    # ------------------------------------------------------------------

    def create_task(self, task_data: dict) -> Task:
        """Validate and store a manually-created task. Returns the Task."""
        title = (task_data.get("title") or "").strip()
        if not title:
            raise ValueError("title is required")

        now = _utc_now()
        task = Task(
            task_id=task_data.get("task_id") or str(uuid.uuid4()),
            title=title,
            priority=task_data.get("priority", 0),
            status=task_data.get("status") or TASK_STATUS_OPEN,
            source=task_data.get("source") or TASK_SOURCE_MANUAL,
            created_at=now,
            updated_at=now,
            party_id=task_data.get("party_id"),
            description=task_data.get("description"),
            due_at=task_data.get("due_at"),
            assignee_user_id=task_data.get("assignee_user_id"),
            source_ref=task_data.get("source_ref"),
            created_by=task_data.get("created_by"),
        )
        self._task_repo.insert(task)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Return a task by ID, or None if not found."""
        return self._task_repo.get_by_id(task_id)

    def update_task(self, task_id: str, data: dict) -> Task:
        """Update editable fields (title, description, due_at, priority, assignee)."""
        task = self._task_repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id!r} not found")
        if data.get("title"):
            task.title = data["title"]
        if "description" in data:
            task.description = data["description"] or None
        if "due_at" in data:
            task.due_at = data["due_at"] or None
        if "priority" in data:
            task.priority = int(data["priority"])
        if "assignee_user_id" in data:
            task.assignee_user_id = data["assignee_user_id"] or None
        self._task_repo.update(task)
        return task

    def assign_task(self, task_id: str, assignee_id: str) -> None:
        """Assign a task to a staff user."""
        task = self._task_repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id!r} not found")
        task.assignee_user_id = assignee_id
        # updated_at is owned by the DB trigger — no app-side stamp needed.
        self._task_repo.update(task)

    def transition_status(self, task_id: str, new_status: str) -> Task:
        """Apply a status change, enforcing domain transition rules.

        Allowed transitions: open→doing→done, open→cancelled.
        done/cancelled→open (re-open) is also permitted.
        """
        if new_status not in VALID_TASK_STATUSES:
            raise ValueError(f"invalid task status {new_status!r}")

        task = self._task_repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id!r} not found")

        allowed = TASK_ALLOWED_TRANSITIONS.get(task.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"cannot transition task from {task.status!r} to {new_status!r}; "
                f"allowed: {allowed}"
            )

        task.status = new_status
        # updated_at is owned by the DB trigger — no app-side stamp needed.
        if new_status in (TASK_STATUS_DONE, TASK_STATUS_CANCELLED):
            task.completed_at = _utc_now()
        else:
            task.completed_at = None

        self._task_repo.update(task)
        return task

    def list_tasks(
        self,
        assignee_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[Task]:
        """Return tasks filtered by optional assignee and/or status."""
        tasks = self._task_repo.list_by_assignee_and_status(
            assignee_user_id=assignee_id or "",
            status=status or "",
        )
        return tasks[:limit]

    # ------------------------------------------------------------------
    # Auto-generation from warehouse action queue
    # ------------------------------------------------------------------

    def generate_tasks_from_action_queue(self, assignee_id: Optional[str] = None) -> int:
        """Read wh_action_queue and convert each unprocessed action into a crm_task.

        Idempotency: actions already converted are skipped (exists_by_source_ref).
        Party resolution: action.customer_key → sapo_customer identity → party_id.
        If no party found, party_id is left None (task still created).
        Cache absent: returns 0 gracefully.

        Returns the number of tasks created.
        """
        actions = self._cache_repo.list_all_action_queue()
        if not actions:
            return 0

        created = 0
        skipped = 0
        for action in actions:
            try:
                n = self._process_action(action, assignee_id)
            except Exception as exc:
                log.error("task service: action %s: %s", action.action_id, exc)
                continue
            created += n
            if n == 0:
                skipped += 1

        log.info(
            "task service: action_queue → %d tasks created, %d skipped (duplicate)",
            created,
            skipped,
        )
        return created

    def _process_action(self, action, assignee_id: Optional[str]) -> int:
        """Convert one ActionQueueItem into a task.

        Returns 1 when created, 0 when skipped as duplicate.
        """
        if self._task_repo.exists_by_source_ref(TASK_SOURCE_ACTION_QUEUE, action.action_id):
            return 0

        # Resolve customer_key → party_id via sapo_customer identity.
        party_id: Optional[str] = None
        if action.customer_key:
            try:
                party = self._party_repo.find_by_identity("sapo_customer", action.customer_key)
                if party is not None:
                    party_id = party.party_id
            except Exception as exc:
                log.warning(
                    "task service: resolve party for customer_key=%s: %s",
                    action.customer_key,
                    exc,
                )
                # Non-fatal — create task without party link.

        rationale = action.rationale_vi or ""
        if rationale:
            label = rationale[:80]
        else:
            label = action.customer_key
        title = f"[{action.action_type}] {label}"

        now = _utc_now()
        source_ref = action.action_id
        task = Task(
            task_id=str(uuid.uuid4()),
            party_id=party_id,
            title=title,
            description=rationale or None,
            priority=action.priority,
            status=TASK_STATUS_OPEN,
            source=TASK_SOURCE_ACTION_QUEUE,
            source_ref=source_ref,
            assignee_user_id=assignee_id,
            created_at=now,
            updated_at=now,
        )
        self._task_repo.insert(task)
        return 1

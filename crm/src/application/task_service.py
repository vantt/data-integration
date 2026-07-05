"""Application service — TaskService: manual task CRUD + auto-generation from wh_action_queue.

Pure domain + ports only; no adapter imports.
"""
from __future__ import annotations

import logging
import uuid
from shared.timestamps import utc_now
from typing import TYPE_CHECKING, Optional

from domain.entities.task import (
    Task,
    TASK_STATUS_OPEN,
    TASK_STATUS_DONE,
    TASK_STATUS_CANCELLED,
    VALID_TASK_STATUSES,
    TASK_ALLOWED_TRANSITIONS,
    TASK_SOURCE_MANUAL,
    TASK_SOURCE_ACTION_QUEUE,
    TASK_SOURCE_ACTION_QUEUE_CLAIM,
)
from domain.ports.task_repository import TaskRepository
from domain.ports.cache_repository import CacheRepository
from application.task_kind import derive_task_kind

if TYPE_CHECKING:
    from adapters.outbound.sqlite.connection import CRMDatabase

log = logging.getLogger(__name__)


class TaskService:
    """Handles task creation, assignment, status transitions,
    and auto-generation from the warehouse action queue."""

    def __init__(
        self,
        task_repo: TaskRepository,
        cache_repo: CacheRepository,
        db: Optional[CRMDatabase] = None,
    ) -> None:
        self._task_repo = task_repo
        self._cache_repo = cache_repo
        self._db = db

    # ------------------------------------------------------------------
    # Manual CRUD
    # ------------------------------------------------------------------

    def create_task(self, task_data: dict) -> Task:
        """Validate and store a manually-created task. Returns the Task."""
        title = (task_data.get("title") or "").strip()
        if not title:
            raise ValueError("title is required")

        source = task_data.get("source") or TASK_SOURCE_MANUAL
        source_ref = task_data.get("source_ref")
        party_id = task_data.get("party_id")

        # Derive task_kind unless the caller supplies an explicit value.
        explicit_kind = task_data.get("task_kind") or ""
        if explicit_kind:
            task_kind = explicit_kind
        else:
            task_kind, _ = derive_task_kind(
                source=source,
                source_ref=source_ref,
                party_id=party_id,
                action_type=task_data.get("action_type"),
            )

        now = utc_now()
        task = Task(
            task_id=task_data.get("task_id") or str(uuid.uuid4()),
            title=title,
            priority=task_data.get("priority", 0),
            status=task_data.get("status") or TASK_STATUS_OPEN,
            source=source,
            created_at=now,
            updated_at=now,
            party_id=party_id,
            description=task_data.get("description"),
            due_at=task_data.get("due_at"),
            assignee_user_id=task_data.get("assignee_user_id"),
            source_ref=source_ref,
            created_by=task_data.get("created_by"),
            task_kind=task_kind,
        )
        self._task_repo.insert(task)
        if self._db:
            self._db.commit()
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
        if self._db:
            self._db.commit()
        return task

    def assign_task(self, task_id: str, assignee_id: str) -> None:
        """Assign a task to a staff user."""
        task = self._task_repo.get_by_id(task_id)
        if task is None:
            raise ValueError(f"task {task_id!r} not found")
        task.assignee_user_id = assignee_id
        # updated_at is owned by the DB trigger — no app-side stamp needed.
        self._task_repo.update(task)
        if self._db:
            self._db.commit()

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
            task.completed_at = utc_now()
        else:
            task.completed_at = None

        self._task_repo.update(task)
        if self._db:
            self._db.commit()
        return task

    def list_unassigned(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[Task]:
        """Return open tasks with no assignee (team queue)."""
        return self._task_repo.list_by_no_assignee(
            [status] if status else [],
            limit,
        )

    def assign_to(self, task_id: str, user_id: str) -> None:
        """Assign a task to a user (self-assign from team queue)."""
        self.assign_task(task_id, user_id)

    def claim_customer_actions(self, party_id: str, actions: list, assignee_id: str) -> tuple:
        """Claim all action items for a customer by creating one per-customer task.

        Returns (task, is_new). is_new=False when already claimed by someone.
        One call per customer — regardless of how many action items exist.
        """
        existing = self._task_repo.get_customer_claim(party_id)
        if existing is not None:
            return existing, False

        count = len(actions)
        customer_name = getattr(actions[0], "customer_name", None) if actions else None
        title = f"Gọi {customer_name or party_id} · {count} hành động"
        lines = [f"[{a.action_type}] {(getattr(a, 'rationale_vi', '') or '').strip()}" for a in actions]
        description = "\n".join(lines) if lines else None
        priority = max((getattr(a, "priority", 1) for a in actions), default=1)

        # Capture action-queue context at claim time (migration 0036)
        value_at_stake_vnd = sum(getattr(a, "value_at_stake_vnd", 0) or 0 for a in actions)
        best_action = max(
            actions,
            key=lambda a: getattr(a, "value_at_stake_vnd", 0) or 0,
            default=None,
        )
        top_affinity_product = (
            (getattr(best_action, "top_affinity_product", "") or "").strip()
            if best_action else ""
        )

        now = utc_now()
        task = Task(
            task_id=str(uuid.uuid4()),
            party_id=party_id,
            title=title,
            description=description,
            priority=priority,
            status=TASK_STATUS_OPEN,
            source=TASK_SOURCE_ACTION_QUEUE_CLAIM,
            source_ref=party_id,
            assignee_user_id=assignee_id,
            created_at=now,
            updated_at=now,
            task_kind="contact",  # claim always means outreach to a customer
            value_at_stake_vnd=value_at_stake_vnd or None,  # store None if sum is 0
            top_affinity_product=top_affinity_product or None,
        )
        self._task_repo.insert(task)
        if self._db:
            self._db.commit()
        return task, True

    def unclaim_customer_actions(self, party_id: str) -> bool:
        """Cancel the per-customer claim task, returning all actions to the unclaimed queue."""
        existing = self._task_repo.get_customer_claim(party_id)
        if existing is None:
            return False
        existing.status = TASK_STATUS_CANCELLED
        existing.completed_at = utc_now()
        self._task_repo.update(existing)
        if self._db:
            self._db.commit()
        return True

    def auto_claim_from_contact(self, party_id: str, customer_name: str, assignee_id: str) -> tuple:
        """Create a minimal claim task when contact is logged without prior claiming.

        Called from the activity route when staff contacts a customer without
        having clicked "Nhận việc" first — ensures ownership is always captured.
        Returns (task, is_new). is_new=False when a claim task already exists.
        Idempotent via the (source, source_ref) unique index on crm_task.
        """
        existing = self._task_repo.get_customer_claim(party_id)
        if existing is not None:
            return existing, False

        now = utc_now()
        task = Task(
            task_id=str(uuid.uuid4()),
            party_id=party_id,
            title=f"Liên hệ {customer_name or party_id}",
            priority=0,
            status=TASK_STATUS_OPEN,
            source=TASK_SOURCE_ACTION_QUEUE_CLAIM,
            source_ref=party_id,
            assignee_user_id=assignee_id,
            created_at=now,
            updated_at=now,
            task_kind="contact",  # auto-claim from contact activity → outreach
        )
        self._task_repo.insert(task)
        if self._db:
            self._db.commit()
        return task, True

    def unclaim_action_item(self, action_id: str) -> bool:
        """Cancel the active task for an action item, returning it to the unclaimed queue.

        Returns True when a task was found and cancelled, False when no active task exists.
        """
        existing = self._task_repo.get_by_source_ref(TASK_SOURCE_ACTION_QUEUE, action_id)
        if existing is None:
            return False
        existing.status = TASK_STATUS_CANCELLED
        existing.completed_at = utc_now()
        self._task_repo.update(existing)
        if self._db:
            self._db.commit()
        return True

    def claim_action_item(
        self, action_id: str, action, assignee_id: str
    ) -> tuple:
        """Claim an action item by creating a task assigned to assignee_id.

        Returns (task, is_new). is_new=False when the action was already claimed.
        Idempotent: a second claim attempt returns the existing task, not an error.
        """
        existing = self._task_repo.get_by_source_ref(TASK_SOURCE_ACTION_QUEUE, action_id)
        if existing is not None:
            return existing, False

        rationale = (getattr(action, "rationale_vi", None) or "").strip()
        label = rationale[:80] if rationale else getattr(action, "customer_key", action_id)
        title = f"[{action.action_type}] {label}"

        action_party_id = getattr(action, "party_id", None)
        action_type = getattr(action, "action_type", None)
        kind, _ = derive_task_kind(
            source=TASK_SOURCE_ACTION_QUEUE,
            source_ref=action_id,
            party_id=action_party_id,
            action_type=action_type,
        )

        now = utc_now()
        task = Task(
            task_id=str(uuid.uuid4()),
            party_id=action_party_id,
            title=title,
            description=rationale or None,
            priority=getattr(action, "priority", 1),
            status=TASK_STATUS_OPEN,
            source=TASK_SOURCE_ACTION_QUEUE,
            source_ref=action_id,
            assignee_user_id=assignee_id,
            created_at=now,
            updated_at=now,
            task_kind=kind,
        )
        self._task_repo.insert(task)
        if self._db:
            self._db.commit()
        return task, True

    def list_tasks(
        self,
        assignee_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[Task]:
        """Return tasks filtered by optional assignee and/or status."""
        tasks = self._task_repo.list_by_assignee_and_status(
            assignee_id or "",
            [status] if status else [],
            limit,
        )
        return tasks

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

        # party_id is pre-resolved by list_all_action_queue via crm_party_identity JOIN.
        party_id: Optional[str] = action.party_id

        rationale = action.rationale_vi or ""
        if rationale:
            label = rationale[:80]
        else:
            label = action.customer_key
        title = f"[{action.action_type}] {label}"

        kind, _ = derive_task_kind(
            source=TASK_SOURCE_ACTION_QUEUE,
            source_ref=action.action_id,
            party_id=party_id,
            action_type=action.action_type,
        )

        now = utc_now()
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
            task_kind=kind,
        )
        self._task_repo.insert(task)
        if self._db:
            self._db.commit()
        return 1

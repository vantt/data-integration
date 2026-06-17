from __future__ import annotations

from typing import Protocol

from domain.entities.task import Task


class TaskRepository(Protocol):
    """Outbound port for Task persistence."""

    def insert(self, task: Task) -> None:
        """Store a new task row."""
        ...

    def get_by_id(self, task_id: str) -> Task | None:
        """Return a task by primary key, or None if not found."""
        ...

    def update(self, task: Task) -> None:
        """Persist mutable task fields (status, assignee, due_at, completed_at, updated_at)."""
        ...

    def list_by_assignee_and_status(
        self, assignee_user_id: str, status: str
    ) -> list[Task]:
        """Return tasks filtered by assignee and/or status.
        Empty string means 'any' for that filter."""
        ...

    def exists_by_source_ref(self, source: str, source_ref: str) -> bool:
        """Return True when a task with the given source + source_ref already exists.
        Used for idempotency in generate_tasks_from_action_queue."""
        ...

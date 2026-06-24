"""HTTP adapter — Task endpoints.

Auth: POST/PATCH mutations require X-CRM-Token header (CRM_API_TOKEN env var).
GET endpoints are read-only and unauthenticated.
"""
from __future__ import annotations

import dataclasses
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from adapters.inbound.http.auth_dependency import require_api_token
from application.task_service import TaskService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── request schemas ───────────────────────────────────────────────────────────

class CreateTaskRequest(BaseModel):
    title: str
    priority: int = 0
    party_id: str | None = None
    description: str | None = None
    due_at: str | None = None
    assignee_user_id: str | None = None
    created_by: str | None = None


class UpdateTaskRequest(BaseModel):
    status: str | None = None
    assignee_user_id: str | None = None


class GenerateTasksRequest(BaseModel):
    assignee_user_id: str | None = None


# ── dependency holder ─────────────────────────────────────────────────────────

_svc: TaskService | None = None


def wire_task_router(svc: TaskService) -> None:
    """Bind the application service; called during app startup."""
    global _svc
    _svc = svc


def _service() -> TaskService:
    if _svc is None:
        raise RuntimeError("TaskService not wired")
    return _svc


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/tasks", status_code=201, dependencies=[Depends(require_api_token)])
def create_task(req: CreateTaskRequest):
    """POST /api/tasks — create a manual task."""
    try:
        task = _service().create_task(req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error("task handler: create_task: %s", exc)
        raise HTTPException(status_code=500, detail="operation failed")
    return JSONResponse(status_code=201, content=dataclasses.asdict(task))


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    """GET /api/tasks/{id} — fetch a single task."""
    try:
        task = _service().get_task(task_id)
    except Exception as exc:
        log.error("task handler: get_task %s: %s", task_id, exc)
        raise HTTPException(status_code=500, detail="failed to get task")
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return dataclasses.asdict(task)


@router.patch("/tasks/{task_id}", dependencies=[Depends(require_api_token)])
def update_task(task_id: str, req: UpdateTaskRequest):
    """PATCH /api/tasks/{id} — update status and/or assignee."""
    svc = _service()
    try:
        if req.assignee_user_id is not None:
            svc.assign_task(task_id, req.assignee_user_id)
        if req.status is not None:
            svc.transition_status(task_id, req.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        log.error("task handler: update_task %s: %s", task_id, exc)
        raise HTTPException(status_code=500, detail="operation failed")
    return {"status": "ok", "task_id": task_id}


@router.get("/tasks")
def list_tasks(assignee: str = "", status: str = "", limit: int = 100):
    """GET /api/tasks?assignee=<user_id>&status=<status> — list tasks."""
    try:
        tasks = _service().list_tasks(
            assignee_id=assignee or None,
            status=status or None,
            limit=limit,
        )
    except Exception as exc:
        log.error("task handler: list_tasks: %s", exc)
        raise HTTPException(status_code=500, detail="failed to list tasks")
    return {"tasks": [dataclasses.asdict(t) for t in tasks]}


@router.post("/tasks/generate", dependencies=[Depends(require_api_token)])
def generate_tasks(req: GenerateTasksRequest):
    """POST /api/tasks/generate — batch-generate tasks from wh_action_queue."""
    try:
        n = _service().generate_tasks_from_action_queue(
            assignee_id=req.assignee_user_id
        )
    except Exception as exc:
        log.error("task handler: generate_tasks: %s", exc)
        raise HTTPException(status_code=500, detail="failed to generate tasks")
    return {"tasks_created": n}

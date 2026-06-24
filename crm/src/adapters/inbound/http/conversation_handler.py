"""FastAPI router: Conversation inbox + Messenger ingest endpoints.

Auth:
  PATCH /api/conversations/{id}  — requires X-CRM-Token (CRM_API_TOKEN env var).
  GET endpoints                   — unauthenticated (read-only).
  POST /api/conversations/messenger/ingest — NO CRM token (external FB webhook;
      Facebook signs payloads with X-Hub-Signature-256, not our internal token).
"""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from adapters.inbound.http.auth_dependency import require_api_token
from application.conversation_service import ConversationService
from application.messenger_parser import parse_messenger_webhook

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------------

class UpdateConversationBody(BaseModel):
    assignee_user_id: Optional[str] = None
    status: Optional[str] = None


# ---------------------------------------------------------------------------
# Dependency helper (router-level service injection via app.state)
# ---------------------------------------------------------------------------

def _svc(request: Request) -> ConversationService:
    return request.app.state.conversation_service


# ---------------------------------------------------------------------------
# GET /api/conversations?assignee=<user_id>&status=<status>
# ---------------------------------------------------------------------------

@router.get("/conversations")
def list_conversations(
    request: Request,
    assignee: str = "",
    status: str = "",
):
    svc = _svc(request)
    convs = svc.list_inbox(assignee_user_id=assignee, status=status)
    return {"conversations": [asdict(c) for c in convs]}


# ---------------------------------------------------------------------------
# PATCH /api/conversations/{id}
# ---------------------------------------------------------------------------

@router.patch("/conversations/{conversation_id}", dependencies=[Depends(require_api_token)])
def update_conversation(
    conversation_id: str,
    body: UpdateConversationBody,
    request: Request,
):
    svc = _svc(request)

    if body.assignee_user_id is not None:
        try:
            svc.assign_conversation(conversation_id, body.assignee_user_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            log.error("assign conversation %s: %s", conversation_id, exc)
            raise HTTPException(status_code=500, detail="operation failed")

    if body.status is not None:
        try:
            svc.set_status(conversation_id, body.status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            log.error("set status %s: %s", conversation_id, exc)
            raise HTTPException(status_code=500, detail="operation failed")

    return {"status": "ok", "conversation_id": conversation_id}


# ---------------------------------------------------------------------------
# GET /api/conversations/{id}/messages
# ---------------------------------------------------------------------------

@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: str, request: Request):
    svc = _svc(request)
    msgs = svc.list_messages(conversation_id)
    return {"conversation_id": conversation_id, "messages": [asdict(m) for m in msgs]}


# ---------------------------------------------------------------------------
# POST /api/conversations/messenger/ingest
# Accepts a raw FB Messenger webhook payload JSON.
# Auth/FB signature verification: TODO — deferred until live token is available.
# ---------------------------------------------------------------------------

@router.post("/conversations/messenger/ingest")
async def messenger_ingest(request: Request):
    body = await request.body()
    if len(body) > 1 << 20:  # 1 MiB cap
        raise HTTPException(status_code=413, detail="payload too large")

    try:
        payload = __import__("json").loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    try:
        parsed = parse_messenger_webhook(payload)
    except Exception as exc:
        log.error("parse messenger payload: %s", exc)
        raise HTTPException(status_code=400, detail="invalid messenger payload")

    svc = _svc(request)
    ingested, skipped = 0, 0
    for msg in parsed:
        try:
            svc.ingest_message(msg)
            ingested += 1
        except Exception as exc:
            log.error("ingest message %s: %s", msg.external_message_id, exc)
            skipped += 1

    return {"parsed": len(parsed), "ingested": ingested, "skipped": skipped}

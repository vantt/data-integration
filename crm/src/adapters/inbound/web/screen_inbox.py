"""Web adapter — S05 Inbox + S06 Conversation Detail screens.

FastAPI router mirroring screen_inbox.go.
Serves full inbox list page and conversation detail page/fragment.
No business logic — thin adapter only.
"""
from __future__ import annotations

import logging
from typing import Optional, Protocol

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crm.src.domain.entities.conversation import Conversation, Message
from crm.src.domain.entities.app_user import AppUser
from crm.src.domain.entities.party import Party

log = logging.getLogger(__name__)

# ── Service protocols ─────────────────────────────────────────────────────────

class ConversationLister(Protocol):
    def list_inbox(self, assignee: str, status: str) -> list[Conversation]: ...
    def get_messages(self, conv_id: str) -> list[Message]: ...


class ConvReader(Protocol):
    def get_by_id(self, conv_id: str) -> Optional[Conversation]: ...


class ConvWriter(Protocol):
    def assign_conversation(self, conv_id: str, assignee_user_id: str) -> None: ...
    def set_status(self, conv_id: str, status: str) -> None: ...
    def link_party(self, conv_id: str, party_id: str) -> None: ...


class PartyReader(Protocol):
    def get_by_id(self, party_id: str) -> Optional[Party]: ...
    def search_by_name(self, q: str) -> list[str]: ...


class AppUserLister(Protocol):
    def list_active(self) -> list[AppUser]: ...


class ActivityLogger(Protocol):
    def log_activity(self, activity_data: dict) -> object: ...


# ── Helpers ───────────────────────────────────────────────────────────────────

def _conv_status_bdg(status: str) -> str:
    return {"open": "bdg--good", "pending": "bdg--warn", "closed": ""}.get(status, "")


def _conv_party_names(
    convs: list[Conversation], party_reader: PartyReader
) -> dict[str, str]:
    """Build partyID → displayName for all conversations that have a linked party."""
    out: dict[str, str] = {}
    for c in convs:
        if c.party_id is None or c.party_id in out:
            continue
        try:
            p = party_reader.get_by_id(c.party_id)
            if p:
                out[c.party_id] = p.display_name
        except Exception:
            pass
    return out


# ── Router factory ────────────────────────────────────────────────────────────

def make_inbox_router(
    templates: Jinja2Templates,
    conversations: ConversationLister,
    conv_reader: ConvReader,
    conv_writer: ConvWriter,
    parties: PartyReader,
    app_users: AppUserLister,
    activity_log: ActivityLogger,
) -> APIRouter:
    """Return APIRouter wired with all Inbox + Conversation Detail routes."""
    router = APIRouter()

    # ── S05 Inbox list ────────────────────────────────────────────────────────

    @router.get("/inbox", response_class=HTMLResponse)
    async def handle_inbox(request: Request) -> Response:
        status = request.query_params.get("status", "")
        assignee = request.query_params.get("assignee", "")
        try:
            convs = conversations.list_inbox(assignee, status)
        except Exception as exc:
            log.error("inbox: list: %s", exc)
            convs = []
        party_names = _conv_party_names(convs, parties)
        return templates.TemplateResponse(
            "inbox.html",
            {
                "request": request,
                "convs": convs,
                "party_names": party_names,
                "status_filter": status,
                "assignee_filter": assignee,
                "conv_status_bdg": _conv_status_bdg,
            },
        )

    # ── S06 Conversation detail ───────────────────────────────────────────────

    @router.get("/inbox/{conv_id}", response_class=HTMLResponse)
    async def handle_conversation_detail(request: Request, conv_id: str) -> Response:
        conv = conv_reader.get_by_id(conv_id)
        if conv is None:
            return HTMLResponse("Không tìm thấy hội thoại", status_code=404)
        try:
            msgs = conversations.get_messages(conv_id)
        except Exception as exc:
            log.error("conv detail: get messages %s: %s", conv_id, exc)
            msgs = []
        party_name, party_link = "", ""
        if conv.party_id:
            try:
                p = parties.get_by_id(conv.party_id)
                if p:
                    party_name = p.display_name
                    party_link = f"/customers/{p.party_id}"
            except Exception:
                pass
        return templates.TemplateResponse(
            "conversation_detail.html",
            {
                "request": request,
                "conv": conv,
                "msgs": msgs,
                "party_name": party_name,
                "party_link": party_link,
                "conv_status_bdg": _conv_status_bdg,
            },
        )

    # ── M09 Assign conversation ───────────────────────────────────────────────

    @router.get("/inbox/{conv_id}/modal/assign", response_class=HTMLResponse)
    async def handle_modal_assign(request: Request, conv_id: str) -> Response:
        conv = conv_reader.get_by_id(conv_id)
        if conv is None:
            return HTMLResponse("not found", status_code=404)
        try:
            users = app_users.list_active()
        except Exception:
            users = []
        return templates.TemplateResponse(
            "fragments/modal_assign_conversation.html",
            {"request": request, "conv_id": conv_id, "conv": conv, "users": users},
        )

    @router.post("/inbox/{conv_id}/assign", response_class=HTMLResponse)
    async def handle_assign_conversation(
        request: Request, conv_id: str, assignee_user_id: str = Form(...)
    ) -> Response:
        assignee_user_id = assignee_user_id.strip()
        if not assignee_user_id:
            return HTMLResponse("assignee_user_id required", status_code=400)
        try:
            conv_writer.assign_conversation(conv_id, assignee_user_id)
        except Exception as exc:
            log.error("assign conv %s: %s", conv_id, exc)
            return HTMLResponse("failed to assign", status_code=500)
        return Response(status_code=200, headers={"HX-Trigger": '{"closeModal":true}'})

    # ── M10 Close conversation ────────────────────────────────────────────────

    @router.get("/inbox/{conv_id}/modal/close", response_class=HTMLResponse)
    async def handle_modal_close(request: Request, conv_id: str) -> Response:
        conv = conv_reader.get_by_id(conv_id)
        if conv is None:
            return HTMLResponse("not found", status_code=404)
        return templates.TemplateResponse(
            "fragments/modal_close_conversation.html",
            {"request": request, "conv_id": conv_id, "conv": conv},
        )

    @router.post("/inbox/{conv_id}/close", response_class=HTMLResponse)
    async def handle_close_conversation(request: Request, conv_id: str) -> Response:
        try:
            conv_writer.set_status(conv_id, "closed")
        except Exception as exc:
            log.error("close conv %s: %s", conv_id, exc)
            return HTMLResponse("failed to close", status_code=500)
        return Response(
            status_code=200,
            headers={"HX-Trigger": '{"closeModal":true}', "HX-Redirect": f"/inbox/{conv_id}"},
        )

    # ── M11 Link party ────────────────────────────────────────────────────────

    @router.get("/inbox/{conv_id}/modal/link-party", response_class=HTMLResponse)
    async def handle_modal_link_party(request: Request, conv_id: str) -> Response:
        conv = conv_reader.get_by_id(conv_id)
        if conv is None:
            return HTMLResponse("not found", status_code=404)
        return templates.TemplateResponse(
            "fragments/modal_link_party.html",
            {"request": request, "conv_id": conv_id, "conv": conv},
        )

    @router.get("/inbox/{conv_id}/parties/search", response_class=HTMLResponse)
    async def handle_inbox_party_search(request: Request, conv_id: str) -> Response:
        q = request.query_params.get("q", "").strip()
        if not q:
            return HTMLResponse('<div class="text-muted">Nhập tên hoặc SĐT để tìm...</div>')
        try:
            ids = parties.search_by_name(q)
            found = [p for pid in ids for p in [parties.get_by_id(pid)] if p]
        except Exception as exc:
            log.error("inbox party search: %s", exc)
            found = []
        return templates.TemplateResponse(
            "fragments/party_search_results.html",
            {"request": request, "parties": found, "conv_id": conv_id},
        )

    @router.post("/inbox/{conv_id}/link-party", response_class=HTMLResponse)
    async def handle_link_party(
        request: Request, conv_id: str, party_id: str = Form(...)
    ) -> Response:
        party_id = party_id.strip()
        if not party_id:
            return HTMLResponse("party_id required", status_code=400)
        try:
            conv_writer.link_party(conv_id, party_id)
        except Exception as exc:
            log.error("link party conv %s party %s: %s", conv_id, party_id, exc)
            return HTMLResponse("failed to link party", status_code=500)
        return Response(status_code=200, headers={"HX-Redirect": f"/inbox/{conv_id}"})

    # ── M08 Log activity (from S06) ───────────────────────────────────────────

    @router.get("/inbox/{conv_id}/modal/log-activity", response_class=HTMLResponse)
    async def handle_modal_log_activity(request: Request, conv_id: str) -> Response:
        conv = conv_reader.get_by_id(conv_id)
        if conv is None:
            return HTMLResponse("not found", status_code=404)
        party_id = conv.party_id or ""
        return templates.TemplateResponse(
            "fragments/modal_log_activity.html",
            {"request": request, "party_id": party_id, "conv_id": conv_id},
        )

    @router.post("/inbox/{conv_id}/log-activity", response_class=HTMLResponse)
    async def handle_log_activity_on_conv(
        request: Request,
        conv_id: str,
        party_id: str = Form(...),
        activity_type: str = Form(default="chat"),
        body: str = Form(...),
    ) -> Response:
        party_id = party_id.strip()
        body = body.strip()
        if not party_id or not body:
            return HTMLResponse("party_id and body required", status_code=400)
        current_user = getattr(request.state, "current_user", None)
        try:
            activity_log.log_activity({
                "party_id": party_id,
                "activity_type": activity_type or "chat",
                "body": body,
                "channel": "messenger",
                "direction": "out",
                "staff_user_id": current_user.user_id if current_user else None,
            })
        except Exception as exc:
            log.error("log activity party %s: %s", party_id, exc)
            return HTMLResponse("failed to log activity", status_code=500)
        return Response(
            status_code=200,
            headers={"HX-Trigger": '{"closeModal":true}', "HX-Redirect": f"/inbox/{conv_id}"},
        )

    return router

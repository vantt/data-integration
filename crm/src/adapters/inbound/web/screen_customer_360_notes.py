"""Web adapter — Customer 360 note CRUD routes.

Extracted from screen_customer_360.py to keep file size manageable.
Registered by make_customer_360_router() via register_note_routes().
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

log = logging.getLogger(__name__)


def register_note_routes(
    router: APIRouter,
    templates: Jinja2Templates,
    *,
    notes,
    app_users=None,
) -> None:
    """Register note add / edit / delete routes on *router*."""

    @router.post("/customers/{party_id}/notes", response_class=HTMLResponse)
    async def handle_add_note(
        request: Request,
        party_id: str,
        body: str = Form(...),
        note_type: str = Form(default="general"),
        pinned: str = Form(default="0"),
        visibility: str = Form(default="team"),
    ) -> Response:
        body = body.strip()
        if not body:
            return HTMLResponse("Nội dung không được bỏ trống", status_code=400)
        current_user = getattr(request.state, "current_user", None)
        try:
            notes.add_note(party_id, body,
                           author_user_id=current_user.user_id if current_user else None,
                           note_type=note_type, pinned=pinned == "1", visibility=visibility)
        except Exception as exc:
            log.error("c360: add note %s: %s", party_id, exc)
            return HTMLResponse("Lỗi thêm ghi chú", status_code=500)
        return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}?tab=notes"})

    @router.post("/customers/{party_id}/notes/{note_id}", response_class=HTMLResponse)
    async def handle_edit_note(
        request: Request,
        party_id: str,
        note_id: str,
        body: str = Form(...),
        note_type: str = Form(default="general"),
        pinned: str = Form(default="0"),
        visibility: str = Form(default="team"),
    ) -> Response:
        body = body.strip()
        if not body:
            return HTMLResponse("Nội dung không được bỏ trống", status_code=400)
        try:
            notes.update_note(note_id, body, note_type=note_type,
                              pinned=pinned == "1", visibility=visibility)
        except Exception as exc:
            log.error("c360: edit note %s: %s", note_id, exc)
            return HTMLResponse("Lỗi cập nhật ghi chú", status_code=500)
        return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}?tab=notes"})

    @router.post("/customers/{party_id}/notes/{note_id}/delete", response_class=HTMLResponse)
    async def handle_delete_note(
        request: Request, party_id: str, note_id: str
    ) -> Response:
        try:
            notes.delete_note(note_id)
        except Exception as exc:
            log.error("c360: delete note %s: %s", note_id, exc)
            return HTMLResponse("Lỗi xoá ghi chú", status_code=500)
        return HTMLResponse(content="", headers={"HX-Redirect": f"/customers/{party_id}?tab=notes"})

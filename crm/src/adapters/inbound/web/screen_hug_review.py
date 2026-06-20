"""Web adapter — Hug CS review queue.

CS agents use this screen to resolve crm_identity_link rows that the automatic
identity resolver could not safely assign (status='needs_review').  Typical
causes: the scanned phone already belongs to a different CRM party, or the
opt-in carries a gift/cross-signal that needs human judgement.

  GET  /hug/review               -> list all needs_review rows, newest first
  POST /hug/review/action        -> confirm (link) or reject a single row

Design notes:
- Self-contained HTML (no template engine), dark-card style matching the other
  Hug screens.  HTML rendering helpers live in screen_hug_review_html.py (no
  FastAPI dependency) so they can be unit-tested without the HTTP framework.
- Keyed by UNIQUE (token, scanner_phone).  scanner_phone may be NULL for
  Zalo-only opt-ins; the form transmits "" and the handler maps "" → None when
  looking up the row.
- Confirm → sets status='linked', applies the phone identity to the chosen
  party via screen_hug_review_data.confirm_link (INSERT OR IGNORE, ladder-safe).
- Reject → sets status='rejected' (requires migration 0023 to widen the CHECK).
- Acting on an already-resolved row is a no-op with a clear message (idempotent).
- Only the crm.db connection is needed; hug.db is not touched here.
"""
from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from adapters.inbound.web.screen_hug_review_html import (
    render_review_queue,
    render_action_result,
)
from adapters.inbound.web.screen_hug_review_data import (
    load_queue,
    fetch_link,
    set_status,
    confirm_link,
)

log = logging.getLogger(__name__)

_RESOLVED_STATUSES = {"linked", "rejected"}


def make_hug_review_router(conn: sqlite3.Connection) -> APIRouter:
    """Return the CS review-queue router bound to the crm.db connection."""
    router = APIRouter()

    @router.get("/hug/review", response_class=HTMLResponse)
    async def review_queue() -> HTMLResponse:
        rows = load_queue(conn)
        return HTMLResponse(render_review_queue(rows))

    @router.post("/hug/review/action", response_class=HTMLResponse)
    async def review_action(
        token: str = Form(default=""),
        scanner_phone: str = Form(default=""),
        action: str = Form(default=""),
        override_customer_id: str = Form(default=""),
    ) -> HTMLResponse:
        token = token.strip()
        # Empty string from the form means NULL phone (Zalo-only opt-in).
        phone: str | None = scanner_phone.strip() or None
        action = action.strip().lower()
        override = override_customer_id.strip() or None

        if not token:
            return HTMLResponse(render_action_result("Thiếu token.", ok=False))
        if action not in ("confirm", "reject"):
            return HTMLResponse(render_action_result(f"Hành động không hợp lệ: '{action}'.", ok=False))

        link = fetch_link(conn, token, phone)
        if link is None:
            return HTMLResponse(
                render_action_result(
                    f"Không tìm thấy dòng: token={token} phone={phone or 'NULL'}.",
                    ok=False,
                )
            )

        current_status = link["status"]
        if current_status in _RESOLVED_STATUSES:
            # Already resolved — idempotent no-op.
            label = "đã được xác nhận" if current_status == "linked" else "đã bị bác bỏ"
            return HTMLResponse(
                render_action_result(
                    f"Dòng này {label} trước đó — không thay đổi.", ok=True
                )
            )

        if action == "reject":
            set_status(conn, token, phone, "rejected")
            log.info("hug review: rejected token=%s phone=%s", token, phone)
            return RedirectResponse("/hug/review", status_code=303)

        # action == "confirm"
        resolved_id = override or link["resolved_customer_id"]
        if not resolved_id:
            return HTMLResponse(
                render_action_result(
                    "Không có resolved_customer_id — nhập party_id vào ô bên trên.", ok=False
                )
            )

        phone_to_attach = link["scanner_phone"]  # may be None (Zalo-only)
        confirm_link(conn, token, phone, resolved_id, phone_to_attach)
        log.info(
            "hug review: confirmed token=%s phone=%s → party=%s", token, phone, resolved_id
        )
        return RedirectResponse("/hug/review", status_code=303)

    return router

"""HTML form routes for the Hug claim station (no-JS fallback path).

  GET  /hug/claim          -> self-contained 2-field kiosk page
  POST /hug/claim          -> bind token (local instant) + best-effort D1 push
  GET  /hug/claim/health   -> token counts by status (ops)

The POST path is the no-JS fallback: it re-renders the full page after each
scan. The JS-driven happy path uses the AJAX endpoints in
``screen_hug_claim_ajax`` instead.
"""
from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from hug import config as hug_config
from hug import d1_push, repository
from hug.claim_fields import CLAIM_FIELDS
from hug.tokens import human_code, is_valid_token, normalize_input

from adapters.inbound.web.screen_hug_claim_render import _render_page, _render_result

log = logging.getLogger(__name__)


def make_claim_form_router(conn: sqlite3.Connection) -> APIRouter:
    """Return the HTML-form router bound to an open hug.db connection."""
    router = APIRouter()

    @router.get("/hug/claim", response_class=HTMLResponse)
    async def claim_form(order: str = "") -> HTMLResponse:
        return HTMLResponse(_render_page(order_code=order))

    @router.post("/hug/claim", response_class=HTMLResponse)
    async def claim_submit(request: Request) -> HTMLResponse:
        # Read all form fields generically so adding a new CLAIM_FIELDS entry
        # requires no change here — the loop below picks it up automatically.
        form = await request.form()
        fields: dict = {}
        for f in CLAIM_FIELDS:
            raw = form.get(f["key"], "")
            if f["type"] == "bool":
                fields[f["key"]] = raw in ("1", "true", "on", "yes")
            else:
                fields[f["key"]] = str(raw).strip()

        token = normalize_input(str(form.get("token", "")))
        order_code = fields.get("order_code", "")
        gift = fields.get("is_gift", False)

        if not order_code:
            return _render_result(False, "Thiếu mã đơn", order_code, token)
        if not is_valid_token(token):
            return _render_result(
                False, f"Tem không hợp lệ: {token or '(trống)'}", order_code, token
            )

        try:
            row = repository.bind_token(
                conn,
                token,
                order_code=order_code,
                is_gift=gift,
            )
        except KeyError:
            return _render_result(False, f"Tem chưa mint: {token}", order_code, token)
        except ValueError as exc:
            return _render_result(False, str(exc), order_code, token)
        except Exception as exc:  # noqa: BLE001
            log.error("hug claim: bind failed token=%s: %s", token, exc)
            return _render_result(False, f"Lỗi: {exc}", order_code, token)

        # Best-effort edge publish — never blocks/fails the claim.
        push = d1_push.push_bound_token(row)
        if push.get("ok"):
            repository.mark_pushed(conn, token)
            edge = "Đã đẩy lên edge (D1)."
        elif push.get("skipped"):
            edge = "Edge: pending deploy (chưa cấu hình Worker)."
        else:
            edge = f"Edge push lỗi (sẽ thử lại): {push.get('error', '?')}"

        msg = f"{human_code(token)} → {order_code}" + (" · QUÀ" if gift else "")
        return _render_result(True, msg, order_code, "", edge=edge)

    @router.get("/hug/claim/health", response_class=JSONResponse)
    async def claim_health() -> JSONResponse:
        return JSONResponse(
            {
                "counts": repository.counts_by_status(conn),
                "push_enabled": hug_config.push_enabled(),
                "hug_domain": hug_config.hug_domain(),
            }
        )

    return router

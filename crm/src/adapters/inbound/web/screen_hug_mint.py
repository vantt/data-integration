"""Web adapter — Hug mint station (warehouse admin).

Simple warehouse UI to pre-generate a batch of Hug tokens and render the
print-ready QR label sheet directly in the browser.

  GET  /hug/mint                    -> batch configuration form (count, batch id, op_type)
  POST /hug/mint                    -> mint batch + return QR labels page (ready to Ctrl-P)
  GET  /hug/batches                 -> recent batch list with token counts by status
  GET  /hug/batch/labels?batch_id=  -> reprint the QR label sheet for an existing batch

Design notes:
- Self-contained HTML (no AppShell / template engine), dark-card kiosk styling
  that mirrors screen_hug_claim.py.
- HTML rendering helpers live in screen_hug_mint_html.py (no FastAPI dependency)
  so they can be unit-tested independently of the HTTP framework.
- QR labels HTML is produced by hug_qr_print.render_labels_html() — the same
  function the CLI calls — so token generation and QR rendering are never
  duplicated (DRY).
- Minting delegates to hug.repository.mint_batch() — same function the CLI uses.
- The labels page embeds an "← Sinh batch khác" back-link and a print button so
  warehouse staff never need the CLI.
"""
from __future__ import annotations

import html
import logging
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse

from hug import repository

# Pure-HTML helpers (no FastAPI imports — independently testable).
from adapters.inbound.web.screen_hug_mint_html import (
    _MAX_COUNT,
    _MIN_COUNT,
    _render_batch_not_found,
    _render_batches,
    _render_form,
)

# Shared QR renderer — same function used by the hug_qr_print.py CLI.
from hug_qr_print import render_labels_html

log = logging.getLogger(__name__)


def _default_batch_id() -> str:
    return "LOT-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")


def make_hug_mint_router(conn: sqlite3.Connection) -> APIRouter:
    """Return the mint-station router bound to an open hug.db connection."""
    router = APIRouter()

    @router.get("/hug/mint", response_class=HTMLResponse)
    async def mint_form() -> HTMLResponse:
        return HTMLResponse(_render_form())

    @router.post("/hug/mint", response_class=HTMLResponse)
    async def mint_submit(
        count: str = Form(default=""),
        batch_id: str = Form(default=""),
        op_type: str = Form(default="package_insert"),
    ) -> HTMLResponse:
        # Validate count
        count_str = count.strip()
        try:
            n = int(count_str)
        except ValueError:
            return HTMLResponse(_render_form(error=f"Số lượng không hợp lệ: '{html.escape(count_str)}'"))
        if not (_MIN_COUNT <= n <= _MAX_COUNT):
            return HTMLResponse(
                _render_form(error=f"Số lượng phải từ {_MIN_COUNT} đến {_MAX_COUNT}.")
            )

        # Normalise batch id
        bid = batch_id.strip() or _default_batch_id()
        op = op_type.strip() or "package_insert"

        try:
            tokens = repository.mint_batch(conn, n, batch_id=bid, op_type=op)
        except Exception as exc:  # noqa: BLE001
            log.error("hug mint: failed batch=%s count=%d: %s", bid, n, exc)
            return HTMLResponse(_render_form(error=f"Lỗi khi sinh token: {html.escape(str(exc))}"))

        log.info("hug mint: batch=%s count=%d op_type=%s", bid, n, op)

        # Return the print-ready QR labels page (shared renderer, DRY).
        labels_html = render_labels_html(tokens, bid, op_type=op)
        return HTMLResponse(labels_html)

    @router.get("/hug/batches", response_class=HTMLResponse)
    async def batch_list() -> HTMLResponse:
        batches = repository.list_recent_batches(conn, limit=50)
        return HTMLResponse(_render_batches(list(batches)))

    @router.get("/hug/batch/labels", response_class=HTMLResponse)
    async def batch_labels_reprint(
        batch_id: str = Query(..., description="Batch ID to reprint labels for"),
    ) -> HTMLResponse:
        """Reprint the QR label sheet for an already-minted batch.

        Warehouse staff use this when they need to reprint after a paper jam or
        to produce extra copies of a label sheet. The batch_id is passed as a
        query parameter so batch IDs containing unusual characters (spaces, slashes,
        etc.) are handled safely without URL-path encoding complications.

        Returns the same print-ready HTML that POST /hug/mint produces originally.
        Returns a friendly error page (HTTP 200) when the batch does not exist.
        """
        rows = repository.list_batch(conn, batch_id)
        if not rows:
            return HTMLResponse(_render_batch_not_found(batch_id))

        tokens = [r["token"] for r in rows]
        # op_type is a mint-time batch property stored on every token row.
        # Guard for very old rows that pre-date the column (treat as default).
        op_type: str = "package_insert"
        try:
            first_op = rows[0]["op_type"]
            if first_op:
                op_type = first_op
        except (IndexError, KeyError):
            pass

        return HTMLResponse(render_labels_html(tokens, batch_id, op_type=op_type))

    return router

"""Web adapter — Hug claim station (kiosk).

Local/LAN claim station for binding pre-printed Hug tokens to a Sapo order.

  GET  /hug/claim?order=SO1234   -> self-contained 2-field kiosk page
  POST /hug/claim                -> bind token (local instant) + best-effort D1 push
  GET  /hug/claim/health         -> token counts by status (ops)
  GET  /hug/claim/check-token    -> AJAX token-state probe
  GET  /hug/claim/check-field    -> AJAX per-field validation
  POST /hug/claim/bind           -> AJAX bind (JS happy path)

Design notes:
- Self-contained HTML (no AppShell) — the station runs on a tablet/PC with a
  USB 2D scanner (acts as a keyboard). 2 inputs: order_code (pre-filled from the
  Sapo userscript via ?order=) and token (filled by the scanner). The token
  field auto-submits on Enter (scanners emit a trailing CR), giving a tap-free
  scan -> beep -> green flow.
- The D1 push is config-gated in hug.d1_push; with HUG_WORKER_URL unset the bind
  still succeeds and the push is skipped ("pending deploy").

This router owns its own hug.db connection (separate from crm.db), opened once
at wiring time — single writer, matching the CRM SQLite discipline.

Composition: this module wires the HTML-form routes (screen_hug_claim_form) and
the AJAX/JSON routes (screen_hug_claim_ajax) onto one router. Rendering lives in
screen_hug_claim_render + screen_hug_claim_template.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter

from adapters.inbound.web.screen_hug_claim_ajax import (  # noqa: F401  (re-exported for tests)
    _PROMOTED_COLS,
    make_claim_ajax_router,
)
from adapters.inbound.web.screen_hug_claim_form import make_claim_form_router
from adapters.inbound.web.screen_hug_claim_render import _render_page  # noqa: F401  (re-exported for tests)


def make_hug_claim_router(conn: sqlite3.Connection) -> APIRouter:
    """Return the claim-station router bound to an open hug.db connection."""
    router = APIRouter()
    router.include_router(make_claim_form_router(conn))
    router.include_router(make_claim_ajax_router(conn))
    return router

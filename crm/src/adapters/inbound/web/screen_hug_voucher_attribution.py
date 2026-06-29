"""Web adapter — Hug voucher attribution readout.

Admin screen showing issued vs. redeemed counts per campaign, sourced from
v_hug_voucher_attribution (crm.db).  Read-only; no mutations.

  GET /hug/vouchers  ->  table: Campaign | Code | Issued | Redeemed | Redeem rate %

Design notes:
- Self-contained HTML (no Jinja2 template), dark-card style matching other Hug screens.
- HTML rendering lives in screen_hug_voucher_attribution_html.py (no FastAPI dep) so it
  can be unit-tested without the HTTP framework.
- Data fetch lives in screen_hug_voucher_attribution_data.py (no FastAPI dep).
- Sorted by issued desc; empty-state shown when no vouchers have been issued yet.
- Only crm.db connection is needed — hug.db is not touched here.

IMPORTANT: make_hug_voucher_attribution_router MUST end with `return router`.
A missing return yields None, which causes app.include_router to silently disable
all routes registered after it in composition.py (observed in screen_hug_campaign.py).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from domain.ports.hug_ports import HugVoucherPort
from adapters.inbound.web.screen_hug_voucher_attribution_data import load_attribution
from adapters.inbound.web.screen_hug_voucher_attribution_html import render_attribution_page

log = logging.getLogger(__name__)


def make_hug_voucher_attribution_router(voucher_port: HugVoucherPort) -> APIRouter:
    """Return the voucher attribution router bound to a HugVoucherPort."""
    router = APIRouter()

    @router.get("/hug/vouchers", response_class=HTMLResponse)
    async def voucher_attribution() -> HTMLResponse:
        rows = load_attribution(voucher_port)
        log.debug("hug vouchers: %d attribution rows", len(rows))
        return HTMLResponse(render_attribution_page(rows))

    return router  # MUST be last — see module docstring

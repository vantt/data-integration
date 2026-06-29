"""Web adapter — S12 Order Detail screen.

FastAPI router mirroring screen_order_detail.go.
Serves full HTML page + HTMX tab fragments (financial, items, operations, context).
Reads order aggregates from DuckDB via OrderReader; returns 503 when unavailable.
"""
from __future__ import annotations

import logging
from typing import Optional, Protocol

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from domain.entities.order import OrderDetail

log = logging.getLogger(__name__)

_VALID_TABS = {"financial", "items", "operations", "context", "action"}


# ── Service protocol ──────────────────────────────────────────────────────────

class OrderReader(Protocol):
    def get_by_code(self, order_code: str) -> Optional[OrderDetail]: ...


# ── Router factory ────────────────────────────────────────────────────────────

def make_order_detail_router(
    templates: Jinja2Templates,
    orders: Optional[OrderReader] = None,
) -> APIRouter:
    """Return APIRouter wired with S12 Order Detail routes.

    Pass orders=None to serve 503 for all order routes (olap.duckdb not mounted).
    """
    router = APIRouter()

    def _unavailable() -> HTMLResponse:
        return HTMLResponse(
            "Order reader unavailable — olap.duckdb not mounted",
            status_code=503,
        )

    def _fetch(order_code: str) -> tuple[Optional[OrderDetail], Optional[HTMLResponse]]:
        """Fetch order; return (order, None) or (None, error_response)."""
        if orders is None:
            return None, _unavailable()
        try:
            o = orders.get_by_code(order_code)
        except Exception as exc:
            log.error("order detail: get %s: %s", order_code, exc)
            return None, HTMLResponse("Lỗi truy vấn đơn hàng", status_code=500)
        if o is None:
            return None, HTMLResponse("Không tìm thấy đơn hàng", status_code=404)
        return o, None

    # ── Full page ─────────────────────────────────────────────────────────────

    @router.get("/orders/{order_code}", response_class=HTMLResponse)
    async def handle_order_detail(request: Request, order_code: str) -> Response:
        o, err = _fetch(order_code)
        if err is not None:
            return err
        active_tab = request.query_params.get("tab", "financial")
        if active_tab not in _VALID_TABS:
            active_tab = "financial"
        return templates.TemplateResponse(
            "order_detail.html",
            {"request": request, "order": o, "active_tab": active_tab},
        )

    # ── HTMX tab fragments ────────────────────────────────────────────────────

    @router.get("/orders/{order_code}/tabs/{tab}", response_class=HTMLResponse)
    async def handle_order_tab(request: Request, order_code: str, tab: str) -> Response:
        o, err = _fetch(order_code)
        if err is not None:
            return err
        ctx = {"request": request, "order": o}
        tab_templates = {
            "financial":  "fragments/order_financial_tab.html",
            "items":      "fragments/order_items_tab.html",
            "operations": "fragments/order_operations_tab.html",
            "context":    "fragments/order_context_tab.html",
            "action":     "fragments/order_action_tab.html",
        }
        tmpl = tab_templates.get(tab)
        if tmpl is None:
            return HTMLResponse("tab not found", status_code=404)
        return templates.TemplateResponse(tmpl, ctx)

    return router

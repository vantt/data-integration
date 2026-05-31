"""HTTP route handlers for the web adapter.

All handlers are registered by web.register_web(); they receive services
via closure — no module-level state except the templates reference.

HTMX detection: presence of 'HX-Request' header → partial response.
Full-page requests always get the shell (base.html extends).

Context contract (FROZEN — frontend depends on these exact names):
  Every response context includes via base_context():
    request       – FastAPI Request (Jinja2 requirement)
    data_health   – DataQualitySummary|None  (system-level DQ strip)
    caps          – dict{"has_carrier_link": bool, "has_per_line_cogs": bool}

  Detail routes additionally include:
    quality_flags – list[DataQualityFlag]  (per-entity flags for sidebar/strip)
"""
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.domain.shared import CustomerTab, DataQualityFlag, OrderTab

logger = logging.getLogger(__name__)


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def register_routes(
    app,  # FastAPI instance
    templates: Jinja2Templates,
    order_service,
    customer_service,
    search_service,
    capability=None,
    data_quality=None,
) -> None:
    """Attach all URL routes to the FastAPI app."""

    # ------------------------------------------------------------------
    # base_context helper
    # Returns the dict every template receives; merges in per-entity vars.
    # ------------------------------------------------------------------
    def _base_context(request: Request) -> dict:
        """Build the shared template context injected into every response.

        Keys (FROZEN contract):
          data_health : DataQualitySummary|None
          caps        : {"has_carrier_link": bool, "has_per_line_cogs": bool}
        """
        data_health = None
        if data_quality is not None:
            try:
                data_health = data_quality.coverage_metrics()
            except Exception:  # noqa: BLE001 — DQ strip must never crash a page
                logger.warning("base_context: coverage_metrics() failed", exc_info=True)

        has_carrier_link = False
        has_per_line_cogs = False
        if capability is not None:
            try:
                has_carrier_link = (
                    capability.has_column("fact_fulfillments", "carrier_url")
                    or capability.view_exists("dim_carriers")
                )
                has_per_line_cogs = capability.has_column("fact_sales", "cogs_amount")
            except Exception:  # noqa: BLE001
                logger.warning("base_context: capability check failed", exc_info=True)

        return {
            "request": request,
            "data_health": data_health,
            "caps": {
                "has_carrier_link": has_carrier_link,
                "has_per_line_cogs": has_per_line_cogs,
            },
        }

    # ------------------------------------------------------------------
    # Home
    # ------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request, nf: str = "", amb: str = ""):
        ctx = _base_context(request)
        if nf:
            # Came from /go/{code} (or Auto search) with no clean redirect:
            # ambiguous=both order_id & customer_id matched; else just unknown.
            ctx["resolver_miss"] = {"code": nf, "ambiguous": bool(amb)}
        return templates.TemplateResponse("home.html", ctx)

    # ------------------------------------------------------------------
    # Search  GET /search?mode=order|customer&q=<query>
    # ------------------------------------------------------------------
    @app.get("/search", response_class=HTMLResponse)
    async def search(request: Request, mode: str = "order", q: str = ""):
        resolution = search_service.resolve(mode, q)

        if resolution.redirect_to:
            if _is_htmx(request):
                # HTMX: instruct the browser to navigate
                return HTMLResponse(
                    content="",
                    headers={"HX-Redirect": resolution.redirect_to},
                )
            return RedirectResponse(url=resolution.redirect_to, status_code=303)

        if resolution.customer_hits:
            ctx = _base_context(request)
            ctx.update({"hits": resolution.customer_hits, "q": q})
            return templates.TemplateResponse(
                "partials/_search_results.html",
                ctx,
            )

        # not_found (or auto-mode ambiguous: token matched both order & customer)
        ctx = _base_context(request)
        ctx.update({"q": q, "mode": mode, "ambiguous": resolution.ambiguous})
        return templates.TemplateResponse(
            "partials/_not_found_hint.html",
            ctx,
        )

    # ------------------------------------------------------------------
    # Order detail  GET /orders/{order_code}
    # ------------------------------------------------------------------
    @app.get("/orders/{order_code}", response_class=HTMLResponse)
    async def order_detail(request: Request, order_code: str):
        order = order_service.get_detail(order_code)
        if order is None:
            ctx = _base_context(request)
            ctx.update({"entity": "Order", "ref": order_code})
            return templates.TemplateResponse(
                "partials/_not_found_page.html",
                ctx,
                status_code=404,
            )

        quality_flags: list[DataQualityFlag] = order.quality_flags(cap=capability)
        ctx = _base_context(request)
        ctx.update({
            "order": order,
            "active_tab": OrderTab.FINANCIAL,
            "tabs": list(OrderTab),
            "order_code": order_code,
            "quality_flags": quality_flags,
        })
        return templates.TemplateResponse("order_detail.html", ctx)

    # ------------------------------------------------------------------
    # Order tab partial  GET /orders/{order_code}/tab/{tab}
    # ------------------------------------------------------------------
    @app.get("/orders/{order_code}/tab/{tab}", response_class=HTMLResponse)
    async def order_tab(request: Request, order_code: str, tab: str):
        try:
            order_tab_val = OrderTab(tab)
        except ValueError:
            return HTMLResponse(
                content=f"<p>Unknown tab: {tab}</p>",
                status_code=404,
            )

        order = order_service.get_detail(order_code)
        if order is None:
            ctx = _base_context(request)
            ctx.update({"entity": "Order", "ref": order_code})
            return templates.TemplateResponse(
                "partials/_not_found_page.html",
                ctx,
                status_code=404,
            )

        _tab_template = {
            OrderTab.FINANCIAL: "partials/order/_financial.html",
            OrderTab.ITEMS: "partials/order/_line_items.html",
            OrderTab.OPERATIONS: "partials/order/_operations.html",
            OrderTab.CONTEXT: "partials/order/_context.html",
            OrderTab.ACTIONS: "partials/order/_actions.html",
        }

        quality_flags: list[DataQualityFlag] = order.quality_flags(cap=capability)
        ctx = _base_context(request)
        ctx.update({
            "order": order,
            "tab": order_tab_val,
            "quality_flags": quality_flags,
        })
        return templates.TemplateResponse(_tab_template[order_tab_val], ctx)

    # ------------------------------------------------------------------
    # Customer detail  GET /customers/{customer_id}
    # ------------------------------------------------------------------
    _CUSTOMER_TAB_TEMPLATE = {
        CustomerTab.OVERVIEW: "partials/customer/_overview.html",
        CustomerTab.STATUS_TIMELINE: "partials/customer/_status_timeline.html",
        CustomerTab.ORDER_HISTORY: "partials/customer/_order_history.html",
        CustomerTab.ACTIONS: "partials/customer/_actions.html",
    }

    @app.get("/customers/{customer_id}", response_class=HTMLResponse)
    async def customer_detail(request: Request, customer_id: str, tab: str = ""):
        customer = customer_service.get_detail(customer_id)
        if customer is None:
            ctx = _base_context(request)
            ctx.update({"entity": "Customer", "ref": customer_id})
            return templates.TemplateResponse(
                "partials/_not_found_page.html",
                ctx,
                status_code=404,
            )

        # Resolve ?tab= query param; fall back to OVERVIEW for unknown/missing values.
        try:
            active_tab = CustomerTab(tab) if tab else CustomerTab.OVERVIEW
        except ValueError:
            active_tab = CustomerTab.OVERVIEW

        dq = None
        if data_quality is not None:
            try:
                dq = data_quality.coverage_metrics()
            except Exception:  # noqa: BLE001
                logger.warning("customer_detail: coverage_metrics() failed", exc_info=True)

        quality_flags: list[DataQualityFlag] = customer.quality_flags(cap=capability, dq=dq)
        ctx = _base_context(request)
        ctx.update({
            "customer": customer,
            "active_tab": active_tab,
            "initial_tab_template": _CUSTOMER_TAB_TEMPLATE[active_tab],
            "tabs": list(CustomerTab),
            "customer_id": customer_id,
            "quality_flags": quality_flags,
        })
        return templates.TemplateResponse("customer_detail.html", ctx)

    # ------------------------------------------------------------------
    # Customer tab partial  GET /customers/{customer_id}/tab/{tab}
    # ------------------------------------------------------------------
    @app.get("/customers/{customer_id}/tab/{tab}", response_class=HTMLResponse)
    async def customer_tab(request: Request, customer_id: str, tab: str):
        try:
            customer_tab_val = CustomerTab(tab)
        except ValueError:
            return HTMLResponse(
                content=f"<p>Unknown tab: {tab}</p>",
                status_code=404,
            )

        customer = customer_service.get_detail(customer_id)
        if customer is None:
            ctx = _base_context(request)
            ctx.update({"entity": "Customer", "ref": customer_id})
            return templates.TemplateResponse(
                "partials/_not_found_page.html",
                ctx,
                status_code=404,
            )

        dq = None
        if data_quality is not None:
            try:
                dq = data_quality.coverage_metrics()
            except Exception:  # noqa: BLE001
                logger.warning("customer_tab: coverage_metrics() failed", exc_info=True)

        _tab_template = {
            CustomerTab.OVERVIEW: "partials/customer/_overview.html",
            CustomerTab.STATUS_TIMELINE: "partials/customer/_status_timeline.html",
            CustomerTab.ORDER_HISTORY: "partials/customer/_order_history.html",
            CustomerTab.ACTIONS: "partials/customer/_actions.html",
        }

        quality_flags: list[DataQualityFlag] = customer.quality_flags(cap=capability, dq=dq)
        ctx = _base_context(request)
        ctx.update({
            "customer": customer,
            "tab": customer_tab_val,
            "customer_id": customer_id,
            "quality_flags": quality_flags,
        })
        return templates.TemplateResponse(_tab_template[customer_tab_val], ctx)

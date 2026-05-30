"""HTTP route handlers for the web adapter.

All handlers are registered by web.register_web(); they receive services
via closure — no module-level state except the templates reference.

HTMX detection: presence of 'HX-Request' header → partial response.
Full-page requests always get the shell (base.html extends).
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.domain.shared import CustomerTab, OrderTab


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def register_routes(
    app,  # FastAPI instance
    templates: Jinja2Templates,
    order_service,
    customer_service,
    search_service,
) -> None:
    """Attach all URL routes to the FastAPI app."""

    # ------------------------------------------------------------------
    # Home
    # ------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse(
            "home.html",
            {"request": request},
        )

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
            return templates.TemplateResponse(
                "partials/_search_results.html",
                {"request": request, "hits": resolution.customer_hits, "q": q},
            )

        # not_found
        return templates.TemplateResponse(
            "partials/_not_found_hint.html",
            {"request": request, "q": q, "mode": mode},
        )

    # ------------------------------------------------------------------
    # Order detail  GET /orders/{order_code}
    # ------------------------------------------------------------------
    @app.get("/orders/{order_code}", response_class=HTMLResponse)
    async def order_detail(request: Request, order_code: str):
        order = order_service.get_detail(order_code)
        if order is None:
            return templates.TemplateResponse(
                "partials/_not_found_page.html",
                {"request": request, "entity": "Order", "ref": order_code},
                status_code=404,
            )

        # Financial tab renders inline on first paint (no lazy load)
        return templates.TemplateResponse(
            "order_detail.html",
            {
                "request": request,
                "order": order,
                "active_tab": OrderTab.FINANCIAL,
                "tabs": list(OrderTab),
                "order_code": order_code,
            },
        )

    # ------------------------------------------------------------------
    # Order tab partial  GET /orders/{order_code}/tab/{tab}
    # ------------------------------------------------------------------
    @app.get("/orders/{order_code}/tab/{tab}", response_class=HTMLResponse)
    async def order_tab(request: Request, order_code: str, tab: str):
        # Validate tab value against enum
        try:
            order_tab = OrderTab(tab)
        except ValueError:
            return HTMLResponse(
                content=f"<p>Unknown tab: {tab}</p>",
                status_code=404,
            )

        order = order_service.get_detail(order_code)
        if order is None:
            return templates.TemplateResponse(
                "partials/_not_found_page.html",
                {"request": request, "entity": "Order", "ref": order_code},
                status_code=404,
            )

        # Map tab enum → partial template (merged panels reuse the original
        # section partials via {% include %}, so markup/HTMX stays DRY).
        _tab_template = {
            OrderTab.FINANCIAL: "partials/order/_financial.html",
            OrderTab.ITEMS: "partials/order/_line_items.html",
            OrderTab.OPERATIONS: "partials/order/_operations.html",
            OrderTab.CONTEXT: "partials/order/_context.html",
        }

        return templates.TemplateResponse(
            _tab_template[order_tab],
            {"request": request, "order": order, "tab": order_tab},
        )

    # ------------------------------------------------------------------
    # Customer detail  GET /customers/{customer_id}
    # ------------------------------------------------------------------
    @app.get("/customers/{customer_id}", response_class=HTMLResponse)
    async def customer_detail(request: Request, customer_id: str):
        customer = customer_service.get_detail(customer_id)
        if customer is None:
            return templates.TemplateResponse(
                "partials/_not_found_page.html",
                {"request": request, "entity": "Customer", "ref": customer_id},
                status_code=404,
            )

        return templates.TemplateResponse(
            "customer_detail.html",
            {
                "request": request,
                "customer": customer,
                "active_tab": CustomerTab.OVERVIEW,
                "tabs": list(CustomerTab),
                "customer_id": customer_id,
            },
        )

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
            return templates.TemplateResponse(
                "partials/_not_found_page.html",
                {"request": request, "entity": "Customer", "ref": customer_id},
                status_code=404,
            )

        _tab_template = {
            CustomerTab.OVERVIEW: "partials/customer/_overview.html",
            CustomerTab.STATUS_TIMELINE: "partials/customer/_status_timeline.html",
            CustomerTab.ORDER_HISTORY: "partials/customer/_order_history.html",
        }

        return templates.TemplateResponse(
            _tab_template[customer_tab_val],
            {
                "request": request,
                "customer": customer,
                "tab": customer_tab_val,
                "customer_id": customer_id,
            },
        )

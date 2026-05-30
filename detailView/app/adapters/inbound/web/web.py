"""Web adapter entry point.

The lead's main.py calls:

    from app.adapters.inbound.web.web import register_web
    register_web(app, order_service=..., customer_service=..., search_service=...,
                 capability=..., data_quality=...)

This module owns:
- Jinja2Templates construction (pointing to web/templates/)
- StaticFiles mount at /static (from web/static/)
- Custom filter registration on the Jinja env
- Global exception handler (renders partials/_503.html on unhandled errors)
- Route registration (delegated to routes.py)

It does NOT instantiate services or repositories — those arrive as arguments
so the dependency graph stays under the composition root's control.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .formatting import register_filters
from .routes import register_routes

logger = logging.getLogger(__name__)

# Absolute paths relative to this file's location
_HERE = Path(__file__).parent
_TEMPLATES_DIR = _HERE / "templates"
_STATIC_DIR = _HERE / "static"


def register_web(
    app: FastAPI,
    *,
    order_service,
    customer_service,
    search_service,
    capability=None,
    data_quality=None,
) -> None:
    """Register the web adapter onto a FastAPI app instance.

    Args:
        app: The FastAPI application (created by the composition root).
        order_service: Instance of OrderService (duck-typed; no hard import).
        customer_service: Instance of CustomerService.
        search_service: Instance of SearchService.
        capability: Optional DuckDbCapabilityAdapter (CapabilityPort).
        data_quality: Optional DuckDbDataQualityAdapter (DataQualityPort).
    """
    # --- Static files (CSS, vendor JS) ---
    # Mounted before routes so /static/* is handled by StaticFiles middleware.
    app.mount(
        "/static",
        StaticFiles(directory=str(_STATIC_DIR)),
        name="static",
    )

    # --- Jinja2 templates ---
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    # Register custom filters (vnd, pct, dt, dateonly) on the Jinja env
    register_filters(templates.env)

    # --- Global exception handler ---
    # Catches unhandled DuckDB errors (lock, missing view, binder error) and any
    # other unexpected exception. Renders _503.html instead of leaking a stack trace.
    @app.exception_handler(Exception)
    async def _global_error_handler(request: Request, exc: Exception) -> HTMLResponse:
        logger.exception("Unhandled exception for %s %s", request.method, request.url)
        return templates.TemplateResponse(
            "partials/_503.html",
            {"request": request},
            status_code=503,
        )

    # --- Routes ---
    register_routes(
        app,
        templates=templates,
        order_service=order_service,
        customer_service=customer_service,
        search_service=search_service,
        capability=capability,
        data_quality=data_quality,
    )

"""Web adapter entry point.

The lead's main.py calls:

    from app.adapters.inbound.web.web import register_web
    register_web(app, order_service=..., customer_service=..., search_service=...)

This module owns:
- Jinja2Templates construction (pointing to web/templates/)
- StaticFiles mount at /static (from web/static/)
- Custom filter registration on the Jinja env
- Route registration (delegated to routes.py)

It does NOT instantiate services or repositories — those arrive as arguments
so the dependency graph stays under the composition root's control.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .formatting import register_filters
from .routes import register_routes

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
) -> None:
    """Register the web adapter onto a FastAPI app instance.

    Args:
        app: The FastAPI application (created by the composition root).
        order_service: Instance of OrderService (duck-typed; no hard import).
        customer_service: Instance of CustomerService.
        search_service: Instance of SearchService.
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

    # --- Routes ---
    register_routes(
        app,
        templates=templates,
        order_service=order_service,
        customer_service=customer_service,
        search_service=search_service,
    )

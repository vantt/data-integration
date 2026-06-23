"""Mount all CRM web routers onto a FastAPI app.

Entry point for the HTMX/server-rendered web layer.
Each screen_*.py owns its own APIRouter; this module wires them together.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .screen_modals import init_modals, router as modals_router
from .templating import make_templates


def mount_web(app: FastAPI, deps: object, templates_dir: str, static_dir: str) -> None:
    """Attach all web sub-routers and static mounts to *app*.

    Call once during application startup, after all services are wired.
    """
    templates = make_templates(templates_dir)

    # Initialise per-router deps + templates reference.
    init_modals(deps, templates)  # type: ignore[arg-type]

    # Register routers.
    app.include_router(modals_router)

    # Static assets (CSS, JS, icons).
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

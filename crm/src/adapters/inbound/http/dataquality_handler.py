"""HTTP handler for the data-health footer strip (/_dq_strip).

Lazy-loaded by layout.html via HTMX after page renders. Returns empty HTML
when the mart is unavailable — the strip simply does not appear.
"""
from __future__ import annotations

from typing import Optional, Protocol

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


class _DQProvider(Protocol):
    def get(self): ...


def make_dataquality_router(
    dq: Optional[_DQProvider],
    templates: Jinja2Templates,
) -> APIRouter:
    router = APIRouter()

    @router.get("/_dq_strip", response_class=HTMLResponse)
    async def dq_strip(request: Request):
        summary = None
        if dq is not None:
            try:
                summary = dq.get()
            except Exception:  # noqa: BLE001
                pass
        if summary is None:
            return HTMLResponse(content="")
        return templates.TemplateResponse(
            "fragments/_dq_strip.html",
            {"request": request, "dq": summary},
        )

    return router

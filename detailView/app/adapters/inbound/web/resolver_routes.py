"""Smart resolver route — GET /go/{code}.

One endpoint that recognises which entity a code belongs to and 302-redirects
to its detail page:
  - order_code / order_id / fulfillment_code / fulfillment_id / tracking_code
        -> /orders/{order_code}   (shipments have no standalone page; the parent
                                    order is the canonical destination)
  - customer_id / customer_code (CUZN…) / phone / email
        -> /customers/{customer_id}

Detection + verification is delegated to SearchService.resolve("auto", …) so the
matching logic lives in one place (shared with the header "Auto" search mode).

Miss handling (per product decision): ambiguous or unknown codes redirect to the
home page with a ?nf= hint rather than rendering a 404 — the home search is the
natural place to retry.

Kept in its own module because routes.py already exceeds the 200-LOC budget.
"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _redirect(request: Request, url: str) -> HTMLResponse | RedirectResponse:
    """303 for a normal browser GET; HX-Redirect header for HTMX-driven calls."""
    if _is_htmx(request):
        return HTMLResponse(content="", headers={"HX-Redirect": url})
    return RedirectResponse(url=url, status_code=303)


def register_resolver_routes(
    app,  # FastAPI instance
    templates: Jinja2Templates,  # reserved for future inline rendering; keeps signature uniform
    search_service,
) -> None:
    """Attach GET /go/{code} to the FastAPI app."""

    @app.get("/go/{code}", response_class=HTMLResponse)
    async def go(request: Request, code: str):
        resolution = search_service.resolve("auto", code)

        if resolution.redirect_to:
            return _redirect(request, resolution.redirect_to)

        # ambiguous / multi-customer / not-found -> home with a hint.
        nf = quote(code, safe="")
        target = f"/?nf={nf}&amb=1" if resolution.ambiguous else f"/?nf={nf}"
        return _redirect(request, target)

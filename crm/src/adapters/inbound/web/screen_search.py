"""Web adapter — Global Header Search endpoint.

GET /search?mode=auto|order|customer&q=...

Returns one of:
  - HX-Redirect header to the matched entity page (single hit)
  - fragments/_search_hits.html  (multiple customer candidates — disambiguation dropdown)
  - fragments/_search_not_found.html (zero hits or ambiguous auto-match)

Customer resolution order:
  1. UUID → party_id direct
  2. Unified FTS (crm_party_search) for everything else

Order resolution delegates to DuckDBOrderRepository.resolve_order_code().
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Protocol

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from domain.entities.party import Party

log = logging.getLogger(__name__)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _fts_query(q: str) -> str:
    """Wrap user input as FTS5 quoted string + prefix wildcard.

    Quoted strings in FTS5 treat all chars as literals except '"'.
    Stripping '"' from user input prevents syntax errors.
    Trailing '*' enables prefix matching.
    """
    clean = q.replace('"', ' ').strip()
    return f'"{clean}"*'


# ── Service protocols ─────────────────────────────────────────────────────────

class PartySearcher(Protocol):
    def get_by_id(self, party_id: str) -> Optional[Party]: ...
    def find_by_identity(self, identity_type: str, identity_value: str) -> Optional[Party]: ...
    def search_unified(self, q: str) -> list[str]: ...  # returns party_ids
    def list_by_phone(self, q: str) -> list[Party]: ...
    def list_by_email(self, q: str) -> list[Party]: ...


class OrderResolver(Protocol):
    def resolve_order_code(self, q: str) -> Optional[str]: ...
    def find_customer_id_by_code(self, customer_code: str) -> Optional[str]: ...


# ── Router factory ────────────────────────────────────────────────────────────

def make_search_router(
    templates: Jinja2Templates,
    parties: PartySearcher,
    orders: Optional[OrderResolver] = None,
) -> APIRouter:
    """Return APIRouter with the /search route."""
    router = APIRouter()

    def _is_htmx(request: Request) -> bool:
        return request.headers.get("HX-Request") == "true"

    def _redirect(request: Request, url: str) -> Response:
        if _is_htmx(request):
            return HTMLResponse(content="", headers={"HX-Redirect": url})
        return RedirectResponse(url=url, status_code=303)

    def _resolve_order(q: str) -> str | None:
        if orders is None:
            return None
        try:
            return orders.resolve_order_code(q)
        except Exception:
            log.warning("search: resolve_order %r failed", q, exc_info=True)
            return None

    def _resolve_customer(q: str) -> tuple[str | None, list[Party]]:
        """Return (redirect_url | None, disambiguation_hits).

        Exactly one of the two return values is non-empty, or both are empty on miss.
        """
        # 1. UUID → party_id direct
        if _UUID_RE.match(q):
            p = parties.get_by_id(q)
            return (f"/customers/{q}" if p else None), []

        # 2. Unified FTS for everything else
        try:
            ids = parties.search_unified(_fts_query(q))
        except Exception:
            log.warning("search: search_unified %r failed", q, exc_info=True)
            ids = []
        valid: list[Party] = []
        for pid in ids[:15]:
            try:
                p = parties.get_by_id(pid)
                if p and not p.is_merged:
                    valid.append(p)
            except Exception:
                pass
        if len(valid) == 1:
            return f"/customers/{valid[0].party_id}", []
        return None, valid[:10]

    # ── Route ─────────────────────────────────────────────────────────────────

    @router.get("/search", response_class=HTMLResponse)
    async def handle_search(request: Request) -> Response:
        mode = request.query_params.get("mode", "auto").lower()
        q = request.query_params.get("q", "").strip()

        if not q:
            return HTMLResponse(content="")

        def _not_found(ambiguous: bool = False) -> Response:
            return templates.TemplateResponse(
                "fragments/_search_not_found.html",
                {"request": request, "q": q, "mode": mode, "ambiguous": ambiguous},
            )

        def _hits(hits: list[Party]) -> Response:
            return templates.TemplateResponse(
                "fragments/_search_hits.html",
                {"request": request, "hits": hits, "q": q},
            )

        # ── Order mode ────────────────────────────────────────────────────────
        if mode == "order":
            code = _resolve_order(q)
            return _redirect(request, f"/orders/{code}") if code else _not_found()

        # ── Customer mode ─────────────────────────────────────────────────────
        if mode == "customer":
            url, customer_hits = _resolve_customer(q)
            if url:
                return _redirect(request, url)
            return _hits(customer_hits) if customer_hits else _not_found()

        # ── Auto mode — detect entity type ────────────────────────────────────
        order_code = _resolve_order(q)
        url, customer_hits = _resolve_customer(q)
        order_hit = bool(order_code)
        customer_hit = bool(url or customer_hits)

        if order_hit and customer_hit:
            return _not_found(ambiguous=True)
        if order_code:
            return _redirect(request, f"/orders/{order_code}")
        if url:
            return _redirect(request, url)
        if customer_hits:
            return _hits(customer_hits)
        return _not_found()

    return router

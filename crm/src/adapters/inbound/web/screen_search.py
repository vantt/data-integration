"""Web adapter — Global Header Search endpoint.

GET /search?mode=auto|order|customer&q=...

Returns one of:
  - HX-Redirect header to the matched entity page (single hit)
  - fragments/_search_hits.html  (multiple customer candidates — disambiguation dropdown)
  - fragments/_search_not_found.html (zero hits or ambiguous auto-match)

Customer resolution order:
  1. UUID → party_id direct
  2. Pure digits → sapo_customer identity; if miss → phone fallback
  3. Contains '@' → email exact match
  4. 9+ stripped digits → phone prefix search
  5. Alphanumeric (non-UUID, non-digit) → customer_code via DuckDB
  6. Fallback → name FTS

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


# ── Service protocols ─────────────────────────────────────────────────────────

class PartySearcher(Protocol):
    def get_by_id(self, party_id: str) -> Optional[Party]: ...
    def find_by_identity(self, identity_type: str, identity_value: str) -> Optional[Party]: ...
    def search_by_name(self, q: str) -> list[str]: ...
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
        phone_digits = re.sub(r"[^0-9]", "", q)

        # 1. UUID → party_id direct
        if _UUID_RE.match(q):
            p = parties.get_by_id(q)
            return (f"/customers/{q}" if p else None), []

        # 2. Pure digits → sapo_customer identity
        if q.isdigit():
            p = parties.find_by_identity("sapo_customer", q)
            if p:
                return f"/customers/{p.party_id}", []
            # fall through to phone check (a 10-digit number may be a phone)

        # 3. Email
        if "@" in q:
            try:
                hits = [p for p in parties.list_by_email(q) if not p.is_merged]
            except Exception:
                hits = []
            if len(hits) == 1:
                return f"/customers/{hits[0].party_id}", []
            if hits:
                return None, hits[:10]
            return None, []

        # 4. Phone (9+ stripped digits covers Vietnamese 10-digit phones with separators)
        if len(phone_digits) >= 9:
            try:
                hits = [p for p in parties.list_by_phone(q) if not p.is_merged]
            except Exception:
                hits = []
            if len(hits) == 1:
                return f"/customers/{hits[0].party_id}", []
            if hits:
                return None, hits[:10]

        # 5. Customer code → DuckDB lookup (alphanumeric, non-UUID, non-digit, non-email)
        if orders is not None and not q.isdigit():
            try:
                customer_id = orders.find_customer_id_by_code(q)
                if customer_id:
                    p = parties.find_by_identity("sapo_customer", customer_id)
                    return (f"/customers/{p.party_id}" if p else None), []
            except Exception:
                log.warning("search: customer_code resolve %r failed", q, exc_info=True)

        # 6. Name FTS fallback
        try:
            ids = parties.search_by_name(q)
        except Exception:
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

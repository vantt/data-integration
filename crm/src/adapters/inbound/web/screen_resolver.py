"""Web adapter — Smart resolver route.

GET /go/{code}  → detects entity type and 302-redirects to detail page:
  - order_code / order_id / fulfillment / tracking  →  /orders/{order_code}
  - customer UUID / sapo_id / phone / email / code  →  /customers/{party_id}

On miss or ambiguity: redirect to /?nf= (home search with hint).
Delegates to the same detection logic as screen_search (auto mode).
"""
from __future__ import annotations

import re
from typing import Optional, Protocol
from urllib.parse import quote

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from crm.src.domain.entities.party import Party

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class _PartySearcher(Protocol):
    def get_by_id(self, party_id: str) -> Optional[Party]: ...
    def find_by_identity(self, identity_type: str, identity_value: str) -> Optional[Party]: ...
    def search_by_name(self, q: str) -> list[str]: ...
    def list_by_phone(self, q: str) -> list[Party]: ...
    def list_by_email(self, q: str) -> list[Party]: ...


class _OrderResolver(Protocol):
    def resolve_order_code(self, q: str) -> Optional[str]: ...
    def find_customer_id_by_code(self, customer_code: str) -> Optional[str]: ...


def make_resolver_router(
    parties: _PartySearcher,
    orders: Optional[_OrderResolver] = None,
) -> APIRouter:
    router = APIRouter()

    def _redir(request: Request, url: str) -> Response:
        if request.headers.get("HX-Request") == "true":
            return HTMLResponse(content="", headers={"HX-Redirect": url})
        return RedirectResponse(url=url, status_code=303)

    def _resolve_order(q: str) -> Optional[str]:
        if orders is None:
            return None
        try:
            return orders.resolve_order_code(q)
        except Exception:
            return None

    def _resolve_customer(q: str) -> Optional[str]:
        phone_digits = re.sub(r"[^0-9]", "", q)
        if _UUID_RE.match(q):
            p = parties.get_by_id(q)
            return f"/customers/{q}" if p else None
        if q.isdigit():
            p = parties.find_by_identity("sapo_customer", q)
            if p:
                return f"/customers/{p.party_id}"
        if "@" in q:
            try:
                hits = [p for p in parties.list_by_email(q) if not p.is_merged]
            except Exception:
                hits = []
            if len(hits) == 1:
                return f"/customers/{hits[0].party_id}"
            return None
        if len(phone_digits) >= 9:
            try:
                hits = [p for p in parties.list_by_phone(q) if not p.is_merged]
            except Exception:
                hits = []
            if len(hits) == 1:
                return f"/customers/{hits[0].party_id}"
            return None
        if orders is not None and not q.isdigit():
            try:
                cid = orders.find_customer_id_by_code(q)
                if cid:
                    p = parties.find_by_identity("sapo_customer", cid)
                    return f"/customers/{p.party_id}" if p else None
            except Exception:
                pass
        return None

    @router.get("/go/{code}", response_class=HTMLResponse)
    async def go_resolver(request: Request, code: str) -> Response:
        order_code = _resolve_order(code)
        customer_url = _resolve_customer(code)
        order_hit = bool(order_code)
        customer_hit = bool(customer_url)
        nf = quote(code, safe="")
        if order_hit and customer_hit:
            return _redir(request, f"/?nf={nf}&amb=1")
        if order_code:
            return _redir(request, f"/orders/{order_code}")
        if customer_url:
            return _redir(request, customer_url)
        return _redir(request, f"/?nf={nf}")

    return router

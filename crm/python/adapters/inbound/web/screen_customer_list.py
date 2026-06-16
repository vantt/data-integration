"""Web adapter — S02 Customer List & Search screen.

FastAPI router mirroring screen_customer_list.go.
Serves full paginated HTML page + HTMX live-search fragment.
No business logic — thin adapter only.
"""
from __future__ import annotations

import logging
from typing import Optional, Protocol

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from crm.python.domain.entities.party import Party

log = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 30

# ── Service protocols ─────────────────────────────────────────────────────────


class PartyLister(Protocol):
    def list_all(self, offset: int, limit: int) -> tuple[list[Party], int]: ...
    def search_by_name(self, q: str) -> list[str]: ...
    def get_by_id(self, party_id: str) -> Optional[Party]: ...
    def list_by_phone(self, q: str) -> list[Party]: ...
    def find_by_identity(self, identity_type: str, identity_value: str) -> Optional[Party]: ...


# ── Router factory ────────────────────────────────────────────────────────────


def make_customer_list_router(
    templates: Jinja2Templates,
    parties: PartyLister,
) -> APIRouter:
    """Return APIRouter wired with all Customer List routes."""
    router = APIRouter()

    def _search_parties(q: str) -> list[Party]:
        """FTS name search + phone prefix search, deduplicated."""
        seen: set[str] = set()
        out: list[Party] = []

        try:
            ids = parties.search_by_name(q)
            for pid in ids:
                if pid in seen:
                    continue
                p = parties.get_by_id(pid)
                if p is not None and not p.is_merged:
                    out.append(p)
                    seen.add(pid)
        except Exception as exc:
            log.error("customer list: name search %r: %s", q, exc)

        try:
            for p in parties.list_by_phone(q):
                if p.party_id not in seen and not p.is_merged:
                    out.append(p)
                    seen.add(p.party_id)
        except Exception as exc:
            log.error("customer list: phone search %r: %s", q, exc)

        return out

    # ── Lookup by Sapo customer_key → redirect to party page ─────────────────

    @router.get("/customers/by-key/{customer_key}", response_class=HTMLResponse)
    async def handle_customer_by_key(request: Request, customer_key: str) -> Response:
        """Resolve a Sapo customer_key (numeric string) to a CRM party and redirect."""
        customer_key = customer_key.strip()
        party = None
        try:
            # customer_key is the numeric Sapo customer_id stored as identity_value
            party = parties.find_by_identity("sapo_customer", customer_key)
        except Exception as exc:
            log.error("customer by-key: find %r: %s", customer_key, exc)
        if party is not None:
            return RedirectResponse(url=f"/customers/{party.party_id}", status_code=302)
        # Fall back to search page
        return RedirectResponse(url=f"/customers?q={customer_key}", status_code=302)

    # ── Full page ─────────────────────────────────────────────────────────────

    @router.get("/customers", response_class=HTMLResponse)
    async def handle_customer_list(request: Request) -> Response:
        q = request.query_params.get("q", "").strip()
        page = _query_int(request, "page", 1)
        if page < 1:
            page = 1
        offset = (page - 1) * DEFAULT_PAGE_SIZE

        if q:
            party_list = _search_parties(q)
            total = len(party_list)
        else:
            try:
                party_list, total = parties.list_all(offset, DEFAULT_PAGE_SIZE)
            except Exception as exc:
                log.error("customer list: list all: %s", exc)
                party_list, total = [], 0

        return templates.TemplateResponse(
            "customer_list.html",
            {
                "request": request,
                "parties": party_list,
                "total": total,
                "page": page,
                "page_size": DEFAULT_PAGE_SIZE,
                "query": q,
            },
        )

    # ── HTMX live-search fragment (tbody rows only) ───────────────────────────

    @router.get("/customers/search", response_class=HTMLResponse)
    async def handle_customer_search(request: Request) -> Response:
        q = request.query_params.get("q", "").strip()

        if q:
            party_list = _search_parties(q)
        else:
            try:
                party_list, _ = parties.list_all(0, DEFAULT_PAGE_SIZE)
            except Exception as exc:
                log.error("customer search: list: %s", exc)
                party_list = []

        return templates.TemplateResponse(
            "fragments/customer_list_rows.html",
            {"request": request, "parties": party_list},
        )

    return router


# ── Pure helpers ──────────────────────────────────────────────────────────────


def _query_int(request: Request, key: str, default: int) -> int:
    """Extract an integer query param with a fallback default."""
    raw = request.query_params.get(key, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default

"""Use-case services. Depend on PORTS only; return DOMAIN objects.

Thin orchestration today — the seam where cross-cutting use-case rules (caching, auth,
audit) would live later without touching domain or adapters.
"""
from __future__ import annotations

from ..domain.customer import CustomerDetail
from ..domain.order import OrderDetail
from ..domain.ports import CustomerRepository, OrderRepository, SearchPort
from ..domain.shared import SearchResolution


class OrderService:
    def __init__(self, repo: OrderRepository) -> None:
        self._repo = repo

    def get_detail(self, order_code: str) -> OrderDetail | None:
        code = (order_code or "").strip()
        if not code:
            return None
        return self._repo.get_by_code(code)


class CustomerService:
    def __init__(self, repo: CustomerRepository) -> None:
        self._repo = repo

    def get_detail(self, customer_id: str) -> CustomerDetail | None:
        cid = (customer_id or "").strip()
        if not cid:
            return None
        return self._repo.get_by_id(cid)


class SearchService:
    """Resolves a header search into a navigation outcome."""

    def __init__(self, search: SearchPort) -> None:
        self._search = search

    def resolve(self, mode: str, query: str) -> SearchResolution:
        q = (query or "").strip()
        if not q:
            return SearchResolution(not_found=True)

        if mode == "order":
            code = self._search.resolve_order(q)
            if code:
                return SearchResolution(redirect_to=f"/orders/{code}")
            return SearchResolution(not_found=True)

        # default: customer
        hits = self._search.resolve_customer(q)
        if not hits:
            return SearchResolution(not_found=True)
        if len(hits) == 1:
            return SearchResolution(redirect_to=f"/customers/{hits[0].customer_id}")
        return SearchResolution(customer_hits=hits)

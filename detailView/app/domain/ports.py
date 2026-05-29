"""Ports — interfaces the application depends on. Adapters implement these.

Driven (secondary) ports only. Pure: returns domain objects, no DB/HTTP types leak through.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .customer import CustomerDetail
from .order import OrderDetail
from .shared import CustomerHit


@runtime_checkable
class OrderRepository(Protocol):
    def get_by_code(self, order_code: str) -> OrderDetail | None:
        """Full single-order aggregate, or None if the code does not exist."""
        ...


@runtime_checkable
class CustomerRepository(Protocol):
    def get_by_id(self, customer_id: str) -> CustomerDetail | None:
        """Full single-customer aggregate (incl. order history), or None."""
        ...


@runtime_checkable
class SearchPort(Protocol):
    def resolve_order(self, query: str) -> str | None:
        """Return the canonical order_code for an exact-ish match, else None."""
        ...

    def resolve_customer(self, query: str) -> list[CustomerHit]:
        """Resolve a customer by id / phone / email. May return 0, 1, or many hits."""
        ...

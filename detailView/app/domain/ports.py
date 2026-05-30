"""Ports — interfaces the application depends on. Adapters implement these.

Driven (secondary) ports only. Pure: returns domain objects, no DB/HTTP types leak through.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from .customer import CustomerDetail
from .order import OrderDetail
from .shared import CustomerHit, DataQualitySummary


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


class CapabilityPort(Protocol):
    """Read-only introspection of the serving layer schema and filesystem freshness.

    Schema queries are cached (5 min TTL). Filesystem reads are lightweight.
    Implementations MUST be safe for concurrent calls (threading.Lock).
    """

    def view_exists(self, view_name: str) -> bool:
        """True if view_name appears in information_schema."""
        ...

    def has_column(self, view_name: str, column_name: str) -> bool:
        """True if view_name has a column named column_name."""
        ...

    def data_version(self) -> str:
        """Lexically-max parquet basename across all rolling dirs (filesystem only).

        Format: '{table}_{YYYYMMDDHHMMSS}.parquet'. Stable, monotone sort key.
        Returns 'unknown' when the rolling dir is empty or absent.
        """
        ...

    def freshness(self, view_name: str) -> datetime | None:
        """Latest parquet mtime for view_name's rolling dir, or None."""
        ...

    def known_tables(self) -> frozenset[str]:
        """Tables listed in .known_tables.json (lock-free JSON read)."""
        ...


class DataQualityPort(Protocol):
    """Pre-aggregated system-level coverage metrics.

    Reads from mart_data_quality (1-row view) + capability signals.
    Cached ~5 min in-process. Returns None when the mart view is absent.
    """

    def coverage_metrics(self) -> DataQualitySummary | None:
        """System-wide coverage snapshot, or None when mart unavailable."""
        ...

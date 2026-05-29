"""Composition root — the ONLY place that wires adapters to ports.

Keeps the dependency graph explicit: outbound DuckDB adapters implement the ports,
application services depend on those ports, the web adapter depends on the services.
"""
from __future__ import annotations

from dataclasses import dataclass

from .adapters.outbound.duckdb import (
    DuckDbCustomerRepository,
    DuckDbOrderRepository,
    DuckDbSearchAdapter,
)
from .application.services import CustomerService, OrderService, SearchService
from .config import Settings


@dataclass(frozen=True)
class Services:
    order: OrderService
    customer: CustomerService
    search: SearchService


def build_services(settings: Settings) -> Services:
    """Instantiate driven adapters and inject them into the application services."""
    db_path = settings.olap_db_path
    return Services(
        order=OrderService(DuckDbOrderRepository(db_path)),
        customer=CustomerService(DuckDbCustomerRepository(db_path)),
        search=SearchService(DuckDbSearchAdapter(db_path)),
    )

"""Composition root — the ONLY place that wires adapters to ports.

Keeps the dependency graph explicit: outbound DuckDB adapters implement the ports,
application services depend on those ports, the web adapter depends on the services.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .adapters.outbound.duckdb import (
    DuckDbCustomerRepository,
    DuckDbOrderRepository,
    DuckDbSearchAdapter,
)
from .adapters.outbound.duckdb.capability_adapter import DuckDbCapabilityAdapter
from .adapters.outbound.duckdb.dataquality_adapter import DuckDbDataQualityAdapter
from .application.services import CustomerService, OrderService, SearchService
from .config import Settings


@dataclass(frozen=True)
class Services:
    order: OrderService
    customer: CustomerService
    search: SearchService
    # Capability and data-quality are Optional so the app starts even when the
    # rolling dir / known_tables_path don't exist yet (e.g. fresh container).
    capability: Optional[DuckDbCapabilityAdapter]
    data_quality: Optional[DuckDbDataQualityAdapter]


def build_services(settings: Settings) -> Services:
    """Instantiate driven adapters and inject them into the application services."""
    db_path = settings.olap_db_path
    capability = DuckDbCapabilityAdapter(
        db_path=db_path,
        rolling_dir=settings.rolling_dir,
        known_tables_path=settings.known_tables_path,
    )
    data_quality = DuckDbDataQualityAdapter(
        db_path=db_path,
        capability=capability,
    )
    return Services(
        order=OrderService(DuckDbOrderRepository(db_path)),
        customer=CustomerService(DuckDbCustomerRepository(db_path)),
        search=SearchService(DuckDbSearchAdapter(db_path)),
        capability=capability,
        data_quality=data_quality,
    )

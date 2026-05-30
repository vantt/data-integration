"""DuckDB read-only outbound adapter.

Public surface: the five driven-port implementations plus the connection helper.
"""
from .capability_adapter import DuckDbCapabilityAdapter
from .connection import read_only_connect, read_only_connection
from .customer_repository import DuckDbCustomerRepository
from .dataquality_adapter import DuckDbDataQualityAdapter
from .order_repository import DuckDbOrderRepository
from .search import DuckDbSearchAdapter

__all__ = [
    "read_only_connect",
    "read_only_connection",
    "DuckDbOrderRepository",
    "DuckDbCustomerRepository",
    "DuckDbSearchAdapter",
    "DuckDbCapabilityAdapter",
    "DuckDbDataQualityAdapter",
]

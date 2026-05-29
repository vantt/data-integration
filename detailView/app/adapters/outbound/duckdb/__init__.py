"""DuckDB read-only outbound adapter.

Public surface: the three driven-port implementations plus the connection helper.
"""
from .connection import read_only_connect, read_only_connection
from .customer_repository import DuckDbCustomerRepository
from .order_repository import DuckDbOrderRepository
from .search import DuckDbSearchAdapter

__all__ = [
    "read_only_connect",
    "read_only_connection",
    "DuckDbOrderRepository",
    "DuckDbCustomerRepository",
    "DuckDbSearchAdapter",
]

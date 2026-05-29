"""Pytest fixtures: a self-contained temp DuckDB seeded with the views-as-tables.

The live serving olap.duckdb defines its views over parquet files that only exist inside
the container, so it is NOT queryable on the host for *data*. These fixtures build a
deterministic standalone DB whose table names + column names mirror the serving layer,
so the repositories run their real SQL against real DuckDB — no mocks.

Seeded scenario:
- ORD-NORMAL : domestic order, has COGS, 2 line items, 1 payment, returns (by order_code).
- ORD-US     : US CrossBorder order, fact_orders.net_revenue = 0 + fact_us_shipment row.
- ORD-NOCOGS : domestic order with has_cogs = FALSE.
- CUST-1      : RETAIL customer owning ORD-NORMAL + ORD-NOCOGS, with a status snapshot.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from tests.seed_schema import seed_database


@pytest.fixture(scope="session")
def seeded_db_path(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Create the seeded temp DuckDB once per session; return its absolute path."""
    db_path = tmp_path_factory.mktemp("olap") / "olap_test.duckdb"
    con = duckdb.connect(str(db_path))
    try:
        con.execute("SET TimeZone='Asia/Ho_Chi_Minh'")
        seed_database(con)
    finally:
        con.close()
    return str(db_path)


@pytest.fixture(scope="session")
def live_db_path() -> str | None:
    """Path to the real serving DB if present on this host, else None (smoke-test gate)."""
    candidate = Path(
        r"D:\vantt\app\data-integration\app_data\data_lake\serving\olap.duckdb"
    )
    return str(candidate) if candidate.is_file() else None

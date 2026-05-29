"""Optional integration smoke test — gated on the real serving DB being present.

The live olap.duckdb defines its views over parquet files that only exist inside the
container, so on a bare host most data queries fail with IOException. We therefore only
assert that the connection opens read-only with the ICT timezone and that the expected
view names exist — never that rows come back.
"""
from __future__ import annotations

import pytest

from app.adapters.outbound.duckdb.connection import read_only_connection


@pytest.mark.integration
def test_live_connection_opens_read_only_with_ict(live_db_path: str | None) -> None:
    if live_db_path is None:
        pytest.skip("live olap.duckdb not present on this host")

    with read_only_connection(live_db_path) as conn:
        tz = conn.execute("SELECT current_setting('TimeZone')").fetchone()[0]
        assert tz == "Asia/Ho_Chi_Minh"

        names = {
            r[0]
            for r in conn.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='main'"
            ).fetchall()
        }
        for required in (
            "fact_orders",
            "fact_order_economics",
            "fact_us_shipment_economics",
            "dim_customers",
            "mart_customer_status_snapshot_monthly",
        ):
            assert required in names, f"missing serving view: {required}"

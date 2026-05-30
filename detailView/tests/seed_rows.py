"""Deterministic fixture rows for the standalone test DuckDB.

Scenario:
- ORD-NORMAL     : domestic order, has COGS, 2 line items, 1 payment, returns (by order_code).
                   Has 2 shipment legs (SHIP-A delivered, SHIP-B shipping) in fact_fulfillments.
- ORD-US         : US CrossBorder order, fact_orders.net_revenue = 0 + fact_us_shipment row.
- ORD-NOCOGS     : domestic order with has_cogs = FALSE.
- ORD-BY-ID-ONLY : order whose order_id ('9991') differs from order_code ('CODE-ALPHA');
                   exercises the order_id fallback in search_order.sql.
- CUST-1         : RETAIL customer owning ORD-NORMAL + ORD-NOCOGS, with a status snapshot.
- CUST-2         : WHOLESALE customer owning ORD-US, no status snapshot (RETAIL-only mart).
"""
from __future__ import annotations

import duckdb


def seed_rows(con: duckdb.DuckDBPyConnection) -> None:
    _seed_dims(con)
    _seed_orders(con)
    _seed_economics(con)
    _seed_children(con)
    _seed_customers(con)
    _seed_fulfillments(con)
    _seed_data_quality(con)


def _seed_dims(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        "INSERT INTO dim_channels VALUES "
        "('CH1','Shopee Official','SHP','MARKETPLACE','SOCIAL','shopee','BrandA','Domestic'),"
        "('CHUS','US CrossBorder','USX','EXPORT','DIRECT','web','BrandA','Export')"
    )
    con.execute("INSERT INTO dim_staff VALUES ('ST1','Alice Seller','alice@x.vn')")
    con.execute("INSERT INTO dim_teams VALUES ('TM1','Team North')")
    con.execute("INSERT INTO dim_branch_location VALUES ('BL1','HCMC Warehouse')")
    con.execute("INSERT INTO dim_geography VALUES ('GEO1','Ho Chi Minh','District 1','Ben Nghe','Vietnam')")
    con.execute("INSERT INTO dim_promotions VALUES ('PR1','SALE10')")
    con.execute(
        "INSERT INTO dim_products VALUES "
        "('PK1','SKU-001','Serum A','30ml','BrandA','Skincare','bottle'),"
        "('PK2','SKU-002','Cream B','50g','BrandA','Skincare','jar')"
    )
    con.execute("INSERT INTO dim_payment_methods VALUES ('PM1','COD','cash')")


def _seed_orders(con: duckdb.DuckDBPyConnection) -> None:
    # order_id, order_code, customer_key, ship_geo, promo, branch, channel,
    # seller, creator, team, status, pay_status, fulfill, gross, disc, net, tax, total,
    # first_shipped, ttc_hours, max_disc_rate, disc_nature, ship_addr, order_ts, updated_at
    rows = [
        ("1001", "ORD-NORMAL", "CK1", "GEO1", "PR1", "BL1", "CH1", "ST1", "ST1", "TM1",
         "COMPLETED", "PAID", "COMPLETED", 1200000, 200000, 1000000, 100000, 1100000,
         "2026-01-10 09:00:00+07", 24, 10.0, "voucher_promotional", "12 Le Loi",
         "2026-01-09 08:00:00+07", "2026-01-11 08:00:00+07"),
        # US order: net_revenue=0 in fact_orders
        ("1002", "ORD-US", "CK2", "GEO1", None, "BL1", "CHUS", "ST1", "ST1", "TM1",
         "COMPLETED", "PAID", "COMPLETED", 0, 0, 0, 0, 0,
         None, None, 0.0, None, "99 Export St",
         "2026-02-01 10:00:00+07", "2026-02-02 10:00:00+07"),
        ("1003", "ORD-NOCOGS", "CK1", "GEO1", None, "BL1", "CH1", "ST1", "ST1", "TM1",
         "COMPLETED", "PAID", "COMPLETED", 600000, 0, 600000, 60000, 660000,
         "2026-03-05 09:00:00+07", 12, 0.0, None, "12 Le Loi",
         "2026-03-04 08:00:00+07", "2026-03-06 08:00:00+07"),
        # order_id differs from order_code — exercises the order_id fallback path.
        # Uses CK3 (no dim_customers row) so it doesn't inflate CK1/CK2 aggregates.
        ("9991", "CODE-ALPHA", "CK3", "GEO1", None, "BL1", "CH1", "ST1", "ST1", "TM1",
         "COMPLETED", "PAID", "COMPLETED", 500000, 0, 500000, 50000, 550000,
         "2026-04-01 09:00:00+07", 10, 0.0, None, "12 Le Loi",
         "2026-03-31 08:00:00+07", "2026-04-02 08:00:00+07"),
    ]
    con.executemany(
        "INSERT INTO fact_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )


def _seed_economics(con: duckdb.DuckDBPyConnection) -> None:
    # order_id, order_code, cogs, has_cogs, gross_profit, margin, shopee fees(5),
    # has_platform_fees, channel_net_profit, channel_net_margin, cod, carrier,
    # return_amount, return_count, has_returns
    rows = [
        ("1001", "ORD-NORMAL", 400000.0, True, 600000, 0.6,
         50000, 5000, 1000, 2000, 942000, True, 542000, 0.542, 1100000, "GHTK",
         150000, 1, True),
        ("1002", "ORD-US", None, False, 0, None,
         None, None, None, None, None, False, 0, None, None, None,
         0, 0, False),
        ("1003", "ORD-NOCOGS", None, False, 600000, 1.0,
         None, None, None, None, None, False, 600000, 1.0, 660000, "JT",
         0, 0, False),
        # Minimal economics for the order_id-fallback fixture; no COGS, no returns.
        ("9991", "CODE-ALPHA", None, False, 500000, 1.0,
         None, None, None, None, None, False, 500000, 1.0, 550000, "JT",
         0, 0, False),
    ]
    con.executemany(
        "INSERT INTO fact_order_economics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )


def _seed_children(con: duckdb.DuckDBPyConnection) -> None:
    # US economics row only for ORD-US
    con.execute(
        "INSERT INTO fact_us_shipment_economics VALUES "
        "('1002','ORD-US', 4500000.0000, 4950000.0000, 2, TRUE, 1.0)"
    )
    # 2 line items for ORD-NORMAL (plus a US line that should NOT surface us price)
    con.executemany(
        "INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?,?)",
        [
            ("PK1", "1001", "5001", 2, 700000, 50000, 20000, 120),
            ("PK2", "1001", "5002", 1, 300000, 0, 10000, 200),
            ("PK1", "1002", "5003", 2, 0, 0, 0, 120),
        ],
    )
    con.execute(
        "INSERT INTO fact_payments VALUES "
        "('PAYK1','1001','PM1', 1100000, 'paid', '2026-01-10 09:30:00+07', '2026-01-10 09:30:00+07')"
    )
    con.executemany(
        "INSERT INTO fact_order_costs VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            ("1001", "ORD-NORMAL", "cogs", "COGS", 400000, None, None, "misa", "INV-1", "actual"),
            ("1001", "ORD-NORMAL", "platform_service", "PLATFORM_FEE", 50000, None, None,
             "shopee", "ORD-NORMAL", "actual"),
        ],
    )
    # Returns join by order_code; order_id stored as BIGINT in this table.
    con.execute(
        "INSERT INTO fact_order_returns VALUES "
        "('RET1', 1001, 'ORD-NORMAL', DATE '2026-01-20', 150000, 1, 'COMPLETED', "
        "'REFUNDED', 'damaged')"
    )


def _seed_fulfillments(con: duckdb.DuckDBPyConnection) -> None:
    """Two shipment legs for ORD-NORMAL; exercises all search paths (code, id, tracking)."""
    # fulfillment_id, fulfillment_code, order_id, order_code,
    # tracking_code, carrier_id, shipping_service,
    # status, cod_amount, created_at, shipped_at
    rows = [
        (
            "FF-001", "SHIP-A", "1001", "ORD-NORMAL",
            "GHTK-TRACK-001", "GHTK", "standard",
            "DELIVERED", 1100000,
            "2026-01-09 10:00:00+07", "2026-01-10 14:00:00+07",
        ),
        (
            "FF-002", "SHIP-B", "1001", "ORD-NORMAL",
            "GHTK-TRACK-002", "GHTK", "express",
            "SHIPPING", None,
            "2026-01-09 11:00:00+07", None,
        ),
    ]
    con.executemany(
        "INSERT INTO fact_fulfillments VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )


def _seed_data_quality(con: duckdb.DuckDBPyConnection) -> None:
    """Single-row mart_data_quality fixture matching the FROZEN contract columns."""
    con.execute(
        "INSERT INTO mart_data_quality VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            "DQ-2026-05-30",                 # dq_key
            "2026-05-30 07:11:44+00",        # as_of_utc (UTC)
            3352,                            # total_orders
            29.3,                            # cogs_rate_pct
            2.7,                             # platform_fees_rate_pct
            94.5,                            # fulfillment_coverage_pct
            0.1,                             # return_rate_pct
            35.4,                            # us_share_pct
            18.8,                            # carrier_null_rate_pct
            100.0,                           # acq_source_null_rate_pct
        ],
    )


def _seed_customers(con: duckdb.DuckDBPyConnection) -> None:
    con.executemany(
        "INSERT INTO dim_customers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("CK1", "CUST-1", "Nguyen Van A", "a@example.com", "0901234567",
             "1990-05-15", "M", "12 Le Loi", "Ben Nghe", "District 1", "Ho Chi Minh",
             "Vietnam", "GEO_HCMC", 120, "RETAIL", "TYPE_RETAIL", "VALUE_GOLD",
             "LIFECYCLE_ACTIVE", "CHANNEL_MARKETPLACE", "PRODUCT_FINE_JAPAN",
             "PAYMENT_COD", 1760000, 2, "2026-01-09 08:00:00+07",
             "2026-03-04 08:00:00+07", 30, 54, "2025-12-01 00:00:00+07",
             "2026-03-06 08:00:00+07"),
            ("CK2", "CUST-2", "Export Buyer", "buyer@us.com", "+1 (415) 555-0100",
             None, None, "99 Export St", None, None, None, "US", "OTHER",
             0, "WHOLESALE", "TYPE_WHOLESALE", "VALUE_SILVER", "LIFECYCLE_NEW",
             "CHANNEL_DIRECT", "MULTI", "PAYMENT_PREPAID", 0, 1,
             "2026-02-01 10:00:00+07", "2026-02-01 10:00:00+07", 100, 0,
             "2026-02-01 00:00:00+07", "2026-02-02 10:00:00+07"),
        ],
    )
    con.execute(
        "INSERT INTO mart_customer_status_snapshot_monthly VALUES "
        "('CK1', DATE '2026-02-28', 'ACTIVE', FALSE, 19, 'VALUE_GOLD')"
    )

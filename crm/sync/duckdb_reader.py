"""
duckdb_reader.py — read-only DuckDB reader for the warehouse reverse-ETL.

Opens olap.duckdb with read_only=True (never acquires a write-lock on the live file).
Falls back to sapo_export_latest.duckdb if the primary path is unavailable.

Column lists are pinned explicitly; a missing column raises MissingColumnError
immediately (dbt-rename guard — fail-fast rather than silently pulling NULLs).

Convention (per warehouse memory):
  - net_revenue          (VAT-inclusive)     NOT gross_revenue
  - realized_margin_pct  (H010-corrected)    NOT gross_margin_pct
  - date_key             ICT YYYYMMDD        pass-through, do NOT recompute
  - customer_type + fact_payments            NOT reliable; not fetched
"""

from __future__ import annotations

import os
from typing import Any

try:
    import duckdb
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "duckdb is required. Install it with: pip install duckdb>=1.0"
    ) from exc

from crm.sync.config import olap_path, olap_fallback_path


class MissingColumnError(RuntimeError):
    """Raised when a required column is absent from the DuckDB result set."""


# ─── Column contracts (pin to prevent silent breakage on dbt renames) ────────

# dim_customers columns used for customer_insight
_DIM_CUSTOMERS_INSIGHT_COLS = [
    "customer_key",
    "customer_id",
    "value_group",
    "customer_status",
    "next_purchase_signal",
    "predicted_next_purchase_date",
    "avg_days_between_orders",
    "avg_order_spend",
    "discount_sensitivity",
    "cancel_rate",
    "last_purchased_sku",
    "top_affinity_product",
    "second_affinity_product",
    "channel_preference",
    "lifetime_contribution_margin",
    "is_margin_negative",
]

# dim_customers columns used for customer_base
_DIM_CUSTOMERS_BASE_COLS = [
    "customer_key",
    "customer_id",
    "customer_code",
    "display_name",
    "phone",
    "email",
    "customer_group",
    "first_order_date",
]

# mart_product_health columns for product_insight
_MART_PRODUCT_HEALTH_COLS = [
    "product_key",
    "sku",
    "abc_class",
    "health_class",
    "lifecycle_stage",
    "velocity_momentum",
    "oos_risk",
    "realized_margin_pct",
    "discount_dependency",
]

# mart_customer_action_queue columns for action_queue
_MART_ACTION_QUEUE_COLS = [
    "action_id",
    "customer_key",
    "action_type",
    "rationale_vi",
    "value_at_stake_vnd",
    "priority",
    "generated_date",
]

# dim_products columns for product catalog
_DIM_PRODUCTS_COLS = [
    "product_key",
    "sku",
    "variant_id",
    "product_name",
    "brand",
    "unit_price",
    "is_active",
]

# fact_orders columns for order header (slim — no line items)
_FACT_ORDERS_COLS = [
    "order_id",
    "order_code",
    "customer_id",
    "date_key",
    "net_revenue",
    "status",
    "channel",
    "item_count",
]


def _open_conn(path: str) -> "duckdb.DuckDBPyConnection":
    """Open a DuckDB connection in read-only mode."""
    return duckdb.connect(path, read_only=True)


def open_warehouse() -> "duckdb.DuckDBPyConnection":
    """
    Open the warehouse DuckDB read-only.

    Tries CRM_OLAP_PATH first; falls back to sapo_export_latest.duckdb in the
    same directory if the primary file does not exist.

    Raises FileNotFoundError when neither path resolves to an existing file.
    """
    primary = olap_path()
    fallback = olap_fallback_path()

    if os.path.exists(primary):
        return _open_conn(primary)

    if os.path.exists(fallback):
        import warnings
        warnings.warn(
            f"Primary warehouse '{primary}' not found; using fallback '{fallback}'",
            stacklevel=2,
        )
        return _open_conn(fallback)

    raise FileNotFoundError(
        f"Warehouse DuckDB not found at '{primary}' or fallback '{fallback}'. "
        "Set CRM_OLAP_PATH to the correct path."
    )


def _check_columns(rows: list[dict], required: list[str], source: str) -> None:
    """Raise MissingColumnError if any required column is absent from the result rows.

    Returns early on empty results — the fail-fast contract for empty tables relies on
    _fetch() raising MissingColumnError on BinderException (column absent at query time).
    Standalone callers must always go through _fetch() to guarantee the guard fires.
    """
    if not rows:
        return  # empty result — nothing to check
    actual = set(rows[0].keys())
    missing = [c for c in required if c not in actual]
    if missing:
        raise MissingColumnError(
            f"[dbt-rename guard] Source '{source}' is missing columns: {missing}. "
            "Update the column list in duckdb_reader.py to match the current dbt model."
        )


def _fetch(conn: "duckdb.DuckDBPyConnection", sql: str) -> list[dict[str, Any]]:
    """
    Execute sql and return list-of-dicts.

    DuckDB raises BinderException when a pinned column name is absent from the table
    (i.e. after a dbt rename).  We surface this as MissingColumnError so callers
    always see the same error type regardless of whether the table is empty or not.
    """
    try:
        rel = conn.execute(sql)
    except Exception as exc:
        msg = str(exc)
        # DuckDB BinderException text: 'Referenced column "foo" not found in FROM clause'
        if "not found in FROM clause" in msg or "Referenced column" in msg:
            raise MissingColumnError(
                f"[dbt-rename guard] Column missing from warehouse query — "
                f"update the column list in duckdb_reader.py. DuckDB error: {exc}"
            ) from exc
        raise
    cols = [desc[0] for desc in rel.description]
    return [dict(zip(cols, row)) for row in rel.fetchall()]


def fetch_customer_insight(conn: "duckdb.DuckDBPyConnection") -> list[dict]:
    """Read insight fields from main_marts.dim_customers."""
    cols = ", ".join(_DIM_CUSTOMERS_INSIGHT_COLS)
    sql = f"SELECT {cols} FROM main_marts.dim_customers"
    rows = _fetch(conn, sql)
    _check_columns(rows, _DIM_CUSTOMERS_INSIGHT_COLS, "main_marts.dim_customers[insight]")
    return rows


def fetch_customer_base(conn: "duckdb.DuckDBPyConnection") -> list[dict]:
    """Read base attributes from main_marts.dim_customers."""
    cols = ", ".join(_DIM_CUSTOMERS_BASE_COLS)
    sql = f"SELECT {cols} FROM main_marts.dim_customers"
    rows = _fetch(conn, sql)
    _check_columns(rows, _DIM_CUSTOMERS_BASE_COLS, "main_marts.dim_customers[base]")
    return rows


def fetch_product_insight(conn: "duckdb.DuckDBPyConnection") -> list[dict]:
    """Read product health insight from main_marts.mart_product_health."""
    cols = ", ".join(_MART_PRODUCT_HEALTH_COLS)
    sql = f"SELECT {cols} FROM main_marts.mart_product_health"
    rows = _fetch(conn, sql)
    _check_columns(rows, _MART_PRODUCT_HEALTH_COLS, "main_marts.mart_product_health")
    return rows


def fetch_action_queue(conn: "duckdb.DuckDBPyConnection") -> list[dict]:
    """Read customer action queue from main_marts.mart_customer_action_queue."""
    cols = ", ".join(_MART_ACTION_QUEUE_COLS)
    sql = f"SELECT {cols} FROM main_marts.mart_customer_action_queue"
    rows = _fetch(conn, sql)
    _check_columns(rows, _MART_ACTION_QUEUE_COLS, "main_marts.mart_customer_action_queue")
    return rows


def fetch_products(conn: "duckdb.DuckDBPyConnection") -> list[dict]:
    """Read product catalog from main_marts.dim_products."""
    cols = ", ".join(_DIM_PRODUCTS_COLS)
    sql = f"SELECT {cols} FROM main_marts.dim_products"
    rows = _fetch(conn, sql)
    _check_columns(rows, _DIM_PRODUCTS_COLS, "main_marts.dim_products")
    return rows


def fetch_order_hdr(
    conn: "duckdb.DuckDBPyConnection",
    since_date_key: int | None = None,
) -> list[dict]:
    """
    Read order headers (slim, no line items) from main_marts.fact_orders.

    since_date_key: if provided, fetch only orders with date_key > since_date_key
                    (incremental high-water mark).  date_key is ICT YYYYMMDD —
                    pass-through from the warehouse; do NOT recompute.
    """
    cols = ", ".join(_FACT_ORDERS_COLS)
    if since_date_key is not None:
        # Use >= (not >) so same-day late-arriving orders are re-pulled on the next run.
        # date_key is day-granularity ICT (YYYYMMDD); idempotent upsert in cache.db dedupes.
        sql = (
            f"SELECT {cols} FROM main_marts.fact_orders "
            f"WHERE date_key >= {int(since_date_key)}"
        )
    else:
        sql = f"SELECT {cols} FROM main_marts.fact_orders"
    rows = _fetch(conn, sql)
    _check_columns(rows, _FACT_ORDERS_COLS, "main_marts.fact_orders")
    return rows

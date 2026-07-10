"""Reads from the serving DuckDB (transformation output) that feed suggestion computation:
actual cash movement (for recurring rolling-average) and reserve-status gap/deadline data
(for reserve required_monthly_adj). Read-only, no credentials needed — DBT_DATA_LAKE_PATH
must point at a data lake with a built `serving/olap.duckdb` (i.e. `dbt build` already ran).
"""
import os

from .fetch import ValidationError


def _fetch_recurring_actuals_from_duckdb(serving_db_path: str, window_months: list) -> list:
    """Query fact_cash_movement for SUM(amount) per (cashflow_line, direction) over
    window_months. window_months values are our own computed 'YYYY-MM-01' strings (never
    user input) — safe to interpolate directly into the IN(...) list.
    """
    import duckdb

    if not os.path.exists(serving_db_path):
        raise ValidationError(
            f"Serving DB không tìm thấy tại {serving_db_path} — cần chạy dbt build trước khi tính gợi ý"
        )
    conn = duckdb.connect(serving_db_path, read_only=True)
    try:
        placeholders = ", ".join(f"'{m}'" for m in window_months)
        rows = conn.execute(f"""
            SELECT cashflow_line, direction, SUM(amount) AS amount
            FROM fact_cash_movement
            WHERE NOT is_internal_transfer
              AND cashflow_line IS NOT NULL
              AND cashflow_line NOT IN ('Chuyển nội bộ tiền', 'Khác')
              AND period_month IN ({placeholders})
            GROUP BY 1, 2
        """).fetchall()
        return [{"cashflow_line": r[0], "direction": r[1], "amount": r[2]} for r in rows]
    finally:
        conn.close()


def _fetch_account_taxonomy_from_duckdb(serving_db_path: str) -> dict:
    """Query dim_gl_account for (account_code -> cashflow_line). Used by budget_transform to
    validate recurring rows' account_code (parsed from the __REF dropdown label) and to derive
    a display cashflow_line for the seed (legacy bucket, kept for the existing Metabase
    "Cashflow Line" filter — see plans/260709-1415-budget-account-level-remap/phase-03).
    """
    import duckdb

    if not os.path.exists(serving_db_path):
        raise ValidationError(
            f"Serving DB không tìm thấy tại {serving_db_path} — cần chạy dbt build trước khi sync budget"
        )
    conn = duckdb.connect(serving_db_path, read_only=True)
    try:
        rows = conn.execute("SELECT account_code, cashflow_line FROM dim_gl_account").fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        conn.close()


def _fetch_reserve_status_from_duckdb(serving_db_path: str) -> list:
    """Query mart_cashflow_reserve_status for has-a-deadline reserve items."""
    import duckdb

    if not os.path.exists(serving_db_path):
        raise ValidationError(
            f"Serving DB không tìm thấy tại {serving_db_path} — cần chạy dbt build trước khi tính gợi ý"
        )
    conn = duckdb.connect(serving_db_path, read_only=True)
    try:
        rows = conn.execute("""
            SELECT cashflow_line, required_monthly_adj
            FROM mart_cashflow_reserve_status
            WHERE item_target IS NOT NULL AND target_month IS NOT NULL
        """).fetchall()
        return [{"cashflow_line": r[0], "required_monthly_adj": r[1]} for r in rows]
    finally:
        conn.close()

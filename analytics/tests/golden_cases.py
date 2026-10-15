"""Metric × window pairs locked by golden SQL (tests/golden/<metric>__<window>[__runtime].sql).

Every metric is locked on the windows the CEO Weekly Pulse uses for it; `net_sales` is locked on
every window, and once with the run-time `as_of` (yesterday when the SQL runs).
"""
from __future__ import annotations

from pathlib import Path

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
AS_OF = "2026-10-11"

WEEK = ("wtd", "prev_week_full")
CASES: list[tuple[str, str, bool]] = []  # (metric, window, run-time as_of)
for _metric in ("gross_revenue", "discount_amount", "orders_count", "active_orders_count", "cancelled_orders",
                "aov", "discount_rate", "return_count", "new_customers", "returning_customers",
                "net_sales_returning_customers", "returning_revenue_share", "channel_net_profit", "gross_profit",
                "net_sales_with_cogs", "gross_margin_pct", "orders_with_cogs", "cogs_coverage_pct"):
    CASES += [(_metric, w, False) for w in WEEK]
for _metric in ("gmv_target", "gmv_pace_index", "gmv_month_end_forecast", "gmv_required_daily_run_rate",
                "gross_revenue"):
    CASES.append((_metric, "mtd_before_as_of", False))
for _metric in ("new_customer_orders", "returning_customer_orders"):
    CASES.append((_metric, "prev_week_start_to_date", False))
for _w in ("wtd", "prev_week_full", "prev_wtd_same_span", "mtd", "mtd_before_as_of", "prev_week_start_to_date",
           "month_full", "prev_month_full", "last_7_days"):
    CASES.append(("net_sales", _w, False))
CASES.append(("net_sales", "wtd", True))


def golden_path(metric: str, window: str, runtime: bool) -> Path:
    return GOLDEN_DIR / f"{metric}__{window}{'__runtime' if runtime else ''}.sql"

"""Suggestion targeting/compute logic for the "Gợi Ý" column (Phase 5,
plans/260705-1459-budget-cashflow-workable-loop/phase-05-prefill-suggestions.md).

Computes the "Gợi Ý" (suggestion) column for NEXT month only — never "Budget". Per item_type:
  recurring : rolling 3-completed-month avg of actual amount from fact_cash_movement,
              per (cashflow_line, direction)
  reserve   : if it has BOTH item_target and target_month (a deadline) -> required_monthly_adj
              straight from mart_cashflow_reserve_status (gap_remaining / months_until_target).
              If target-only / open-ended -> no suggestion, cell left untouched.
  one_off   : 0, except in the item's own target_month (finance enters that one manually).

This module is pure (no I/O, no credentials needed) — see duckdb_actuals.py for the DuckDB
reads that feed the *_map arguments below, and sheet_writeback.py for the credentialed
Sheets API write path.
"""
from collections import defaultdict
from datetime import datetime

import pandas as pd

from .fetch import _ICT
from .budget_transform import BI_COL_DATA_START

SUGGESTION_ROLLING_WINDOW_MONTHS = 3


def next_month_start(now: datetime | None = None) -> str:
    """Target month for the suggestion write-back: the calendar month after 'now'."""
    now = now or datetime.now(_ICT)
    year, month = now.year, now.month + 1
    if month > 12:
        month = 1
        year += 1
    return f"{year:04d}-{month:02d}-01"


def _preceding_months(period_month: str, n: int = SUGGESTION_ROLLING_WINDOW_MONTHS) -> list:
    """n calendar months immediately BEFORE period_month, oldest-first."""
    target = datetime.strptime(period_month, "%Y-%m-%d")
    out = []
    y, m = target.year, target.month
    for _ in range(n):
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        out.append(f"{y:04d}-{m:02d}-01")
    return list(reversed(out))


def compute_recurring_suggestions(actual_rows: list, window_size: int = SUGGESTION_ROLLING_WINDOW_MONTHS) -> dict:
    """Rolling N-month average of actual amount per (cashflow_line, direction).

    actual_rows: [{'cashflow_line':.., 'direction':.., 'amount':..}, ...] — one row per
    (cashflow_line, direction) already SUM(amount)-aggregated across the N-month window
    (caller is responsible for filtering to exactly that window).
    Divides by window_size (not the count of months actually present) so a line with
    movement in only 2 of N months still averages over N — missing months count as zero,
    which is what a true rolling average over a fixed window means.
    """
    totals = defaultdict(float)
    for r in actual_rows:
        totals[(r["cashflow_line"], r["direction"])] += float(r["amount"])
    return {k: v / window_size for k, v in totals.items()}


def compute_reserve_suggestions(reserve_rows: list) -> dict:
    """{cashflow_line: required_monthly_adj} from mart_cashflow_reserve_status rows.

    reserve_rows should already be pre-filtered by the caller to item_target IS NOT NULL
    AND target_month IS NOT NULL (has-a-deadline reserves only — open-ended reserves never
    get a suggestion). Rows where required_monthly_adj is None (deadline already passed /
    zero months remaining, mart returns NULL) are skipped — no suggestion, not zero.
    """
    out = {}
    for r in reserve_rows:
        if r.get("required_monthly_adj") is not None:
            out[r["cashflow_line"]] = float(r["required_monthly_adj"])
    return out


def _safe_parse_month(raw: str):
    """Best-effort month parse -> 'YYYY-MM-01', or None if blank/unparseable."""
    if not raw:
        return None
    try:
        return pd.to_datetime(raw).strftime("%Y-%m-01")
    except Exception:
        return None


def _assert_gio_column(col: int):
    """Defensive guard: col must be a 'Gợi Ý' column (even offset from BI_COL_DATA_START),
    NEVER the adjacent 'Budget' column. This is the hard requirement from the phase spec —
    this write-back path must NEVER touch Budget. Raises AssertionError (abort) if violated.
    """
    offset = col - BI_COL_DATA_START
    assert offset >= 0 and offset % 2 == 0, (
        f"Refusing to write: column index {col} is not a 'Gợi Ý' column (would hit Budget) "
        f"— aborting to protect finance-entered data"
    )


def build_suggestion_writes(items: list, months: list, target_month: str,
                             recurring_map: dict, reserve_map: dict) -> list:
    """Pure targeting logic — decides WHAT to write WHERE. No I/O, fully unit-testable.

    items: raw item dicts from parse_budget_matrix (caller must have already run
           validate_and_build_budget_rows and confirmed no errors — this function trusts
           item_type/direction_raw/cashflow_line are well-formed).
    months: [(gio_col, period_month), ...] from parse_budget_matrix — gio_col is always the
            "Gợi Ý" column of the pair (see module docstring: [Gợi Ý][Budget] per month).
    Returns [{"sheet_row", "col", "value", "cashflow_line", "item_type"}, ...] — one entry
    per cell that should actually be written. Skips (no entry emitted): no suggestion data
    available for a recurring line, open-ended/target-only reserves, and a one_off item's
    own target_month (finance enters that one by hand).
    """
    month_to_col = {pm: col for col, pm in months}
    target_col = month_to_col.get(target_month)
    if target_col is None:
        return []  # finance hasn't added the target month's columns yet — nothing to write

    _assert_gio_column(target_col)

    writes = []
    for it in items:
        item_type = it["item_type"]
        cashflow_line = it["cashflow_line"].strip()
        direction = "inflow" if it["direction_raw"] == "Thu" else "outflow"

        if item_type == "recurring":
            value = recurring_map.get((cashflow_line, direction))
            if value is None:
                continue
        elif item_type == "reserve":
            has_deadline = bool(it["item_target_raw"]) and bool(it["target_month_raw"])
            if not has_deadline:
                continue  # target-only / fully open-ended — never write a suggestion
            value = reserve_map.get(cashflow_line)
            if value is None:
                continue
        elif item_type == "one_off":
            item_target_month = _safe_parse_month(it["target_month_raw"])
            if item_target_month == target_month:
                continue  # its own due month — finance enters this manually
            value = 0
        else:
            continue  # unreachable post-validation — defensive only

        writes.append({
            "sheet_row": it["sheet_row"],
            "col": target_col,
            "value": value,
            "cashflow_line": cashflow_line,
            "item_type": item_type,
        })
    return writes

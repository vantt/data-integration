"""Compile the cards of a report spec (v2) into one SQL query each (engine-independent)."""
from __future__ import annotations

import re
from typing import Any

from .spec_validate import metric_refs
from .sql import AsOf, CompileError, Compiler, window

# spec comparison -> compiler window
COMPARISON_WINDOWS = {
    "prev_week_full": "prev_week_full",
    "prev_wtd_same_span": "prev_wtd_same_span",
    "prev_month": "prev_month_full",
}
PLACEHOLDER = re.compile(r"{{\s*([a-z_]+)\s*}}")


def comparison_window(card: dict[str, Any]) -> str | None:
    comp = card.get("comparison")
    if comp is None or comp == "target":
        return None
    if comp not in COMPARISON_WINDOWS:
        raise CompileError(f"card '{card['card_id']}': comparison '{comp}' is not supported by the compiler yet")
    return COMPARISON_WINDOWS[comp]


def compile_card(compiler: Compiler, card: dict[str, Any], as_of: AsOf) -> str | None:
    """SQL returning the card's result, or None for cards without data (text, meta)."""
    kind = card["kind"]
    if kind in ("text", "meta_period", "meta_freshness"):
        return None
    win = window(card["window"], as_of)
    if kind == "inline_sql":
        start, end = compiler.bounds(win)
        values = {"as_of": as_of.sql, "window_start": start, "window_end": end, "tz": compiler.tz}

        def sub(match: re.Match) -> str:
            name = match.group(1)
            if name not in values:
                raise CompileError(f"card '{card['card_id']}': unknown placeholder '{name}'")
            return values[name]

        return PLACEHOLDER.sub(sub, card["inline_sql"]["sql"]).rstrip("\n") + "\n"
    refs = metric_refs(card)
    cmp_name = comparison_window(card)
    if kind in ("kpi_compare", "derived"):
        cols = [f"  {compiler.total(mid, win, as_of)} AS {mid}" for mid in refs]
        if cmp_name:
            cmp = window(cmp_name, as_of)
            cols += [f"  {compiler.total(mid, cmp, as_of)} AS {mid}__cmp" for mid in refs]
        return "SELECT\n" + ",\n".join(cols) + "\n"
    if kind in ("trend", "breakdown", "table"):
        return compiler.grouped(refs, card.get("dimensions", []), card.get("grain"), win,
                                sort_metric=card.get("pct_change_of"), sort=card.get("sort"), limit=card.get("limit"))
    if kind == "breakdown_compare":
        if not cmp_name:
            raise CompileError(f"card '{card['card_id']}': breakdown_compare needs a comparison window")
        return compiler.grouped_compare(refs, card["dimensions"], win, window(cmp_name, as_of),
                                        pct_change_of=card.get("pct_change_of"), sort=card.get("sort"))
    raise CompileError(f"card '{card['card_id']}': unknown kind '{kind}'")


def compile_meta(compiler: Compiler, as_of: AsOf, freshness_model: str, freshness_filters: list[str],
                 coverage_metric: str | None) -> str:
    """One-row query for the report header and the meta cards: as_of, period bounds, freshness."""
    a = as_of.sql
    wtd, prev = window("wtd", as_of), window("prev_week_full", as_of)
    cols = [
        f"  {a} AS as_of",
        f"  {wtd.start} AS week_start",
        f"  {prev.start} AS prev_week_start",
        f"  ({prev.end} - 1) AS prev_week_end",
        f"  {window('mtd', as_of).start} AS month_start",
        f"  {compiler.last_event(freshness_model, freshness_filters, wtd)} AS last_event_at",
    ]
    if coverage_metric:
        last30 = window("last_30_days", as_of)
        cols.append(f"  {compiler.total(coverage_metric, last30, as_of)} AS cost_coverage_30d")
    return "SELECT\n" + ",\n".join(cols) + "\n"

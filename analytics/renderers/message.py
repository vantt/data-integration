"""Summary message of a report: its KPI tiles (catalog `kpi_tiles`) as text plus a link to the page.

Pure functions; the caller (orchestration/reports/summary_message.py) runs the SQL read-only and
sends the card. A tile that shows costs is dropped for a channel with `can_view_cost: false`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from ..compiler.cards import COMPARISON_WINDOWS, compile_card
from ..compiler.loader import Registry, load_spec, spec_file
from ..compiler.spec_validate import card_cost_sensitive, iter_cards, metric_refs
from ..compiler.sql import AsOf, Compiler

TILE_KINDS = {"kpi_compare", "derived"}
COMPARISON_LABEL = {"prev_week_full": "tuần trước", "prev_wtd_same_span": "cùng kỳ tuần trước", "prev_month": "tháng trước"}


@dataclass(frozen=True)
class Tile:
    card_id: str
    title: str
    metric: str
    unit: str
    decimals: int | None
    comparison: str | None
    sql: str


def report_entry(catalog: dict[str, Any], report_id: str) -> dict[str, Any]:
    for report in catalog["reports"]:
        if report["id"] == report_id:
            return report
    raise KeyError(f"report '{report_id}' is not in the catalog")


def summary_tiles(reg: Registry, profile: dict[str, Any], catalog: dict[str, Any], catalog_path: Path,
                  report_id: str, as_of: date, can_view_cost: bool) -> list[Tile]:
    report = report_entry(catalog, report_id)
    spec = load_spec(spec_file(catalog_path, report["spec"]))
    cards = {c["card_id"]: c for _, _, c in iter_cards(spec)}
    compiler = Compiler(reg, profile)
    a = AsOf.literal(as_of.isoformat())
    tiles = []
    for card_id in report["kpi_tiles"]:
        card = cards[card_id]
        if card["kind"] not in TILE_KINDS:
            raise ValueError(f"kpi_tile '{card_id}' is a {card['kind']} card; only single-value cards can be tiles")
        if card_cost_sensitive(reg, card) and not can_view_cost:
            continue
        metric = metric_refs(card)[0]
        comparison = card.get("comparison") if card.get("comparison") in COMPARISON_WINDOWS else None
        tiles.append(Tile(card_id, card["title"]["vi"], metric, reg.metrics[metric]["unit"], card.get("decimals"),
                          comparison, compile_card(compiler, card, a)))
    return tiles


def format_number(value: float | int | None, unit: str, decimals: int | None = None) -> str:
    """Vietnamese style: 1.234.567 and 12,3 %; '–' for a missing value."""
    if value is None:
        return "–"
    if decimals is None:
        decimals = {"currency": 0, "count": 0, "percent": 1, "ratio": 2, "index": 2}.get(unit, 0)
    text = f"{float(value):,.{decimals}f}".replace(",", "\0").replace(".", ",").replace("\0", ".")
    if unit == "currency":
        return text + " ₫"
    if unit == "percent":
        return text + " %"
    return text


def format_change(current: float | None, previous: float | None, unit: str) -> str | None:
    if current is None or previous is None:
        return None
    if unit == "percent":
        diff = float(current) - float(previous)
        return f"{'▲' if diff >= 0 else '▼'} {format_number(abs(diff), 'ratio', 1)} điểm %"
    if float(previous) == 0:
        return None
    pct = (float(current) - float(previous)) * 100.0 / abs(float(previous))
    return f"{'▲' if pct >= 0 else '▼'} {format_number(abs(pct), 'ratio', 1)} %"


def summary_card(report: dict[str, Any], tiles: list[Tile], rows: dict[str, dict[str, Any]], as_of: date,
                 link: str) -> tuple[str, dict[str, str]]:
    """(title, fields) for the Lark card; `rows` maps card_id to the single result row of its SQL."""
    fields: dict[str, str] = {}
    for tile in tiles:
        row = rows.get(tile.card_id) or {}
        text = format_number(row.get(tile.metric), tile.unit, tile.decimals)
        if tile.comparison:
            change = format_change(row.get(tile.metric), row.get(f"{tile.metric}__cmp"), tile.unit)
            if change:
                text += f" ({change} so với {COMPARISON_LABEL[tile.comparison]})"
        fields[tile.title] = text
    fields["Dữ liệu đến hết"] = as_of.strftime("%d/%m/%Y")
    fields["Xem báo cáo"] = f"[{report['title']}]({link})"
    return f"{report['title']} — {as_of.strftime('%d/%m/%Y')}", fields


def report_link(profile: dict[str, Any], report: dict[str, Any]) -> str:
    return f"{profile['access']['site_url'].rstrip('/')}/{report['area']}/{report['id']}/"

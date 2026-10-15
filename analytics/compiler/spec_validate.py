"""Checks of report specs (v2) and of the catalog against the registry and tenant profiles."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from .formula import FormulaError, parse
from .loader import Registry, RegistryError, load_spec, spec_file

DATA_KINDS = {"kpi_compare", "trend", "breakdown", "breakdown_compare", "derived", "table", "inline_sql"}
GROUPED_KINDS = {"trend", "breakdown", "breakdown_compare", "table"}
PLACEHOLDER = re.compile(r"{{\s*([a-z_]+)\s*}}")
ALLOWED_PLACEHOLDERS = {"as_of", "window_start", "window_end", "tz"}
INLINE_SQL_LIMIT = 0.30  # stop condition of the pilot: more than 30 % of data cards need inline SQL

Report = Callable[[str, str], None]


def metric_refs(card: dict[str, Any]) -> list[str]:
    ref = card.get("metric_ref")
    if ref is None:
        return []
    return [ref] if isinstance(ref, str) else list(ref)


def iter_cards(spec: dict[str, Any]):
    for tab in spec.get("tabs", []):
        for block in tab.get("blocks", []):
            for card in block.get("cards", []):
                yield tab, block, card


def simple_components(reg: Registry, metric_id: str, seen: frozenset[str] = frozenset()) -> list[dict[str, Any]]:
    """The simple/snapshot metrics a metric is built from."""
    if metric_id in seen or metric_id not in reg.metrics:
        return []
    metric = reg.metrics[metric_id]
    kind = metric["type"]
    if kind in ("simple", "snapshot"):
        return [metric]
    deps: list[str] = []
    if kind == "ratio":
        deps = [metric["numerator"], metric["denominator"]]
    elif kind == "derived":
        try:
            deps = list(parse(metric["expression"]).metrics)
        except FormulaError:
            return []
    out: list[dict[str, Any]] = []
    for dep in deps:
        out += simple_components(reg, dep, seen | {metric_id})
    return out


def card_cost_sensitive(reg: Registry, card: dict[str, Any]) -> bool:
    """A card shows cost, margin or profit: through a cost-sensitive metric or flagged inline SQL."""
    if card.get("kind") == "inline_sql":
        return bool(card["inline_sql"].get("cost_sensitive"))
    return any(reg.metrics.get(m, {}).get("cost_sensitive") for m in metric_refs(card))


def _axis(reg: Registry, metric: dict[str, Any]) -> str | None:
    model = reg.semantic.get(metric.get("model", ""), {})
    for t in model.get("time_dimensions", []):
        if t["name"] == metric.get("time_axis"):
            return t.get("axis")
    return None


def check_spec(reg: Registry, spec: dict[str, Any], where: str, profiles: dict[str, dict[str, Any]],
               error: Report, warn: Report) -> dict[str, Any]:
    """Validate one spec; returns facts the catalog check needs (metrics, card ids, cost flag)."""
    seen_cards: set[str] = set()
    for kind, key in (("tab", "tab_id"), ("block", "block_id")):
        ids = [t[key] for t in spec["tabs"]] if kind == "tab" else [b[key] for t in spec["tabs"] for b in t["blocks"]]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            error(where, f"duplicate {key}: {dup}")

    used_metrics: set[str] = set()
    data_cards = inline_cards = 0
    for tab, block, card in iter_cards(spec):
        cid = card["card_id"]
        here = f"{where}#{cid}"
        if cid in seen_cards:
            error(here, "card_id is not unique in the report")
        seen_cards.add(cid)
        kind = card["kind"]
        if kind in DATA_KINDS:
            data_cards += 1
        refs = metric_refs(card)
        used_metrics.update(refs)
        for mid in refs:
            if mid not in reg.metrics:
                error(here, f"metric_ref '{mid}' is not in the registry")
            elif reg.metrics[mid].get("status") != "active":
                error(here, f"metric_ref '{mid}' is {reg.metrics[mid].get('status')}, not active")
        known = [m for m in refs if m in reg.metrics]
        components = [c for m in known for c in simple_components(reg, m)]

        # time axis: every flow component must be on the axis the reader is told
        axis = card.get("time_axis") or block["time_axis"]
        for comp in components:
            if comp["type"] != "simple":
                continue
            comp_axis = _axis(reg, comp)
            if comp_axis != axis:
                error(here, f"metric '{comp['id']}' is on axis '{comp_axis}' but the card shows '{axis}' "
                            "(set the card's time_axis or move it to a block on that axis)")

        # grouped cards compile to one GROUP BY query over one model
        if kind in GROUPED_KINDS and known:
            for mid in known:
                if reg.metrics[mid]["type"] == "derived":
                    error(here, f"derived metric '{mid}' cannot be broken down or trended; use a KPI card")
            if len({c.get("time_axis") for c in components}) > 1:
                error(here, "grouped card mixes metrics on different time axes")
            models = {c["model"] for c in components}
            if any(c["type"] == "snapshot" for c in components):
                error(here, "a snapshot metric cannot be broken down or trended")
            if len(models) > 1:
                error(here, f"grouped card mixes metrics of several models {sorted(models)}; split the card")
            for dim in card.get("dimensions", []):
                dmodel, dname = dim.split(".", 1)
                model = reg.semantic.get(dmodel)
                if model is None or dname not in {d["name"] for d in model.get("dimensions", [])}:
                    error(here, f"dimension '{dim}' is not declared in the semantic layer")
                    continue
                for base in models:
                    base_model = reg.semantic.get(base, {})
                    if dmodel != base and dmodel not in {j["model"] for j in base_model.get("joins", [])}:
                        error(here, f"dimension '{dim}' is not reachable from model '{base}' in one join")

        if card.get("pct_change_of") and card["pct_change_of"] not in refs:
            error(here, f"pct_change_of '{card['pct_change_of']}' is not one of the card's metrics")
        if card.get("pct_change_of") and not card.get("comparison"):
            error(here, "pct_change_of needs a comparison")
        bands = [b["max"] for b in card.get("bands", [])]
        if bands != sorted(bands) or len(set(bands)) != len(bands):
            error(here, "bands must have strictly ascending max")

        params = []
        if card.get("goal"):
            params.append(card["goal"]["param"])
        if kind == "inline_sql":
            inline_cards += 1
            sql = card["inline_sql"]["sql"]
            bad = sorted(set(PLACEHOLDER.findall(sql)) - ALLOWED_PLACEHOLDERS)
            if bad:
                error(here, f"inline_sql uses unknown placeholders {bad} (allowed: {sorted(ALLOWED_PLACEHOLDERS)})")
            if "current_date" in sql.lower() or "now()" in sql.lower():
                error(here, "inline_sql must use {{as_of}} / {{window_start}} / {{window_end}}, not the clock")
            for out in card["inline_sql"]["outputs"]:
                if out.get("link"):
                    params.append(out["link"]["param"])
        for param in params:
            for pname, profile in profiles.items():
                if param not in (profile.get("tenant_params") or {}):
                    error(here, f"tenant param '{param}' is missing in profile '{pname}'")

    ratio = inline_cards / data_cards if data_cards else 0.0
    if ratio > INLINE_SQL_LIMIT:
        warn(where, f"{inline_cards}/{data_cards} data cards use inline_sql ({ratio:.0%} > {INLINE_SQL_LIMIT:.0%})")
    cost = any(reg.metrics[m].get("cost_sensitive") for m in used_metrics if m in reg.metrics)
    return {"metrics": used_metrics, "cards": seen_cards, "cost_sensitive": cost,
            "data_cards": data_cards, "inline_cards": inline_cards}


def check_catalog(reg: Registry, catalog: dict[str, Any], catalog_path: Path, rel: Callable[[Path], str],
                  profiles: dict[str, dict[str, Any]], schema_errors: Callable[[Any, str, str], bool],
                  error: Report, warn: Report) -> list[str]:
    """Validate the catalog and every spec it lists. Returns one summary line per report."""
    where_cat = rel(catalog_path)
    ids = [r["id"] for r in catalog["reports"]]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        error(where_cat, f"duplicate report id '{dup}'")
    summaries = []
    for report in catalog["reports"]:
        here = f"{where_cat}#{report['id']}"
        path = spec_file(catalog_path, report["spec"])
        if not path.exists():
            error(here, f"spec file {report['spec']} does not exist")
            continue
        try:
            spec = load_spec(path)
        except RegistryError as exc:
            error(here, str(exc))
            continue
        where = rel(path)
        if not schema_errors(spec, "report-spec", where):
            continue
        if spec["spec_id"] != report["id"]:
            error(here, f"spec_id '{spec['spec_id']}' differs from the catalog id")
        if report["primary_cell"] not in report["cell"]:
            error(here, "primary_cell must be one of cell")
        facts = check_spec(reg, spec, where, profiles, error, warn)
        if sorted(report["metrics"]) != sorted(facts["metrics"]):
            error(here, f"metrics must equal the union of metric_ref in the spec: {sorted(facts['metrics'])}")
        if report["cost_sensitive"] != facts["cost_sensitive"]:
            error(here, f"cost_sensitive must be {facts['cost_sensitive']} (derived from the metrics)")
        kinds = {c["card_id"]: c["kind"] for _, _, c in iter_cards(spec)}
        for tile in report["kpi_tiles"]:
            if tile not in facts["cards"]:
                error(here, f"kpi_tile '{tile}' is not a card_id of the spec")
            elif kinds[tile] not in ("kpi_compare", "derived"):
                error(here, f"kpi_tile '{tile}' is a {kinds[tile]} card; a tile must be a single-value card")
        for pname, profile in profiles.items():
            areas = {a["id"]: a for a in (profile.get("access") or {}).get("areas", [])}
            if not areas:
                continue
            area = areas.get(report["area"])
            if area is None:
                error(here, f"area '{report['area']}' is not declared in profile '{pname}' (access.areas)")
                continue
            if area.get("legacy"):
                error(here, f"area '{report['area']}' is the legacy area (hand-written pages only)")
            if not area["can_view_cost"]:
                for _, _, card in iter_cards(spec):
                    if card.get("required") and card_cost_sensitive(reg, card):
                        error(f"{where}#{card['card_id']}",
                              f"required card shows costs but area '{area['id']}' of profile '{pname}' cannot view costs")
        summaries.append(f"{report['id']}: {facts['inline_cards']}/{facts['data_cards']} data cards use inline_sql")
    for pname, profile in profiles.items():
        message = profile.get("message") or {}
        channels = {c["id"] for c in message.get("channels", [])}
        engines = {r["id"]: r["engine"] for r in catalog["reports"]}
        for entry in message.get("reports", []):
            if entry["report"] not in engines:
                error(pname, f"message.reports: '{entry['report']}' is not in the catalog")
            elif engines[entry["report"]] != "evidence":
                error(pname, f"message.reports: '{entry['report']}' is not built by the report site (engine evidence)")
            for ch in entry["channels"]:
                if ch not in channels:
                    error(pname, f"message.reports: channel '{ch}' is not declared in message.channels")
    return summaries

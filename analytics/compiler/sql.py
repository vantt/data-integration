"""Compile registry metrics into DuckDB SQL.

The compiler is deliberately small (analytics/README.md, "Giới hạn cứng"): one aggregate per simple
metric, ratios of totals, linear derived expressions, one many-to-one join step, one time axis.

Every date boundary is an SQL DATE expression derived from `as_of`; it is turned into a TIMESTAMPTZ
with `timezone(<tenant tz>, ...)`, so results do not depend on the DuckDB session time zone.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from .formula import Formula, parse, to_sql
from .loader import Registry, RegistryError

AGG_SQL = {
    "sum": "SUM({col})",
    "count": "COUNT({col})",
    "count_distinct": "COUNT(DISTINCT {col})",
    "min": "MIN({col})",
    "max": "MAX({col})",
}
COUNT_AGGS = {"count", "count_distinct"}
BASE_ALIAS = "m"
_LAST_N = re.compile(r"^last_([1-9][0-9]{0,2})_days$")
WINDOW_NAMES = (
    "wtd", "prev_week_full", "prev_wtd_same_span", "mtd", "mtd_before_as_of",
    "prev_week_start_to_date", "month_full", "prev_month_full",
)


class CompileError(ValueError):
    """The request cannot be compiled (unknown window, missing segment binding, limit exceeded)."""


@dataclass(frozen=True)
class AsOf:
    """Reference date: last day the data is considered complete for (a DATE-valued SQL expression)."""

    sql: str

    @classmethod
    def literal(cls, iso_date: str) -> "AsOf":
        try:
            parsed = date.fromisoformat(iso_date)
        except ValueError as exc:
            raise CompileError(f"as_of must be YYYY-MM-DD, got '{iso_date}'") from exc
        return cls(f"DATE '{parsed.isoformat()}'")

    @classmethod
    def runtime(cls, timezone: str) -> "AsOf":
        """Yesterday in the tenant's time zone, evaluated when the SQL runs (scheduled builds)."""
        return cls(f"(CAST(timezone('{_tz(timezone)}', now()) AS DATE) - 1)")


@dataclass(frozen=True)
class Window:
    name: str
    start: str  # DATE expression, inclusive
    end: str  # DATE expression, exclusive
    ref: str  # DATE expression a snapshot metric is evaluated at


def window(name: str, as_of: AsOf) -> Window:
    a = as_of.sql
    week = f"CAST(date_trunc('week', {a}) AS DATE)"
    month = f"CAST(date_trunc('month', {a}) AS DATE)"
    next_day = f"({a} + 1)"
    if name == "wtd":
        return Window(name, week, next_day, a)
    if name == "prev_week_full":
        return Window(name, f"({week} - 7)", week, f"({week} - 1)")
    if name == "prev_wtd_same_span":
        return Window(name, f"({week} - 7)", f"({a} - 6)", f"({a} - 7)")
    if name == "mtd":
        return Window(name, month, next_day, a)
    if name == "mtd_before_as_of":
        return Window(name, month, a, a)
    if name == "prev_week_start_to_date":
        return Window(name, f"({week} - 7)", next_day, a)
    if name == "month_full":
        return Window(name, month, f"CAST({month} + INTERVAL 1 MONTH AS DATE)", a)
    if name == "prev_month_full":
        return Window(name, f"CAST({month} - INTERVAL 1 MONTH AS DATE)", month, f"({month} - 1)")
    match = _LAST_N.match(name)
    if match:
        n = int(match.group(1))
        return Window(name, f"({a} - {n - 1})", next_day, a)
    raise CompileError(f"unknown window '{name}' (known: {', '.join(WINDOW_NAMES)}, last_<n>_days)")


def _tz(timezone: str) -> str:
    if not re.fullmatch(r"[A-Za-z]+(/[A-Za-z_]+)+", timezone or ""):
        raise CompileError(f"invalid time zone '{timezone}'")
    return timezone


def _literal(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"


class Compiler:
    def __init__(self, registry: Registry, profile: dict[str, Any]):
        self.reg = registry
        self.tz = _tz(profile.get("locale", {}).get("timezone", ""))
        self.segments: dict[str, dict[str, Any]] = profile.get("segments") or {}
        self._formulas: dict[str, Formula] = {}

    # ------------------------------------------------------------------ public API
    def total(self, metric_id: str, win: Window, as_of: AsOf) -> str:
        """Scalar SQL expression: the metric over the window."""
        metric = self.reg.metric(metric_id)
        kind = metric["type"]
        if kind in ("simple", "snapshot"):
            return self._scalar(metric, win)
        if kind == "ratio":
            num = self.total(metric["numerator"], win, as_of)
            den = self.total(metric["denominator"], win, as_of)
            scale = " * 100.0" if metric.get("scale") == 100 else ""
            if metric.get("on_zero_denominator") == "zero":
                return f"(CASE WHEN {den} = 0 THEN 0 ELSE {num}{scale} / {den} END)"
            return f"({num}{scale} / NULLIF({den}, 0))"
        if kind == "derived":
            return to_sql(
                self.formula(metric_id),
                metric_sql=lambda mid: self.total(mid, win, as_of),
                calendar_sql=lambda name: _calendar(name, as_of),
            )
        raise CompileError(f"metric '{metric_id}': unknown type '{kind}'")

    def kpi_query(self, metric_id: str, window_name: str, as_of: AsOf, compare: str | None = None) -> str:
        """SELECT returning one row: the metric (and the comparison window as <id>__cmp)."""
        cols = [f"  {self.total(metric_id, window(window_name, as_of), as_of)} AS {metric_id}"]
        if compare:
            cols.append(f"  {self.total(metric_id, window(compare, as_of), as_of)} AS {metric_id}__cmp")
        return "SELECT\n" + ",\n".join(cols) + "\n"

    # ------------------------------------------------------------------ grouped queries
    def _components(self, metric_id: str) -> list[dict[str, Any]]:
        metric = self.reg.metric(metric_id)
        if metric["type"] == "simple":
            return [metric]
        if metric["type"] == "ratio":
            return self._components(metric["numerator"]) + self._components(metric["denominator"])
        raise CompileError(f"metric '{metric_id}' ({metric['type']}) cannot be grouped; use a KPI card")

    def grouped(self, metric_ids: list[str], dimensions: list[str], grain: str | None, win: Window,
                sort_metric: str | None = None, sort: str | None = None, limit: int | None = None) -> str:
        """One GROUP BY query over one model: filters shared by every metric go to WHERE (so the groups
        are exactly those of a single-metric query); the rest become FILTER clauses."""
        comps = [c for mid in metric_ids for c in self._components(mid)]
        models = {c["model"] for c in comps}
        axes = {c["time_axis"] for c in comps}
        if len(models) != 1 or len(axes) != 1:
            raise CompileError(f"grouped metrics {metric_ids} must share one model and one time axis")
        model = self.reg.model(models.pop())
        axis = axes.pop()
        common = [f for f in comps[0].get("filters", []) if all(f in c.get("filters", []) for c in comps)]
        joins: list[str] = []
        where = self._time_predicate(model, axis, win, joins)
        where += [self._filter(model, f, win, joins) for f in common]

        keys: list[tuple[str, str]] = []  # (alias, expression)
        if grain:
            dim = _named(model.get("time_dimensions", []), axis, f"time dimension of model '{model['id']}'")
            col = self._column(model, dim, joins)
            if grain == "day":
                keys.append(("day", self._local_date(col)))
            elif grain in ("week", "month"):
                keys.append((grain, f"CAST(date_trunc('{grain}', {self._local_date(col)}) AS DATE)"))
            else:
                raise CompileError(f"unknown grain '{grain}'")
        for ref in dimensions:
            dmodel, dname = ref.split(".", 1)
            dim = _named(self.reg.model(dmodel).get("dimensions", []), dname, f"dimension of model '{dmodel}'")
            spec = dict(dim, via=None if dmodel == model["id"] else dmodel)
            keys.append((dname, self._column(model, spec, joins)))

        def agg(metric: dict[str, Any]) -> str:
            measure = _named(model.get("measures", []), metric["measure"], f"measure of model '{model['id']}'")
            sql = AGG_SQL[measure["agg"]].format(col=f"{BASE_ALIAS}.{measure['column']}")
            extra = [self._filter(model, f, win, joins) for f in metric.get("filters", []) if f not in common]
            if extra:
                sql += " FILTER (WHERE " + " AND ".join(extra) + ")"
                if metric.get("empty_result", "zero") == "zero" and measure["agg"] not in COUNT_AGGS:
                    sql = f"COALESCE({sql}, 0)"
            return sql

        def expr(metric_id: str) -> str:
            metric = self.reg.metric(metric_id)
            if metric["type"] == "simple":
                return agg(metric)
            num, den = expr(metric["numerator"]), expr(metric["denominator"])
            scale = " * 100.0" if metric.get("scale") == 100 else ""
            if metric.get("on_zero_denominator") == "zero":
                return f"CASE WHEN {den} = 0 THEN 0 ELSE {num}{scale} / {den} END"
            return f"{num}{scale} / NULLIF({den}, 0)"

        select = [f"  {e} AS {a}" for a, e in keys] + [f"  {expr(mid)} AS {mid}" for mid in metric_ids]
        lines = ["SELECT", ",\n".join(select), f"FROM {model['relation']} AS {BASE_ALIAS}"]
        lines += joins
        lines.append("WHERE " + "\n  AND ".join(where))
        if keys:
            lines.append("GROUP BY " + ", ".join(str(i + 1) for i in range(len(keys))))
        order = _order_by([a for a, _ in keys], sort, sort_metric or (metric_ids[0] if metric_ids else None))
        if order:
            lines.append(order)
        if limit:
            lines.append(f"LIMIT {int(limit)}")
        return "\n".join(lines) + "\n"

    def grouped_compare(self, metric_ids: list[str], dimensions: list[str], win: Window, cmp: Window,
                        pct_change_of: str | None = None, sort: str | None = None,
                        sort_metric: str | None = None) -> str:
        """Current vs comparison window per group (FULL OUTER JOIN, missing side counts as 0)."""
        names = [d.split(".", 1)[1] for d in dimensions]
        cur = self.grouped(metric_ids, dimensions, None, win)
        prev = self.grouped(metric_ids, dimensions, None, cmp)

        def side(alias: str, mid: str) -> str:
            if self.reg.metric(mid)["type"] == "simple" and self.reg.metric(mid).get("empty_result", "zero") == "zero":
                return f"COALESCE({alias}.{mid}, 0)"
            return f"{alias}.{mid}"

        cols = [f"  COALESCE(cur.{n}, cmp.{n}) AS {n}" for n in names]
        cols += [f"  {side('cur', mid)} AS {mid}" for mid in metric_ids]
        cols += [f"  {side('cmp', mid)} AS {mid}__cmp" for mid in metric_ids]
        if pct_change_of:
            p = pct_change_of
            cols.append(f"  CASE WHEN COALESCE(cmp.{p}, 0) = 0 THEN NULL "
                        f"ELSE ({side('cur', p)} - cmp.{p}) * 100.0 / cmp.{p} END AS {p}__pct_change")
        on = " AND ".join(f"cur.{n} = cmp.{n}" for n in names)
        sort_by = sort_metric or pct_change_of or metric_ids[0]
        lines = [
            "WITH cur AS (", _indent(cur), "),", "cmp AS (", _indent(prev), ")",
            "SELECT", ",\n".join(cols),
            f"FROM cur FULL OUTER JOIN cmp ON {on}",
        ]
        if sort in ("value_desc", "value_asc"):
            direction = "DESC" if sort == "value_desc" else "ASC"
            lines.append(f"ORDER BY {side('cur', sort_by)} {direction}, " + ", ".join(f"{i + 1}" for i in range(len(names))))
        elif names:
            lines.append("ORDER BY " + ", ".join(f"{i + 1}" for i in range(len(names))))
        return "\n".join(lines) + "\n"

    def last_event(self, model_id: str, filters: list[str], win: Window) -> str:
        """Scalar: latest value of the model's default time dimension (data freshness)."""
        model = self.reg.model(model_id)
        dim = next((t for t in model.get("time_dimensions", []) if t.get("default")), None)
        if dim is None:
            raise CompileError(f"model '{model_id}' has no default time dimension")
        joins: list[str] = []
        col = self._column(model, dim, joins)
        where = [self._filter(model, f, win, joins) for f in filters] or ["TRUE"]
        lines = [f"(SELECT MAX({col})", f"   FROM {model['relation']} AS {BASE_ALIAS}"]
        lines += [f"   {j}" for j in joins]
        lines.append("   WHERE " + "\n     AND ".join(where) + ")")
        return "\n".join(lines)

    def bounds(self, win: Window) -> tuple[str, str]:
        """TIMESTAMPTZ expressions of the window (for inline SQL placeholders)."""
        return self._bound(win.start), self._bound(win.end)

    def formula(self, metric_id: str) -> Formula:
        if metric_id not in self._formulas:
            self._formulas[metric_id] = parse(self.reg.metric(metric_id)["expression"])
        return self._formulas[metric_id]

    # ------------------------------------------------------------------ simple / snapshot
    def _scalar(self, metric: dict[str, Any], win: Window) -> str:
        model = self.reg.model(metric["model"])
        measure = _named(model.get("measures", []), metric["measure"], f"measure of model '{model['id']}'")
        if measure.get("aggregatable") is False:
            raise CompileError(f"metric '{metric['id']}': measure '{measure['name']}' is a per-row ratio and cannot be aggregated")
        joins: list[str] = []
        where: list[str] = []
        if metric["type"] == "simple":
            where += self._time_predicate(model, metric["time_axis"], win, joins)
        else:
            validity = model.get("validity")
            if not validity:
                raise CompileError(f"snapshot metric '{metric['id']}': model '{model['id']}' has no validity")
            where.append(f"{BASE_ALIAS}.{validity['from']} <= {win.ref}")
            where.append(f"{BASE_ALIAS}.{validity['to']} >= {win.ref}")
        for name in metric.get("filters", []):
            where.append(self._filter(model, name, win, joins))
        agg = AGG_SQL[measure["agg"]].format(col=f"{BASE_ALIAS}.{measure['column']}")
        if metric.get("zero_as_missing"):
            value = f"NULLIF({agg}, 0)"
        elif metric.get("empty_result", "zero") == "zero" and measure["agg"] not in COUNT_AGGS:
            value = f"COALESCE({agg}, 0)"
        else:
            value = agg
        lines = [f"(SELECT {value}", f"   FROM {model['relation']} AS {BASE_ALIAS}"]
        lines += [f"   {j}" for j in joins]
        lines.append("   WHERE " + "\n     AND ".join(where) + ")")
        return "\n".join(lines)

    def _join(self, model: dict[str, Any], target_id: str, joins: list[str]) -> str:
        """Add the LEFT JOIN to `target_id` (one many-to-one step) and return its alias."""
        alias = f"j_{target_id}"
        spec = next((j for j in model.get("joins", []) if j["model"] == target_id), None)
        if spec is None:
            raise CompileError(f"model '{model['id']}' declares no join to '{target_id}'")
        other = self.reg.model(target_id)
        clause = f"LEFT JOIN {other['relation']} AS {alias} ON {BASE_ALIAS}.{spec['from']} = {alias}.{spec['to']}"
        if clause not in joins:
            joins.append(clause)
        return alias

    def _column(self, model: dict[str, Any], spec: dict[str, Any], joins: list[str]) -> str:
        if spec.get("via"):
            return f"{self._join(model, spec['via'], joins)}.{spec['column']}"
        return f"{BASE_ALIAS}.{spec['column']}"

    def _local_date(self, col: str) -> str:
        return f"CAST(timezone('{self.tz}', {col}) AS DATE)"

    def _bound(self, date_sql: str) -> str:
        return f"timezone('{self.tz}', CAST({date_sql} AS TIMESTAMP))"

    def _time_predicate(self, model: dict[str, Any], axis: str, win: Window, joins: list[str]) -> list[str]:
        dim = _named(model.get("time_dimensions", []), axis, f"time dimension of model '{model['id']}'")
        col = self._column(model, dim, joins)
        if dim["type"] == "date":
            return [f"{col} >= {win.start}", f"{col} < {win.end}"]
        return [f"{col} >= {self._bound(win.start)}", f"{col} < {self._bound(win.end)}"]

    def _filter(self, model: dict[str, Any], name: str, win: Window, joins: list[str]) -> str:
        gate = (model.get("gates") or {}).get(name)
        if gate is None:
            binding = (self.segments.get(name) or {}).get(model["id"])
            if binding is None:
                raise CompileError(
                    f"filter '{name}' is neither a gate of model '{model['id']}' nor bound for it in the tenant profile (segments.{name}.{model['id']})"
                )
            gate = binding
        col = self._column(model, gate, joins)
        op = gate["op"]
        if op == "is_true":
            return col
        if op == "is_false":
            return f"NOT {col}"
        if op == "eq":
            return f"{col} = {_literal(gate['value'])}"
        if op in ("in", "not_in"):
            values = ", ".join(_literal(v) for v in gate["values"])
            return f"{col} {'NOT IN' if op == 'not_in' else 'IN'} ({values})"
        if op == "before_window_start":
            return f"{self._local_date(col)} < {win.start}"
        if op in ("same_date_as", "date_distinct_from"):
            other = _named(model.get("time_dimensions", []), gate["other"], f"time dimension of model '{model['id']}'")
            other_col = self._column(model, other, joins)
            cmp = "=" if op == "same_date_as" else "IS DISTINCT FROM"
            return f"{self._local_date(col)} {cmp} {self._local_date(other_col)}"
        raise CompileError(f"gate '{name}': unknown op '{op}'")


def _calendar(name: str, as_of: AsOf) -> str:
    a = as_of.sql
    if name == "day_of_month":
        return f"EXTRACT(DAY FROM {a})"
    if name == "days_in_month":
        return f"EXTRACT(DAY FROM last_day({a}))"
    if name == "days_left_in_month":
        return f"GREATEST(EXTRACT(DAY FROM last_day({a})) - EXTRACT(DAY FROM {a}), 1)"
    raise CompileError(f"unknown calendar quantity '{name}'")


def _indent(sql: str, pad: str = "  ") -> str:
    return "\n".join(pad + line if line else line for line in sql.rstrip("\n").split("\n"))


def _order_by(keys: list[str], sort: str | None, sort_metric: str | None) -> str:
    if sort in ("value_desc", "value_asc") and sort_metric:
        direction = "DESC" if sort == "value_desc" else "ASC"
        tie = (", " + ", ".join(str(i + 1) for i in range(len(keys)))) if keys else ""
        return f"ORDER BY {sort_metric} {direction}{tie}"
    if sort in ("time_asc", "dimension_asc") and keys:
        return "ORDER BY " + ", ".join(str(i + 1) for i in range(len(keys)))
    if sort == "time_desc" and keys:
        return "ORDER BY 1 DESC"
    return ""


def _named(items: list[dict[str, Any]], name: str, what: str) -> dict[str, Any]:
    for item in items:
        if item.get("name") == name:
            return item
    raise CompileError(f"unknown {what}: '{name}'")


def compile_kpi(registry: Registry, profile: dict[str, Any], metric_id: str, window_name: str,
                as_of: AsOf, compare: str | None = None) -> str:
    try:
        return Compiler(registry, profile).kpi_query(metric_id, window_name, as_of, compare)
    except RegistryError as exc:
        raise CompileError(str(exc)) from exc

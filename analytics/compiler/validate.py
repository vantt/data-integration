"""Validator of the metric registry and tenant profiles.

  python3 scripts/checks/check_analytics_registry.py [--manifest <manifest.json>]
  python3 -m analytics validate [...]

Exit 1 when any ERROR is found. Report specs and the catalog are checked too (spec_validate.py).
Registry checks: JSON Schema; references between models, metrics and
profiles; compiler limits (aggregatable measures, one join step, linear derived expressions);
`legacy_names` never equal to an active id; cost flags consistent with cost columns, and every
cost-sensitive metric declares a coverage metric; columns declared in the dbt manifest (WARN when a
column has no docs); generated docs up to date; every metric compiles for every profile.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .formula import FormulaError, parse
from .loader import (
    CATALOG_FILE, REGISTRY_DIR, REPO_ROOT, Registry, RegistryError, discover_profiles, load_catalog,
    load_profile, load_registry, load_schema,
)
from .spec_validate import check_catalog
from .sql import AsOf, CompileError, Compiler, window

# Columns that carry cost, margin or profit. A measure on one of them must be `cost: true`, and a
# metric built on such a measure must be `cost_sensitive: true` (it is hidden from areas that may
# not see costs).
COST_COLUMNS = frozenset({
    "cogs_amount", "gross_profit", "gross_margin_pct", "channel_net_profit", "channel_net_margin_pct",
    "fully_loaded_net_profit", "fully_loaded_net_margin_pct", "cm1", "cm2", "cm3",
    "contribution_margin_1", "contribution_margin_2", "contribution_margin_3",
})
DEFAULT_MANIFEST = REPO_ROOT / "transformation" / "target" / "manifest.json"
DEFAULT_DOCS_DIR = REPO_ROOT / "docs" / "analytics-handbook" / "semantic"


@dataclass(frozen=True, order=True)
class Issue:
    level: str  # ERROR | WARN | INFO
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.level} {self.where}: {self.message}"


class _Collector:
    def __init__(self) -> None:
        self.issues: list[Issue] = []

    def error(self, where: str, message: str) -> None:
        self.issues.append(Issue("ERROR", where, message))

    def warn(self, where: str, message: str) -> None:
        self.issues.append(Issue("WARN", where, message))

    def info(self, where: str, message: str) -> None:
        self.issues.append(Issue("INFO", where, message))


# ---------------------------------------------------------------------- schema
def _schema_errors(doc: Any, schema_name: str, where: str, out: _Collector) -> bool:
    validator = Draft202012Validator(load_schema(schema_name))
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    for err in errors:
        path = "/".join(str(p) for p in err.absolute_path) or "(root)"
        out.error(where, f"schema: {path}: {err.message}")
    return not errors


# ---------------------------------------------------------------------- semantic models
def _check_semantic(reg: Registry, out: _Collector) -> None:
    for mid, model in reg.semantic.items():
        where = reg.sources[mid]
        joins = {j["model"]: j for j in model.get("joins", [])}
        for target_id in joins:
            if target_id not in reg.semantic:
                out.error(where, f"join to unknown model '{target_id}'")
        time_names = {t["name"] for t in model.get("time_dimensions", [])}

        def check_via(spec: dict[str, Any], what: str) -> None:
            via = spec.get("via")
            if via and via not in joins:
                out.error(where, f"{what} reads '{via}.{spec['column']}' but '{mid}' has no direct join to '{via}' "
                                 "(only one many-to-one step is allowed)")

        for t in model.get("time_dimensions", []):
            check_via(t, f"time dimension '{t['name']}'")
        defaults = [t["name"] for t in model.get("time_dimensions", []) if t.get("default")]
        if len(defaults) > 1:
            out.error(where, f"more than one default time dimension: {defaults}")
        for name, gate in (model.get("gates") or {}).items():
            check_via(gate, f"gate '{name}'")
            if gate.get("other") and gate["other"] not in time_names:
                out.error(where, f"gate '{name}': '{gate['other']}' is not a time dimension of '{mid}'")
        for measure in model.get("measures", []):
            is_cost_column = measure["column"] in COST_COLUMNS
            if is_cost_column and not measure.get("cost"):
                out.error(where, f"measure '{measure['name']}' reads cost column '{measure['column']}' and must be cost: true")
            if measure.get("cost") and not is_cost_column:
                out.error(where, f"measure '{measure['name']}' is cost: true but '{measure['column']}' is not a known cost column")
        names = [m["name"] for m in model.get("measures", [])]
        if len(names) != len(set(names)):
            out.error(where, "duplicate measure names")


# ---------------------------------------------------------------------- metrics
def _measure(reg: Registry, metric: dict[str, Any]) -> dict[str, Any] | None:
    model = reg.semantic.get(metric.get("model", ""))
    if not model:
        return None
    return next((m for m in model.get("measures", []) if m["name"] == metric.get("measure")), None)


def _dependencies(reg: Registry, metric: dict[str, Any]) -> list[str]:
    kind = metric.get("type")
    if kind == "ratio":
        return [metric["numerator"], metric["denominator"]]
    if kind == "derived":
        try:
            return list(parse(metric["expression"]).metrics)
        except FormulaError:
            return []
    return []


def _uses_cost(reg: Registry, metric_id: str, seen: frozenset[str] = frozenset()) -> bool:
    if metric_id in seen or metric_id not in reg.metrics:
        return False
    metric = reg.metrics[metric_id]
    if metric["type"] in ("simple", "snapshot"):
        measure = _measure(reg, metric)
        return bool(measure and measure.get("cost"))
    return any(_uses_cost(reg, dep, seen | {metric_id}) for dep in _dependencies(reg, metric))


def _find_cycle(reg: Registry) -> list[str] | None:
    state: dict[str, int] = {}

    def visit(mid: str, path: list[str]) -> list[str] | None:
        if state.get(mid) == 1:
            return path[path.index(mid):] + [mid]
        if state.get(mid) == 2 or mid not in reg.metrics:
            return None
        state[mid] = 1
        for dep in _dependencies(reg, reg.metrics[mid]):
            found = visit(dep, path + [mid])
            if found:
                return found
        state[mid] = 2
        return None

    for mid in sorted(reg.metrics):
        cycle = visit(mid, [])
        if cycle:
            return cycle
    return None


def _check_metrics(reg: Registry, profiles: dict[str, dict[str, Any]], out: _Collector) -> None:
    active_ids = {mid for mid, m in reg.metrics.items() if m.get("status") == "active"}
    legacy_owner: dict[str, str] = {}
    for mid, metric in reg.metrics.items():
        where = f"{reg.sources['metric:' + mid]}#{mid}"
        kind = metric["type"]
        if kind in ("simple", "snapshot"):
            model = reg.semantic.get(metric["model"])
            if model is None:
                out.error(where, f"unknown model '{metric['model']}'")
                continue
            measure = _measure(reg, metric)
            if measure is None:
                out.error(where, f"model '{model['id']}' has no measure '{metric['measure']}'")
            elif measure.get("aggregatable") is False:
                out.error(where, f"measure '{measure['name']}' is a per-row ratio (aggregatable: false); "
                                 "use a ratio of totals instead")
            if kind == "simple":
                if metric["time_axis"] not in {t["name"] for t in model.get("time_dimensions", [])}:
                    out.error(where, f"time_axis '{metric['time_axis']}' is not a time dimension of '{model['id']}'")
            elif not model.get("validity"):
                out.error(where, f"snapshot metric needs a model with validity; '{model['id']}' has none")
            gates = model.get("gates") or {}
            for name in metric.get("filters", []):
                if name in gates:
                    continue
                for pname, profile in profiles.items():
                    if model["id"] not in ((profile.get("segments") or {}).get(name) or {}):
                        out.error(where, f"filter '{name}' is not a gate of '{model['id']}' and profile "
                                         f"'{pname}' does not bind segments.{name}.{model['id']}")
        else:
            if kind == "derived":
                try:
                    parse(metric["expression"])
                except FormulaError as exc:
                    out.error(where, f"expression: {exc}")
            for dep in _dependencies(reg, metric):
                if dep not in reg.metrics:
                    out.error(where, f"references unknown metric '{dep}'")
                elif reg.metrics[dep].get("status") == "deprecated":
                    out.warn(where, f"references deprecated metric '{dep}'")

        cost = _uses_cost(reg, mid)
        if cost != bool(metric.get("cost_sensitive")):
            out.error(where, f"cost_sensitive is {metric.get('cost_sensitive')} but the metric "
                             f"{'uses' if cost else 'does not use'} a cost measure")
        if metric.get("cost_sensitive"):
            cov = metric.get("coverage_metric")
            if not cov:
                out.error(where, "cost-sensitive metric must declare coverage_metric (share of orders with a known cost)")
            elif cov not in reg.metrics:
                out.error(where, f"coverage_metric '{cov}' is not a metric")
        elif metric.get("coverage_metric") and metric["coverage_metric"] not in reg.metrics:
            out.error(where, f"coverage_metric '{metric['coverage_metric']}' is not a metric")
        if metric.get("replaced_by") and metric["replaced_by"] not in reg.metrics:
            out.error(where, f"replaced_by '{metric['replaced_by']}' is not a metric")
        for legacy in metric.get("legacy_names", []):
            if legacy in active_ids:
                out.error(where, f"legacy name '{legacy}' is the id of an active metric")
            if legacy in legacy_owner:
                out.error(where, f"legacy name '{legacy}' is also claimed by '{legacy_owner[legacy]}'")
            legacy_owner[legacy] = mid

    cycle = _find_cycle(reg)
    if cycle:
        out.error("registry", f"metric dependency cycle: {' -> '.join(cycle)}")


# ---------------------------------------------------------------------- manifest
def _manifest_columns(manifest: dict[str, Any]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for node in (manifest.get("nodes") or {}).values():
        if node.get("resource_type") == "model":
            out[node["name"]] = set((node.get("columns") or {}).keys())
    return out


def _check_manifest(reg: Registry, manifest: dict[str, Any], out: _Collector) -> None:
    columns = _manifest_columns(manifest)
    for mid, model in reg.semantic.items():
        where = reg.sources[mid]
        if model["model"] not in columns:
            out.error(where, f"dbt model '{model['model']}' is not in the manifest (renamed or disabled?)")
            continue
        if model["relation"].split(".")[-1] != model["model"]:
            out.warn(where, f"relation '{model['relation']}' does not end with the model name '{model['model']}'")
        used: dict[str, set[str]] = {}

        def use(spec_model: str, col: str) -> None:
            used.setdefault(spec_model, set()).add(col)

        for col in model.get("grain", []):
            use(mid, col)
        for item in model.get("time_dimensions", []) + model.get("dimensions", []):
            use(item.get("via") or mid, item["column"])
        for gate in (model.get("gates") or {}).values():
            use(gate.get("via") or mid, gate["column"])
        for m in model.get("measures", []):
            use(mid, m["column"])
        for j in model.get("joins", []):
            use(mid, j["from"])
            use(j["model"], j["to"])
        if model.get("validity"):
            use(mid, model["validity"]["from"])
            use(mid, model["validity"]["to"])
        for owner, cols in sorted(used.items()):
            owner_model = reg.semantic.get(owner)
            if not owner_model or owner_model["model"] not in columns:
                continue
            documented = columns[owner_model["model"]]
            for col in sorted(cols - documented):
                out.warn(where, f"column '{owner_model['model']}.{col}' has no dbt docs (not in the manifest); "
                                "this becomes an error once the mart has an enforced contract")


# ---------------------------------------------------------------------- profiles and compile smoke test
def _check_compile(reg: Registry, profiles: dict[str, dict[str, Any]], out: _Collector) -> None:
    as_of = AsOf.literal("2026-01-15")
    for pname, profile in profiles.items():
        try:
            compiler = Compiler(reg, profile)
        except CompileError as exc:
            out.error(pname, str(exc))
            continue
        for mid in sorted(reg.metrics):
            try:
                compiler.total(mid, window("wtd", as_of), as_of)
            except (CompileError, RegistryError, FormulaError) as exc:
                out.error(f"{reg.sources['metric:' + mid]}#{mid}", f"does not compile with profile '{pname}': {exc}")


def _check_docs(reg: Registry, docs_dir: Path, out: _Collector) -> None:
    from ..renderers.docs import render_all

    for name, content in render_all(reg).items():
        path = docs_dir / name
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            out.error(str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
                      "generated file is out of date: run `python3 -m analytics docs`")


# ---------------------------------------------------------------------- entry points
def validate(registry_dir: Path | None = None, profile_paths: Iterable[Path] | None = None,
             manifest_path: Path | None = None, docs_dir: Path | None = None,
             catalog_path: Path | None = None) -> list[Issue]:
    out = _Collector()
    try:
        reg = load_registry(registry_dir)
    except RegistryError as exc:
        return [Issue("ERROR", "registry", str(exc))]

    schema_ok = True
    for where, kind, doc in reg.documents:
        schema_ok &= _schema_errors(doc, "semantic-model" if kind == "semantic" else "metric", where, out)

    profiles: dict[str, dict[str, Any]] = {}
    for path in (list(profile_paths) if profile_paths is not None else discover_profiles()):
        try:
            doc = load_profile(path)
        except RegistryError as exc:
            out.error(str(path), str(exc))
            continue
        where = str(path.resolve().relative_to(REPO_ROOT)) if path.resolve().is_relative_to(REPO_ROOT) else str(path)
        if _schema_errors(doc, "tenant-profile", where, out):
            profiles[where] = doc
        else:
            schema_ok = False
    if not profiles:
        out.error("profiles", "no valid tenant profile (tenants/<t>/analytics/profile.yml)")

    if not schema_ok:
        # Reference checks on documents that fail the schema only produce noise.
        return sorted(set(out.issues))

    _check_semantic(reg, out)
    _check_metrics(reg, profiles, out)
    if manifest_path is not None:
        try:
            with open(manifest_path, encoding="utf-8") as fh:
                manifest = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            out.error(str(manifest_path), f"cannot read dbt manifest ({exc})")
        else:
            _check_manifest(reg, manifest, out)
    if not [i for i in out.issues if i.level == "ERROR"]:
        _check_compile(reg, profiles, out)
        if docs_dir is not None:
            _check_docs(reg, docs_dir, out)
    if catalog_path is not None:
        _check_catalog(reg, Path(catalog_path), profiles, out)
    return sorted(set(out.issues))


def _rel(path: Path) -> str:
    path = Path(path).resolve()
    return str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)


def _check_catalog(reg: Registry, catalog_path: Path, profiles: dict[str, dict[str, Any]], out: _Collector) -> None:
    try:
        catalog = load_catalog(catalog_path)
    except RegistryError as exc:
        out.error(_rel(catalog_path), str(exc))
        return
    if not _schema_errors(catalog, "catalog", _rel(catalog_path), out):
        return
    summaries = check_catalog(reg, catalog, catalog_path, _rel, profiles,
                              lambda doc, schema, where: _schema_errors(doc, schema, where, out),
                              out.error, out.warn)
    for line in summaries:
        out.info(_rel(catalog_path), line)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="check_analytics_registry", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--registry", type=Path, default=REGISTRY_DIR, help="registry root (default: analytics/registry)")
    p.add_argument("--profile", type=Path, action="append",
                   help="tenant profile (repeatable; default: every tenants/<t>/analytics/profile.yml)")
    p.add_argument("--manifest", type=Path, default=None,
                   help="dbt manifest.json for the column check (default: transformation/target/manifest.json if present)")
    p.add_argument("--catalog", type=Path, default=None,
                   help="report catalog to check with its specs (default: analytics/catalog/catalog.yml, only for the default registry)")
    p.add_argument("--docs-dir", type=Path, default=None,
                   help="directory of the generated docs to check (default: the handbook, only for the default registry)")
    args = p.parse_args(argv)

    manifest = args.manifest
    if manifest is None and DEFAULT_MANIFEST.exists():
        manifest = DEFAULT_MANIFEST
    docs_dir = args.docs_dir
    default_registry = args.registry.resolve() == REGISTRY_DIR.resolve()
    if docs_dir is None and default_registry:
        docs_dir = DEFAULT_DOCS_DIR
    catalog = args.catalog
    if catalog is None and default_registry:
        catalog = CATALOG_FILE

    issues = validate(args.registry, args.profile, manifest, docs_dir, catalog)
    if manifest is None:
        issues.append(Issue("WARN", "manifest", "no dbt manifest: column check skipped (run `dbt parse` or scripts/checks/run-all.sh)"))
    for issue in issues:
        print(issue)
    errors = sum(1 for i in issues if i.level == "ERROR")
    warns = sum(1 for i in issues if i.level == "WARN")
    try:
        reg = load_registry(args.registry)
        counts = f"{len(reg.semantic)} semantic models, {len(reg.metrics)} metrics"
    except RegistryError:
        counts = "registry not loaded"
    print(f"analytics registry: {counts}; {errors} error(s), {warns} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

"""The validator accepts the real registry and rejects each broken fixture."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from analytics.compiler import validate as v
from analytics.compiler.loader import REGISTRY_DIR, discover_profiles

PROFILE = discover_profiles()[0]


@pytest.fixture()
def registry(tmp_path: Path) -> Path:
    root = tmp_path / "registry"
    shutil.copytree(REGISTRY_DIR, root)
    return root


def _edit(path: Path, fn) -> None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _metric(doc, metric_id):
    return next(m for m in doc["metrics"] if m["id"] == metric_id)


def _errors(root: Path, **kw) -> list[str]:
    return [i.message for i in v.validate(root, [PROFILE], **kw) if i.level == "ERROR"]


def test_real_registry_is_clean():
    issues = v.validate(None, None, None, v.DEFAULT_DOCS_DIR)
    assert not [i for i in issues if i.level == "ERROR"], issues


def test_copy_of_registry_is_clean(registry):
    assert _errors(registry) == []


def test_missing_required_field(registry):
    _edit(registry / "metrics" / "sales.yml", lambda d: _metric(d, "net_sales").pop("cost_sensitive"))
    assert any("cost_sensitive" in e for e in _errors(registry))


def test_per_row_ratio_cannot_be_a_measure(registry):
    def add(doc):
        doc["metrics"].append({
            "id": "avg_gross_margin", "version": 1, "label": {"vi": "x", "en": "x"}, "description": "x",
            "type": "simple", "model": "order_economics", "measure": "gross_margin_pct_row",
            "filters": ["has_cogs"], "time_axis": "ordered_at", "additivity": "non_additive",
            "null_policy": "propagate", "cost_sensitive": True, "coverage_metric": "cogs_coverage_pct",
            "unit": "percent", "status": "active",
        })
    _edit(registry / "metrics" / "finance.yml", add)
    assert any("aggregatable: false" in e for e in _errors(registry))


def test_two_step_join_is_rejected(registry):
    # order_economics joins orders, orders joins customers: economics -> customers is two steps
    def add(doc):
        doc["gates"]["customer_known"] = {"column": "first_order_date", "via": "customers", "op": "before_window_start"}
    _edit(registry / "semantic" / "order_economics.yml", add)
    assert any("only one many-to-one step" in e for e in _errors(registry))


def test_legacy_name_equal_to_active_id(registry):
    _edit(registry / "metrics" / "sales.yml",
          lambda d: _metric(d, "gross_revenue").__setitem__("legacy_names", ["net_sales"]))
    assert any("legacy name 'net_sales'" in e for e in _errors(registry))


def test_cost_sensitive_needs_coverage(registry):
    _edit(registry / "metrics" / "finance.yml", lambda d: _metric(d, "gross_profit").pop("coverage_metric"))
    assert any("coverage_metric" in e for e in _errors(registry))


def test_cost_flag_must_match_measures(registry):
    _edit(registry / "metrics" / "finance.yml",
          lambda d: _metric(d, "gross_margin_pct").__setitem__("cost_sensitive", False))
    assert any("uses a cost measure" in e for e in _errors(registry))


def test_cost_column_measure_must_be_flagged(registry):
    def unflag(doc):
        next(m for m in doc["measures"] if m["name"] == "cogs_amount")["cost"] = False
    _edit(registry / "semantic" / "order_economics.yml", unflag)
    assert any("must be cost: true" in e for e in _errors(registry))


def test_non_linear_derived_is_rejected(registry):
    _edit(registry / "metrics" / "sales.yml",
          lambda d: _metric(d, "gmv_month_end_forecast").__setitem__("expression", "gross_revenue * net_sales"))
    assert any("multiply" in e for e in _errors(registry))


def test_unbound_segment_is_rejected(registry, tmp_path):
    profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
    del profile["segments"]["in_sales_scope"]["order_returns"]
    path = tmp_path / "profile.yml"
    path.write_text(yaml.safe_dump(profile, allow_unicode=True), encoding="utf-8")
    issues = [i.message for i in v.validate(registry, [path]) if i.level == "ERROR"]
    assert any("segments.in_sales_scope.order_returns" in e for e in issues)


def test_dependency_cycle(registry):
    _edit(registry / "metrics" / "sales.yml",
          lambda d: _metric(d, "aov").__setitem__("denominator", "aov"))
    assert any("cycle" in e for e in _errors(registry))


def test_manifest_columns(registry, tmp_path):
    manifest = {"nodes": {
        "model.p.fact_orders": {"resource_type": "model", "name": "fact_orders",
                                "columns": {"order_id": {}, "net_revenue": {}}},
    }}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    issues = v.validate(registry, [PROFILE], manifest_path=path)
    errors = [i.message for i in issues if i.level == "ERROR"]
    warns = [i.message for i in issues if i.level == "WARN"]
    assert any("'fact_order_returns' is not in the manifest" in e for e in errors)
    assert any("fact_orders.gross_revenue" in w for w in warns)
    assert not any("fact_orders.net_revenue" in w for w in warns)


def test_stale_generated_docs(registry, tmp_path):
    assert any("out of date" in e for e in _errors(registry, docs_dir=tmp_path))


def test_cli_exit_codes(registry):
    assert v.main(["--registry", str(registry), "--profile", str(PROFILE)]) == 0
    _edit(registry / "metrics" / "sales.yml", lambda d: _metric(d, "net_sales").pop("unit"))
    assert v.main(["--registry", str(registry), "--profile", str(PROFILE)]) == 1

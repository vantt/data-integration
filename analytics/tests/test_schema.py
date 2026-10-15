"""The real registry and profiles satisfy the JSON Schemas; malformed documents do not."""
from __future__ import annotations

import copy

import pytest
from jsonschema import Draft202012Validator

from analytics.compiler.loader import discover_profiles, load_profile, load_registry, load_schema


def _errors(doc, schema_name):
    return list(Draft202012Validator(load_schema(schema_name)).iter_errors(doc))


@pytest.mark.parametrize("name", ["semantic-model", "metric", "tenant-profile"])
def test_schemas_are_valid_2020_12(name):
    Draft202012Validator.check_schema(load_schema(name))


def test_registry_documents_match_schema():
    reg = load_registry()
    assert reg.semantic and reg.metrics
    for where, kind, doc in reg.documents:
        errors = _errors(doc, "semantic-model" if kind == "semantic" else "metric")
        assert not errors, f"{where}: {[e.message for e in errors]}"


def test_profiles_match_schema():
    paths = discover_profiles()
    assert paths, "at least one tenant profile"
    for path in paths:
        assert not _errors(load_profile(path), "tenant-profile"), path


def _metric(metric_id):
    return copy.deepcopy(load_registry().metric(metric_id))


def test_metric_missing_required_field_fails():
    bad = _metric("net_sales")
    del bad["null_policy"]
    assert _errors({"metrics": [bad]}, "metric")


def test_average_aggregation_is_not_allowed():
    model = copy.deepcopy(load_registry().model("order_economics"))
    model["measures"].append({"name": "avg_margin", "column": "gross_margin_pct", "agg": "avg", "cost": True})
    assert _errors(model, "semantic-model")


def test_ratio_cannot_carry_a_measure():
    bad = _metric("aov")
    bad["measure"] = "net_revenue"
    assert _errors({"metrics": [bad]}, "metric")


def test_null_policy_only_propagates():
    bad = _metric("net_sales")
    bad["null_policy"] = "zero"
    assert _errors({"metrics": [bad]}, "metric")


def test_deprecated_metric_needs_replacement():
    bad = _metric("orders_count")
    bad["status"] = "deprecated"
    assert _errors({"metrics": [bad]}, "metric")


def test_profile_revenue_parameters_are_explicit():
    profile = load_profile(discover_profiles()[0])
    for key in ("recognition_date", "vat", "returns", "excluded_statuses"):
        bad = copy.deepcopy(profile)
        del bad["revenue"][key]
        assert _errors(bad, "tenant-profile"), key

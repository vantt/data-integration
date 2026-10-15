"""Compiled SQL is locked by golden files and is deterministic."""
from __future__ import annotations

import re

import pytest

from analytics.compiler.formula import FormulaError, parse
from analytics.compiler.loader import load_profile, load_registry, profile_path
from analytics.compiler.sql import AsOf, CompileError, Compiler, window

from .golden_cases import AS_OF, CASES, golden_path
from .regen_golden import render


def _norm(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


@pytest.mark.parametrize("metric,window_name,runtime", CASES,
                         ids=[f"{m}-{w}{'-runtime' if r else ''}" for m, w, r in CASES])
def test_golden(metric, window_name, runtime):
    path = golden_path(metric, window_name, runtime)
    assert path.exists(), f"missing {path.name}: python3 -m analytics.tests.regen_golden"
    assert _norm(render(metric, window_name, runtime)) == _norm(path.read_text(encoding="utf-8"))


def test_every_metric_has_a_golden():
    assert set(load_registry().metrics) <= {m for m, _, _ in CASES}


def test_compile_is_deterministic():
    reg = load_registry()
    profile = load_profile(profile_path("fine_japan"))
    as_of = AsOf.literal(AS_OF)
    first = [Compiler(reg, profile).total(m, window("wtd", as_of), as_of) for m in sorted(reg.metrics)]
    second = [Compiler(load_registry(), profile).total(m, window("wtd", as_of), as_of) for m in sorted(reg.metrics)]
    assert first == second


def test_windows_are_relative_to_as_of():
    a = AsOf.literal("2026-10-11")
    assert window("wtd", a).end == "(DATE '2026-10-11' + 1)"
    assert window("mtd_before_as_of", a).end == "DATE '2026-10-11'"
    assert window("last_14_days", a).start == "(DATE '2026-10-11' - 13)"
    with pytest.raises(CompileError):
        window("ytd", a)
    with pytest.raises(CompileError):
        AsOf.literal("11/10/2026")


def test_time_zone_comes_from_the_profile():
    profile = load_profile(profile_path("fine_japan"))
    a = AsOf.literal(AS_OF)
    sql = Compiler(load_registry(), profile).total("net_sales", window("wtd", a), a)
    assert "timezone('Asia/Ho_Chi_Minh'" in sql
    bad = dict(profile, locale=dict(profile["locale"], timezone="Asia/Saigon'; DROP"))
    with pytest.raises(CompileError):
        Compiler(load_registry(), bad)


def test_missing_segment_binding_is_an_error():
    profile = load_profile(profile_path("fine_japan"))
    profile = dict(profile, segments={})
    a = AsOf.literal(AS_OF)
    with pytest.raises(CompileError, match="in_sales_scope"):
        Compiler(load_registry(), profile).total("net_sales", window("wtd", a), a)


def test_no_row_level_coalesce():
    reg = load_registry()
    profile = load_profile(profile_path("fine_japan"))
    a = AsOf.literal(AS_OF)
    for metric in reg.metrics:
        sql = Compiler(reg, profile).total(metric, window("wtd", a), a)
        assert not re.search(r"(SUM|COUNT)\(\s*COALESCE", sql), metric


@pytest.mark.parametrize("expr", [
    "gross_revenue * net_sales",          # two metrics multiply
    "net_sales / (gross_revenue / aov)",  # metric in a nested denominator
    "abs(net_sales)",                     # function other than greatest
    "net_sales ** 2",                     # operator not allowed
    "net_sales > 0",                      # comparison
    "day_of_month",                       # no metric
    "greatest(net_sales, gross_revenue)", # clamp floor must be a number
])
def test_formula_limits(expr):
    with pytest.raises(FormulaError):
        parse(expr)


def test_formula_ratio_of_linear_forms():
    f = parse("gross_revenue / (gmv_target * day_of_month / days_in_month)")
    assert f.metrics == ("gmv_target", "gross_revenue")
    assert parse("greatest(gmv_target - gross_revenue, 0) / days_left_in_month").metrics == ("gmv_target", "gross_revenue")

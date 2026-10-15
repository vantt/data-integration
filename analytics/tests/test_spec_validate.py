"""Report spec v2 and catalog: the real ones pass, broken fixtures fail."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from analytics.compiler import validate as v
from analytics.compiler.loader import CATALOG_FILE, PACKAGE_DIR, REPO_ROOT, discover_profiles

PROFILE = discover_profiles()[0]
SPEC = PACKAGE_DIR / "specs" / "ceo_weekly_pulse.yml"
NOT_ON_LIVE_DASHBOARD = {"Forecasted Month-End GMV", "Cần Đạt Mỗi Ngày (Required Daily Run-Rate)"}
BLUEPRINT = REPO_ROOT / "docs" / "analytics-handbook" / "blueprints" / "metabase" / "ceo_weekly_pulse.md"


@pytest.fixture()
def package(tmp_path: Path) -> Path:
    """Copy of catalog/ and specs/ (the catalog resolves specs relative to its parent)."""
    root = tmp_path / "analytics"
    shutil.copytree(PACKAGE_DIR / "catalog", root / "catalog")
    shutil.copytree(PACKAGE_DIR / "specs", root / "specs")
    return root


def _edit(path: Path, fn) -> None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _card(spec, card_id):
    for tab in spec["tabs"]:
        for block in tab["blocks"]:
            for card in block["cards"]:
                if card["card_id"] == card_id:
                    return card
    raise KeyError(card_id)


def _issues(package: Path, profile: Path = PROFILE):
    return v.validate(None, [profile], catalog_path=package / "catalog" / "catalog.yml")


def _errors(package: Path, profile: Path = PROFILE) -> list[str]:
    return [i.message for i in _issues(package, profile) if i.level == "ERROR"]


def test_real_catalog_and_spec_pass():
    issues = v.validate(None, None, catalog_path=CATALOG_FILE)
    assert not [i for i in issues if i.level == "ERROR"], issues
    assert any("2/22 data cards use inline_sql" in i.message for i in issues if i.level == "INFO")


def test_spec_follows_the_blueprint_order_and_names():
    """28 questions, same tabs, order and names as the running dashboard (Metabase 43). Its SQL equals the
    blueprint's; it lacks two blueprint questions, which the spec therefore leaves out."""
    tabs, current = [], None
    for line in BLUEPRINT.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^### Tab: (.*)$", line)
        if m:
            current = (m.group(1).strip(), [])
            tabs.append(current)
            continue
        m = re.match(r"^#### (?:❓ )?Question: (.*)$", line)
        if m:
            if m.group(1).strip() not in NOT_ON_LIVE_DASHBOARD:
                current[1].append(m.group(1).strip())
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    ours = [(t["baseline_name"], [c["baseline_name"] for b in t["blocks"] for c in b["cards"]]) for t in spec["tabs"]]
    assert ours == tabs
    assert sum(len(names) for _, names in ours) == 28


def test_copy_passes(package):
    assert _errors(package) == []


def test_unknown_metric_ref(package):
    _edit(package / "specs" / "ceo_weekly_pulse.yml", lambda d: _card(d, "aov_wow").__setitem__("metric_ref", "aov_x"))
    errors = _errors(package)
    assert any("'aov_x' is not in the registry" in e for e in errors)


def test_duplicate_card_id(package):
    _edit(package / "specs" / "ceo_weekly_pulse.yml",
          lambda d: _card(d, "gross_revenue_wow").__setitem__("card_id", "net_sales_wow"))
    assert any("card_id is not unique" in e for e in _errors(package))


def test_inline_sql_without_outputs(package):
    _edit(package / "specs" / "ceo_weekly_pulse.yml",
          lambda d: _card(d, "loss_making_channels")["inline_sql"].pop("outputs"))
    assert any("outputs" in e for e in _errors(package))


def test_inline_sql_must_not_read_the_clock(package):
    def clock(d):
        c = _card(d, "loss_making_channels")
        c["inline_sql"]["sql"] = c["inline_sql"]["sql"].replace("{{window_end}}", "current_date + 1")
    _edit(package / "specs" / "ceo_weekly_pulse.yml", clock)
    assert any("not the clock" in e for e in _errors(package))


def test_unknown_dimension(package):
    _edit(package / "specs" / "ceo_weekly_pulse.yml",
          lambda d: _card(d, "top_channels").__setitem__("dimensions", ["channels.channel_owner"]))
    assert any("not declared in the semantic layer" in e for e in _errors(package))


def test_wrong_time_axis(package):
    _edit(package / "specs" / "ceo_weekly_pulse.yml", lambda d: _card(d, "returns_wow").pop("time_axis"))
    assert any("axis 'return_date'" in e for e in _errors(package))


def test_catalog_metrics_must_match_spec(package):
    _edit(package / "catalog" / "catalog.yml", lambda d: d["reports"][0]["metrics"].remove("aov"))
    assert any("union of metric_ref" in e for e in _errors(package))


def test_catalog_cost_flag_is_derived(package):
    _edit(package / "catalog" / "catalog.yml", lambda d: d["reports"][0].__setitem__("cost_sensitive", False))
    assert any("cost_sensitive must be True" in e for e in _errors(package))


def test_kpi_tile_must_be_a_card(package):
    _edit(package / "catalog" / "catalog.yml", lambda d: d["reports"][0]["kpi_tiles"].append("nope"))
    assert any("kpi_tile 'nope'" in e for e in _errors(package))


def test_tenant_param_must_exist(package, tmp_path):
    profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
    del profile["tenant_params"]["monthly_target_goal"]
    path = tmp_path / "profile.yml"
    path.write_text(yaml.safe_dump(profile, allow_unicode=True), encoding="utf-8")
    assert any("monthly_target_goal" in e for e in _errors(package, path))


def test_too_many_inline_cards_warns(package):
    def inline_everything(d):
        sql = "SELECT 1 AS x WHERE {{as_of}} IS NOT NULL"
        for tab in d["tabs"]:
            for block in tab["blocks"]:
                for card in block["cards"]:
                    if card["kind"] in {"kpi_compare", "derived"}:
                        for key in ("metric_ref", "comparison", "goal", "bands", "pct_change_of", "time_axis"):
                            card.pop(key, None)
                        card["kind"] = "inline_sql"
                        card["inline_sql"] = {"sql": sql, "reason": "test", "cost_sensitive": False,
                                             "outputs": [{"name": "x", "type": "integer"}]}
    _edit(package / "specs" / "ceo_weekly_pulse.yml", inline_everything)
    issues = _issues(package)
    assert any("data cards use inline_sql" in i.message for i in issues if i.level == "WARN")


def test_skill_template_is_a_valid_spec():
    """The template shipped by .skills/analytics-design passes the schema and the registry checks."""
    from jsonschema import Draft202012Validator

    from analytics.compiler.loader import load_profile, load_registry, load_schema
    from analytics.compiler.spec_validate import check_spec

    path = REPO_ROOT / ".skills" / "analytics-design" / "templates" / "report_spec_v2_template.yml"
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert not list(Draft202012Validator(load_schema("report-spec")).iter_errors(spec))
    found = []
    check_spec(load_registry(), spec, "template", {"p": load_profile(PROFILE)},
               lambda w, m: found.append(m), lambda w, m: None)
    assert found == []

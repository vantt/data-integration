"""test_rolling_dirs.py — rolling export directories do not depend on model folders.

Run:
  python -m pytest scripts/tests/test_rolling_dirs.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_TRANSFORMATION_SCRIPTS = str(Path(__file__).resolve().parents[2] / "transformation" / "scripts")
if _TRANSFORMATION_SCRIPTS not in sys.path:
    sys.path.insert(0, _TRANSFORMATION_SCRIPTS)

import rolling_dirs  # noqa: E402


def _node(name, materialized, location=None):
    cfg = {"materialized": materialized}
    if location:
        cfg["location"] = location
    return {"resource_type": "model", "name": name, "config": cfg}


def test_manifest_selects_external_rolling_models_only(tmp_path):
    project = tmp_path / "transformation"
    (project / "target").mkdir(parents=True)
    nodes = {
        "model.p.fact_orders": _node("fact_orders", "external", "{{ get_rolling_location() }}"),
        "model.p.stg_marketing_spend": _node("stg_marketing_spend", "view", "{{ get_rolling_location() }}"),
        "model.p.mart_hug_optin": _node("mart_hug_optin", "external"),
    }
    (project / "target" / "manifest.json").write_text(json.dumps({"nodes": nodes}))
    assert rolling_dirs.rolling_model_names(str(project)) == ["fact_orders"]


def test_fallback_scans_every_folder_without_manifest(tmp_path):
    project = tmp_path / "transformation"
    for rel, body in {
        "models/core/facts/fact_orders.sql": "{{ config(location='{{ get_rolling_location() }}') }} select 1",
        "models/packs/finance/fact_cash_movement.sql": "{{ config(location='{{ get_rolling_location() }}') }} select 1",
        "models/cdm/std_orders.sql": "select 1",
    }.items():
        f = project / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body)
    assert rolling_dirs.rolling_model_names(str(project)) == ["fact_cash_movement", "fact_orders"]


def test_ensure_creates_only_missing_dirs(tmp_path):
    export = tmp_path / "export" / "marts"
    (export / "rolling" / "fact_orders").mkdir(parents=True)
    created = rolling_dirs.ensure_rolling_dirs(str(export), ["fact_orders", "dim_date"])
    assert created == [str(export / "rolling" / "dim_date")]
    assert (export / "rolling" / "dim_date").is_dir()

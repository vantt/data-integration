"""test_check_boundaries.py — the module boundary rules reject what they must reject.

Run:
  python -m pytest scripts/tests/test_check_boundaries.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from checks import check_boundaries as cb  # noqa: E402

PACKS = {"marketplace": ["shopee"]}


@pytest.mark.parametrize("src,dst,ok", [
    ("connector:sapo_v2", "connector:sapo_v2", True),
    ("connector:sapo_v2", "connector:shopee", False),
    ("connector:sapo_v2", "core", False),
    ("cdm", "connector:sapo_v2", True),
    ("cdm", "core", False),
    ("core", "cdm", True),
    ("core", "core", True),
    ("core", "connector:sapo_v2", False),
    ("core", "pack:marketplace", False),
    ("core", "tenant:fine_japan", False),
    ("pack:marketplace", "connector:shopee", True),
    ("pack:marketplace", "connector:sapo_v2", False),
    ("pack:marketplace", "pack:finance", False),
    ("pack:marketplace", "core", True),
    ("tenant:fine_japan", "connector:sapo_v2", True),
    ("monitoring", "tenant:fine_japan", True),
])
def test_matrix(src, dst, ok):
    assert cb._allowed(src, dst, PACKS) is ok


def _model(name, deps):
    return {"resource_type": "model", "name": name, "depends_on": {"nodes": deps}}


def test_dbt_violations_ref_source_and_missing_bucket():
    manifest = {"nodes": {
        "model.p.stg_x": _model("stg_x", ["source.p.raw.x"]),
        "model.p.fact_x": _model("fact_x", ["model.p.stg_x", "source.p.raw.y"]),
        "model.p.new_model": _model("new_model", []),
    }, "disabled": {}}
    spec = {"buckets": {"stg_x": "connector:sapo_v2", "fact_x": "core"}, "pack_connectors": {}}
    found = cb.dbt_violations(manifest, spec)
    assert ("dbt-ref", "fact_x", "stg_x [core -> connector:sapo_v2]") in found
    assert ("dbt-source", "fact_x", "raw.y") in found
    assert ("dbt-bucket", "new_model", "no bucket in model_buckets.yaml") in found
    assert not [f for f in found if f[1] == "stg_x"]  # connectors may read sources


def test_disabled_models_need_a_bucket_too():
    manifest = {"nodes": {}, "disabled": {"model.p.dormant": [_model("dormant", [])]}}
    found = cb.dbt_violations(manifest, {"buckets": {}, "pack_connectors": {}})
    assert ("dbt-bucket", "dormant", "no bucket in model_buckets.yaml") in found


def test_python_import_rule(tmp_path, monkeypatch):
    (tmp_path / "crm" / "ops").mkdir(parents=True)
    (tmp_path / "crm" / "ops" / "bad.py").write_text("from orchestration.notifications import x\n")
    (tmp_path / "crm" / "ops" / "ok.py").write_text("import json\nfrom crm.src import y\n")
    (tmp_path / "ingestion").mkdir()
    (tmp_path / "ingestion" / "bad.py").write_text("import orchestration.ops\n")
    monkeypatch.setattr(cb, "ROOT", str(tmp_path))
    found = cb.python_violations()
    assert ("py-import", "crm/ops/bad.py", "orchestration.notifications") in found
    assert ("py-import", "ingestion/bad.py", "orchestration.ops") in found
    assert not [f for f in found if f[1] == "crm/ops/ok.py"]


def test_seed_duplicate_rule(tmp_path, monkeypatch):
    seeds = tmp_path / "transformation" / "seeds"
    (seeds / "taxonomy").mkdir(parents=True)
    (seeds / "ref_brands.csv").write_text("a\n")
    (seeds / "taxonomy" / "ref_brands.csv").write_text("a\n")
    (seeds / "taxonomy" / "ref_other.csv").write_text("a\n")
    monkeypatch.setattr(cb, "ROOT", str(tmp_path))
    found = cb.seed_violations()
    assert len(found) == 1 and found[0][1] == "ref_brands.csv"


def test_connector_url_rule(tmp_path, monkeypatch):
    pkg = tmp_path / "orchestration" / "connectors" / "sheets"
    pkg.mkdir(parents=True)
    (pkg / "assets.py").write_text('URL = "https://docs.google.com/spreadsheets/d/abc"\n')
    monkeypatch.setattr(cb, "ROOT", str(tmp_path))
    found = cb.url_violations()
    assert found and found[0][0] == "connector-url"


def test_missing_tree_is_a_violation(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, "ROOT", str(tmp_path))
    found = cb.python_violations()
    assert ("py-scan", "crm", "directory not found") in found

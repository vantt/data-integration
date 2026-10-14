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


def _model(name, deps, path=None):
    return {"resource_type": "model", "name": name, "depends_on": {"nodes": deps},
            "original_file_path": path or f"models/any/{name}.sql"}


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
    assert not [f for f in found if f[1] == "stg_x" and f[0] != "dbt-path"]  # connectors may read sources


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


def test_model_must_live_in_its_module_folder():
    manifest = {"nodes": {
        "model.p.fact_ok": _model("fact_ok", [], "models/core/marts/fact_ok.sql"),
        "model.p.fact_bad": _model("fact_bad", [], "models/marts/sales/fact_bad.sql"),
        "model.p.stg_y": _model("stg_y", [], "models/connectors/shopee/staging/stg_y.sql"),
    }, "disabled": {}}
    spec = {"buckets": {"fact_ok": "core", "fact_bad": "core", "stg_y": "connector:sapo_v2"}, "pack_connectors": {}}
    found = {(r, s) for r, s, _ in cb.dbt_violations(manifest, spec)}
    assert ("dbt-path", "fact_bad") in found
    assert ("dbt-path", "stg_y") in found
    assert ("dbt-path", "fact_ok") not in found


def test_core_may_not_read_a_pack_without_allowlist():
    manifest = {"nodes": {
        "model.p.dim_x": _model("dim_x", ["model.p.int_cost"], "models/core/marts/dim_x.sql"),
        "model.p.int_cost": _model("int_cost", [], "models/packs/finance/marts/int_cost.sql"),
    }, "disabled": {}}
    spec = {"buckets": {"dim_x": "core", "int_cost": "pack:finance"}, "pack_connectors": {}}
    assert ("dbt-ref", "dim_x", "int_cost [core -> pack:finance]") in cb.dbt_violations(manifest, spec)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_connector_may_not_import_a_pack(tmp_path, monkeypatch):
    orch = tmp_path / "orchestration"
    _write(orch / "connectors" / "sapo_v2" / "jobs.py", "from orchestration.packs.crm import crm_sync\n")
    _write(orch / "connectors" / "shopee" / "jobs.py", "from orchestration.packs import crm\n")
    _write(orch / "connectors" / "misa_amis" / "jobs.py", "from orchestration.assets import serving\n")
    monkeypatch.setattr(cb, "ROOT", str(tmp_path))
    found = cb.orchestration_violations()
    assert ("orch-import", "orchestration/connectors/sapo_v2/jobs.py", "orchestration.packs.crm") in found
    assert ("orch-import", "orchestration/connectors/shopee/jobs.py", "orchestration.packs.crm") in found
    assert not [f for f in found if "misa_amis" in f[1]]


def test_pack_may_import_itself_but_not_another_pack(tmp_path, monkeypatch):
    orch = tmp_path / "orchestration"
    _write(orch / "packs" / "__init__.py", "from orchestration import module_registry\n")
    _write(orch / "packs" / "crm" / "jobs.py", "from orchestration.packs.crm.crm_sync import x\nfrom . import y\n")
    _write(orch / "packs" / "sales_playbook" / "a.py", "import orchestration.packs.crm.crm_sync\n")
    monkeypatch.setattr(cb, "ROOT", str(tmp_path))
    found = cb.orchestration_violations()
    assert found == [("orch-import", "orchestration/packs/sales_playbook/a.py", "orchestration.packs.crm")]


def test_pack_url_and_domain_rule(tmp_path, monkeypatch):
    pack = tmp_path / "orchestration" / "packs" / "crm"
    _write(pack / "crm_sync.py", 'URL = os.environ.get("CRM_REFRESH_URL", "http://crm:8090/admin/refresh")\n')
    _write(pack / "hosts.py", 'HOST = "fine-japan.mysapo.net"\nMOD = "orchestration.packs.crm"\nF = "seed.csv"\n')
    _write(tmp_path / "orchestration" / "connectors" / "sapo_v2" / "c.py", 'DOMAIN = "finejapan.vn"\n')
    monkeypatch.setattr(cb, "ROOT", str(tmp_path))
    found = cb.url_violations()
    assert [f for f in found if f[0] == "pack-url" and f[1] == "orchestration/packs/crm/crm_sync.py:1"]
    assert ("pack-url", "orchestration/packs/crm/hosts.py:1", "fine-japan.mysapo.net") in found
    assert ("connector-url", "orchestration/connectors/sapo_v2/c.py:1", "finejapan.vn") in found
    assert not [f for f in found if f[1].endswith("hosts.py:2") or f[1].endswith("hosts.py:3")]

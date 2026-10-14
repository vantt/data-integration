"""test_check_boundaries.py — the module boundary rules reject what they must reject.

Run:
  python -m pytest scripts/tests/test_check_boundaries.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

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


def _seed(name, path):
    return {"resource_type": "seed", "name": name, "original_file_path": path}


def test_core_may_not_read_a_tenant_seed():
    manifest = {"nodes": {
        "seed.p.seed_targets": _seed("seed_targets", "seeds/tenants/fine_japan/seed_targets.csv"),
        "seed.p.ref_brands": _seed("ref_brands", "seeds/taxonomy/ref_brands.csv"),
        "model.p.dim_t": _model("dim_t", ["seed.p.seed_targets", "seed.p.ref_brands"], "models/core/marts/dim_t.sql"),
        "model.p.std_t": _model("std_t", ["seed.p.seed_targets"], "models/cdm/staging/std_t.sql"),
        "model.p.stg_t": _model("stg_t", ["seed.p.seed_targets"], "models/connectors/gsheet/staging/stg_t.sql"),
    }, "disabled": {}}
    spec = {"buckets": {"dim_t": "core", "std_t": "cdm", "stg_t": "connector:gsheet"}, "pack_connectors": {}}
    found = [f for f in cb.dbt_violations(manifest, spec) if f[0] == "dbt-seed"]
    assert sorted(found) == [
        ("dbt-seed", "dim_t", "seed_targets [core -> tenant:fine_japan]"),
        ("dbt-seed", "std_t", "seed_targets [cdm -> tenant:fine_japan]"),
        ("dbt-seed", "stg_t", "seed_targets [connector:gsheet -> tenant:fine_japan]"),
    ]  # taxonomy seeds stay readable by everyone


def test_packs_monitoring_and_the_own_tenant_may_read_tenant_seeds():
    manifest = {"nodes": {
        "seed.p.seed_budget": _seed("seed_budget", "seeds/tenants/fine_japan/seed_budget.csv"),
        "model.p.fact_b": _model("fact_b", ["seed.p.seed_budget"], "models/packs/finance/marts/fact_b.sql"),
        "model.p.mart_dq": _model("mart_dq", ["seed.p.seed_budget"], "models/monitoring/mart_dq.sql"),
        "model.p.fact_us": _model("fact_us", ["seed.p.seed_budget"], "models/tenants/fine_japan/marts/fact_us.sql"),
        "model.p.fact_other": _model("fact_other", ["seed.p.seed_budget"], "models/tenants/acme/marts/fact_other.sql"),
    }, "disabled": {}}
    spec = {"buckets": {"fact_b": "pack:finance", "mart_dq": "monitoring", "fact_us": "tenant:fine_japan",
                        "fact_other": "tenant:acme"}, "pack_connectors": {}}
    found = [f for f in cb.dbt_violations(manifest, spec) if f[0] == "dbt-seed"]
    assert found == [("dbt-seed", "fact_other", "seed_budget [tenant:acme -> tenant:fine_japan]")]


def test_planted_tenant_seed_read_fails_the_check(tmp_path, monkeypatch, capsys):
    """End to end: a new core -> tenant seed edge not in the allowlist makes main() exit 1."""
    manifest = {"nodes": {
        "seed.p.seed_x": _seed("seed_x", "seeds/tenants/fine_japan/seed_x.csv"),
        "model.p.dim_x": _model("dim_x", ["seed.p.seed_x"], "models/core/marts/dim_x.sql"),
    }, "disabled": {}}
    (tmp_path / "manifest.json").write_text(__import__("json").dumps(manifest))
    (tmp_path / "buckets.yaml").write_text("buckets:\n  dim_x: core\npack_connectors: {}\n")
    (tmp_path / "allow.yaml").write_text("allow: []\n")
    for top in ("crm", "detailView", "ingestion"):
        (tmp_path / top).mkdir()
    monkeypatch.setattr(cb, "ROOT", str(tmp_path))
    monkeypatch.setattr(cb, "BUCKETS_FILE", str(tmp_path / "buckets.yaml"))
    monkeypatch.setattr(cb, "ALLOWLIST_FILE", str(tmp_path / "allow.yaml"))
    monkeypatch.setattr(sys, "argv", ["check_boundaries.py", "--manifest", str(tmp_path / "manifest.json")])
    assert cb.main() == 1
    assert "VIOLATION [dbt-seed] dim_x -> seed_x [core -> tenant:fine_japan]" in capsys.readouterr().out


# ------------------------------------------------------------------ pack_ref and the pack switch
def _core_reading(raw_code, enabled=True):
    node = _model("dim_x", ["model.p.int_cost"], "models/core/marts/dim_x.sql")
    node["raw_code"] = raw_code
    node["config"] = {"enabled": enabled}
    return {"nodes": {
        "model.p.dim_x": node,
        "model.p.int_cost": _model("int_cost", [], "models/packs/finance/marts/int_cost.sql"),
    }, "disabled": {}}


HOOK_SPEC = {"buckets": {"dim_x": "core", "int_cost": "pack:finance"}, "pack_connectors": {}}
VIOLATION = ("dbt-ref", "dim_x", "int_cost [core -> pack:finance]")


@pytest.mark.parametrize("raw_code,contracts,ok", [
    ("SELECT * FROM {{ pack_ref('finance', 'int_cost') }}", {"int_cost": "finance"}, True),
    ('SELECT * FROM {{ pack_ref("finance", "int_cost", {"a": "DOUBLE"}) }}', {"int_cost": "finance"}, True),
    ("SELECT * FROM {{ ref('int_cost') }}", {"int_cost": "finance"}, False),               # direct ref
    ("SELECT * FROM {{ pack_ref('finance', 'int_cost') }}", {}, False),                    # no contract
    ("SELECT * FROM {{ pack_ref('finance', 'int_cost') }}", {"int_cost": "crm"}, False),   # contract of another pack
    ("SELECT * FROM {{ pack_ref(pack='finance', model='int_cost') }}", {"int_cost": "finance"}, False),  # other spelling
    ("{{ pack_ref('finance', 'int_cost') }} JOIN {{ ref('int_cost') }}", {"int_cost": "finance"}, False),  # mixed
])
def test_core_reads_a_pack_only_through_pack_ref_with_a_contract(raw_code, contracts, ok):
    found = cb.dbt_violations(_core_reading(raw_code), HOOK_SPEC, contracts)
    assert (VIOLATION not in found) is ok


def test_disabled_models_keep_bucket_and_path_rules_but_no_edge_rules():
    manifest = _core_reading("SELECT * FROM {{ ref('int_cost') }}", enabled=False)
    off = _model("off_x", ["model.p.int_cost"], "models/marts/off_x.sql")
    manifest["disabled"] = {"model.p.off_x": [off]}
    spec = {"buckets": {**HOOK_SPEC["buckets"], "off_x": "core"}, "pack_connectors": {}}
    found = cb.dbt_violations(manifest, spec, {})
    assert VIOLATION not in found
    assert not [f for f in found if f[0] == "dbt-ref"]
    assert ("dbt-path", "off_x", "models/marts/off_x.sql not under models/core/") in found


def test_contracts_are_read_from_the_macro_file(tmp_path):
    path = tmp_path / "pack_contracts.sql"
    path.write_text("{# '<model>': {'pack': '<pack>', ... e.g. 'x_doc': {'pack': 'doc'} #}\n"
                    "{% macro pack_contracts() %}\n  {{ return({\n"
                    "    'int_customer_economics': {'pack': 'finance', 'columns': {'customer_id': 'VARCHAR'}},\n"
                    "    \"stg_crm__app_user\": {\"pack\": \"crm\", \"columns\": {}},\n  }) }}\n{% endmacro %}\n")
    assert cb.pack_contract_models(str(path)) == {"int_customer_economics": "finance", "stg_crm__app_user": "crm"}


def test_committed_pack_contracts_parse():
    assert isinstance(cb.pack_contract_models(), dict)


def _yaml(doc):
    return yaml.safe_dump(doc, sort_keys=False)


def _pack_tree(tmp_path, monkeypatch, modules, enabled_var, folders, defaults=None, pack_ids=None):
    defaults = modules if defaults is None else defaults
    pack_ids = folders if pack_ids is None else pack_ids
    _write(tmp_path / "modules.yaml", _yaml({"packs": modules}))
    packs_cfg = {p: {"+enabled": cb.ENABLED_TEMPLATE.format(pack=p, default=repr(list(defaults)))} for p in folders}
    _write(tmp_path / "dbt_project.yml", _yaml({
        "name": "sapo_warehouse", "models": {"sapo_warehouse": {"packs": packs_cfg}},
        "vars": {"external_root": "x", "enabled_packs": enabled_var}}))
    for p in folders:
        (tmp_path / "packs" / p).mkdir(parents=True)
    _write(tmp_path / "macros" / "pack_enabled.sql",
           "{% macro pack_ids() %}\n  {{ return(" + repr(list(pack_ids)) + ") }}\n{% endmacro %}\n")
    monkeypatch.setattr(cb, "MODULES_FILE", str(tmp_path / "modules.yaml"))
    monkeypatch.setattr(cb, "DBT_PROJECT_FILE", str(tmp_path / "dbt_project.yml"))
    monkeypatch.setattr(cb, "PACK_MODELS_DIR", str(tmp_path / "packs"))
    monkeypatch.setattr(cb, "PACK_MACROS_DIR", str(tmp_path / "macros"))


def test_module_config_in_sync(tmp_path, monkeypatch):
    _pack_tree(tmp_path, monkeypatch, ["crm", "finance"], ["crm", "finance"], ["crm", "finance", "hug"])
    assert cb.module_config_violations() == ([], "")


@pytest.mark.parametrize("kwargs,subject", [
    ({"enabled_var": ["crm"]}, "vars.enabled_packs"),
    ({"defaults": ["crm"]}, "models.packs.finance.+enabled"),
    ({"pack_ids": ["crm", "finance"]}, "pack_ids()"),
    ({"modules": ["crm", "finance", "nope"], "enabled_var": ["crm", "finance", "nope"],
      "defaults": ["crm", "finance", "nope"]}, "modules.yaml packs.nope"),
])
def test_module_config_mismatch_fails_and_prints_the_block(tmp_path, monkeypatch, kwargs, subject):
    args = {"modules": ["crm", "finance"], "enabled_var": ["crm", "finance"], "folders": ["crm", "finance", "hug"]}
    args.update(kwargs)
    _pack_tree(tmp_path, monkeypatch, **args)
    problems, block = cb.module_config_violations()
    assert subject in [s for _, s, _ in problems]
    modules = args["modules"]
    assert f"  enabled_packs: [{', '.join(modules)}]" in block
    assert f"('hug' in var('enabled_packs', {modules!r}))" in block
    assert "return(['crm', 'finance', 'hug'])" in block


def test_committed_pack_switch_is_in_sync():
    """modules.yaml, dbt_project.yml and pack_ids() of this checkout agree."""
    assert cb.module_config_violations() == ([], "")


def test_module_config_problem_fails_main(tmp_path, monkeypatch, capsys):
    _pack_tree(tmp_path, monkeypatch, ["crm", "finance"], ["crm"], ["crm", "finance"])
    (tmp_path / "manifest.json").write_text('{"nodes": {}, "disabled": {}}')
    (tmp_path / "buckets.yaml").write_text("buckets: {}\npack_connectors: {}\n")
    (tmp_path / "allow.yaml").write_text("allow: []\n")
    for top in ("crm", "detailView", "ingestion"):
        (tmp_path / top).mkdir()
    monkeypatch.setattr(cb, "ROOT", str(tmp_path))
    monkeypatch.setattr(cb, "BUCKETS_FILE", str(tmp_path / "buckets.yaml"))
    monkeypatch.setattr(cb, "ALLOWLIST_FILE", str(tmp_path / "allow.yaml"))
    monkeypatch.setattr(sys, "argv", ["check_boundaries.py", "--manifest", str(tmp_path / "manifest.json")])
    assert cb.main() == 1
    out = capsys.readouterr().out
    assert "VIOLATION [module-config] vars.enabled_packs" in out
    assert "Expected pack switch" in out and "enabled_packs: [crm, finance]" in out

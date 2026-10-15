"""test_dbt_inventory.py — a repointed dependency is accepted only while its lineage is intact.

Run:
  python -m pytest scripts/tests/test_dbt_inventory.py -q
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from checks import dbt_inventory  # noqa: E402


def _node(*deps: str) -> dict:
    return {"resource_type": "model", "depends_on": sorted(deps), "checksum": "x", "config": {}}


def _diff(tmp_path, a: dict, b: dict, **flags) -> int:
    pa, pb = tmp_path / "a.json", tmp_path / "b.json"
    pa.write_text(json.dumps(a))
    pb.write_text(json.dumps(b))
    args = argparse.Namespace(a=str(pa), b=str(pb), allow_new=flags.get("allow_new", False),
                              allow_code_change=flags.get("allow_code_change", False))
    return dbt_inventory.cmd_diff(args)


BASE = {"stg": _node(), "core": _node("stg")}


def test_repoint_through_pass_through_is_accepted(tmp_path, capsys):
    new = {"stg": _node(), "std": _node("stg"), "core": _node("std")}
    rc = _diff(tmp_path, BASE, new, allow_new=True, allow_code_change=True)
    out = capsys.readouterr().out
    assert rc == 0
    assert "INFO core: repointed dependency: stg -> via std" in out


def test_removed_dependency_no_longer_upstream_is_rejected(tmp_path, capsys):
    new = {"stg": _node(), "other": _node(), "core": _node("other")}
    rc = _diff(tmp_path, BASE, new, allow_new=True, allow_code_change=True)
    assert rc == 1
    assert "DIFF core: depends_on" in capsys.readouterr().out


def test_repoint_without_allow_code_change_is_rejected(tmp_path, capsys):
    new = {"stg": _node(), "std": _node("stg"), "core": _node("std")}
    rc = _diff(tmp_path, BASE, new, allow_new=True)
    assert rc == 1
    assert "DIFF core: depends_on" in capsys.readouterr().out


def _manifest_with_disabled_test() -> dict:
    model = {"resource_type": "model", "depends_on": {"nodes": []}, "config": {"enabled": True},
             "checksum": {"checksum": "c"}, "compiled_code": "select 1"}
    return {"nodes": {
        "model.p.core_x": model,
        "model.p.off_y": {**model, "config": {"enabled": False}, "compiled_code": "select 2"},
        "test.p.on_t": {"resource_type": "test", "depends_on": {"nodes": ["model.p.core_x"]}, "config": {"enabled": True}},
        # dbt keeps a singular test whose pack model is disabled, with enabled false
        "test.p.off_t": {"resource_type": "test", "depends_on": {"nodes": ["model.p.core_x"]}, "config": {"enabled": False}},
    }}


def test_export_ignores_disabled_nodes(tmp_path):
    (tmp_path / "m.json").write_text(json.dumps(_manifest_with_disabled_test()))
    out = tmp_path / "inv.json"
    assert dbt_inventory.cmd_export(argparse.Namespace(manifest=str(tmp_path / "m.json"), out=str(out))) == 0
    inv = json.loads(out.read_text())
    assert sorted(inv) == ["model.p.core_x"]
    assert inv["model.p.core_x"]["tests"] == ["test.p.on_t"]


def test_compiled_diff_ignores_disabled_models(tmp_path, capsys):
    a = _manifest_with_disabled_test()
    b = _manifest_with_disabled_test()
    del b["nodes"]["model.p.off_y"]
    (tmp_path / "a.json").write_text(json.dumps(a))
    (tmp_path / "b.json").write_text(json.dumps(b))
    args = argparse.Namespace(a=str(tmp_path / "a.json"), b=str(tmp_path / "b.json"), allow_code_change=False)
    assert dbt_inventory.cmd_compiled_diff(args) == 0
    assert "1 vs 1 models" in capsys.readouterr().out


def test_added_test_on_a_node_needs_allow_new(tmp_path, capsys):
    a = {"m": {**_node(), "tests": ["test.p.unique_m"]}}
    b = {"m": {**_node(), "tests": ["test.p.pack_contract_m", "test.p.unique_m"]}}
    assert _diff(tmp_path, a, b) == 1
    assert _diff(tmp_path, a, b, allow_new=True) == 0
    assert _diff(tmp_path, b, a, allow_new=True) == 1    # a removed test is always a difference


def test_changed_description_needs_allow_code_change(tmp_path):
    a = {"m": {**_node(), "description": "Reads mart_x."}}
    b = {"m": {**_node(), "description": "Reads int_y."}}
    assert _diff(tmp_path, a, b) == 1
    assert _diff(tmp_path, a, b, allow_new=True) == 1
    assert _diff(tmp_path, a, b, allow_code_change=True) == 0


SPLIT_BASE = {"fact": _node(), "mart": _node("fact"), "reader": _node("mart")}


def test_reader_moved_to_the_split_off_part_is_accepted(tmp_path, capsys):
    """mart is split: its sales half becomes int_sales, which mart now reads; reader reads int_sales."""
    new = {"fact": _node(), "int_sales": _node("fact"), "mart": _node("int_sales"), "reader": _node("int_sales")}
    rc = _diff(tmp_path, SPLIT_BASE, new, allow_new=True, allow_code_change=True)
    out = capsys.readouterr().out
    assert rc == 0
    assert "INFO reader: repointed dependency: mart -> split into int_sales" in out


def test_swap_to_a_node_the_removed_one_does_not_read_is_rejected(tmp_path, capsys):
    new = {"fact": _node(), "other": _node("fact"), "mart": _node("fact"), "reader": _node("other")}
    rc = _diff(tmp_path, SPLIT_BASE, new, allow_new=True, allow_code_change=True)
    assert rc == 1
    assert "DIFF reader: depends_on" in capsys.readouterr().out


def test_split_without_allow_code_change_is_rejected(tmp_path):
    new = {"fact": _node(), "int_sales": _node("fact"), "mart": _node("int_sales"), "reader": _node("int_sales")}
    assert _diff(tmp_path, SPLIT_BASE, new, allow_new=True) == 1


def test_removed_dependency_still_upstream_through_other_deps_is_described(tmp_path, capsys):
    a = {"mart": _node(), "health": _node("mart"), "queue": _node("mart", "health")}
    b = {"mart": _node(), "health": _node("mart"), "queue": _node("health")}
    assert _diff(tmp_path, a, b, allow_code_change=True) == 0
    assert "queue: repointed dependency: mart -> still upstream through unchanged dependencies" in capsys.readouterr().out

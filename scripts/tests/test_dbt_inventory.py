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
    assert "INFO core: repointed dependency kept upstream: stg -> via std" in out


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

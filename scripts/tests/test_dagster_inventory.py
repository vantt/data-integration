"""test_dagster_inventory.py — assets never resolve to a dbt node that dbt disabled.

Run (shadow container, dagster importable):
  python -m pytest scripts/tests/test_dagster_inventory.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from checks import dagster_inventory  # noqa: E402


class _Key:
    def __init__(self, *path):
        self.path = list(path)


class _Translator:
    def get_asset_key(self, node):
        if node.get("unmapped"):
            raise KeyError(node["name"])
        return _Key("marts", node["name"])


def test_key_map_skips_disabled_nodes_and_tests():
    manifest = {
        "nodes": {
            "model.p.on": {"resource_type": "model", "name": "on", "config": {"enabled": True}},
            "model.p.off": {"resource_type": "model", "name": "off", "config": {"enabled": False}},
            "test.p.t": {"resource_type": "test", "name": "t", "config": {"enabled": True}},
            "seed.p.s": {"resource_type": "seed", "name": "s", "config": {}},
        },
        "sources": {"source.p.raw.x": {"resource_type": "source", "name": "x", "unmapped": True}},
    }
    assert dagster_inventory.asset_key_to_unique_id(manifest, _Translator()) == {
        "marts/on": "model.p.on", "marts/s": "seed.p.s"}


def _diff(tmp_path, a, b, allow_new):
    import argparse
    import json
    pa, pb = tmp_path / "a.json", tmp_path / "b.json"
    pa.write_text(json.dumps(a))
    pb.write_text(json.dumps(b))
    return dagster_inventory.cmd_diff(argparse.Namespace(a=str(pa), b=str(pb), allow_new=allow_new))


def _inv(asset_uid, job_uids=()):
    return {"assets": {"sapo/ingest": {"group": "g", "dbt_unique_id": asset_uid}},
            "jobs": {"j": {"assets": ["sapo/ingest"], "dbt_unique_ids": list(job_uids), "tags": {}}},
            "schedules": {}, "sensors": {}, "sla": {}, "asset_checks": []}


def test_ingest_asset_mapped_to_a_new_dbt_source_is_an_addition(tmp_path):
    a = _inv(None, ["model.p.old"])
    b = _inv("source.p.raw.new", ["model.p.old"])
    assert _diff(tmp_path, a, b, allow_new=True) == 0
    assert _diff(tmp_path, a, b, allow_new=False) == 1


def test_remapping_an_asset_to_a_dbt_node_the_baseline_knew_is_a_difference(tmp_path):
    a = _inv(None, ["source.p.raw.old"])
    b = _inv("source.p.raw.old", ["source.p.raw.old"])
    assert _diff(tmp_path, a, b, allow_new=True) == 1
    a = _inv("source.p.raw.old")
    b = _inv("source.p.raw.new")
    assert _diff(tmp_path, a, b, allow_new=True) == 1

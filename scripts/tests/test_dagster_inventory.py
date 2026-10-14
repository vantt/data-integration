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

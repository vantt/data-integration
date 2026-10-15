"""test_capabilities_seeds.py — the capability seeds name real connectors, modules and probes.

Run:
  python -m pytest scripts/tests/test_capabilities_seeds.py -q
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SEEDS = REPO / "transformation" / "seeds" / "capabilities"
MODEL = REPO / "transformation" / "models" / "monitoring" / "mart_capabilities.sql"


def _rows(name: str) -> list[dict]:
    with open(SEEDS / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _packages(kind: str) -> set[str]:
    return {p.name for p in (REPO / "orchestration" / kind).iterdir()
            if (p / "__init__.py").exists() and not p.name.startswith("__")}


def test_connector_ids_are_connector_packages():
    unknown = {r["connector_id"] for r in _rows("connector_capabilities.csv")} - _packages("connectors")
    assert not unknown, f"connector_id not under orchestration/connectors/: {sorted(unknown)}"


def test_required_by_is_core_or_a_pack():
    unknown = {r["required_by"] for r in _rows("capability_catalog.csv")} - _packages("packs") - {"core"}
    assert not unknown, f"required_by neither core nor a pack: {sorted(unknown)}"


def test_declared_capabilities_are_in_the_catalog():
    catalog = {r["capability"] for r in _rows("capability_catalog.csv")}
    unknown = {r["capability"] for r in _rows("connector_capabilities.csv")} - catalog
    assert not unknown, f"declared but not in capability_catalog.csv: {sorted(unknown)}"


def test_each_connector_is_one_block_of_rows():
    ids = [r["connector_id"] for r in _rows("connector_capabilities.csv")]
    blocks = [c for i, c in enumerate(ids) if i == 0 or ids[i - 1] != c]
    assert len(blocks) == len(set(blocks)), f"connector rows not contiguous: {blocks}"


def test_every_catalog_capability_has_a_probe():
    """mart_capabilities also fails at build time; this catches it before dbt runs."""
    block = MODEL.read_text().split("set probes = {", 1)[1].split("} -%}", 1)[0]
    probes = set(re.findall(r"^\s*'(\w+)':\s*\{", block, flags=re.M))
    catalog = {r["capability"] for r in _rows("capability_catalog.csv")}
    assert catalog == probes, f"catalog without probe: {sorted(catalog - probes)}; probe without catalog: {sorted(probes - catalog)}"

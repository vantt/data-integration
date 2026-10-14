"""Read orchestration/config/modules.yaml: which connectors, packs and tenants are enabled.

The kernel never imports a connector, pack or tenant package by name; it asks the loaders in
`orchestration.connectors`, `orchestration.packs` and `orchestration.tenants`, which read the
ids from this file (one list per kind, file order kept).
"""
from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import yaml

MODULES_FILE = Path(__file__).resolve().parent / "config" / "modules.yaml"
KINDS = ("connectors", "packs", "tenants")


def enabled_ids(kind: str, modules_file: Path = MODULES_FILE) -> list[str]:
    """Ids listed under `kind` in modules.yaml, in file order (empty when the key is absent)."""
    if kind not in KINDS:
        raise ValueError(f"unknown module kind {kind!r}; expected one of {KINDS}")
    with open(modules_file) as fh:
        data = yaml.safe_load(fh) or {}
    ids = data.get(kind) or []
    if not isinstance(ids, list) or not all(isinstance(i, str) and i for i in ids):
        raise ValueError(f"{modules_file}: `{kind}` must be a list of ids, got {ids!r}")
    return list(ids)


def import_each(package: str, ids: list[str], submodule: str = "") -> list[ModuleType]:
    """Import `<package>.<id>[.<submodule>]` for every id; an unknown id fails loudly."""
    suffix = f".{submodule}" if submodule else ""
    return [importlib.import_module(f"{package}.{i}{suffix}") for i in ids]

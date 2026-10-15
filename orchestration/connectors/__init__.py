"""Connector packages: one package per data source under orchestration/connectors/<id>/.

`orchestration/config/modules.yaml` lists the enabled ids. A package exports plain
lists/dicts (see connectors/README.md for the contract):

  <id>/__init__.py   ASSETS, ASSET_CHECKS, CHECK_ASSET_DEFS, NIGHTLY_ASSETS, DIGEST_ASSETS,
                     DIGEST_DISPLAY, JOB_MAX_RUNTIME, DBT_SOURCE_KEYS
  <id>/jobs.py       JOBS, SCHEDULES, SENSORS

Jobs live in their own module because they select the dbt assets, and assets/dbt.py in
turn reads DBT_SOURCE_KEYS from the packages: importing jobs from the package __init__
would make that a cycle.
"""
from __future__ import annotations

from types import ModuleType

from orchestration import module_registry

# Module attribute so tests can point the loader at another modules.yaml.
_MODULES_FILE = module_registry.MODULES_FILE


def enabled_ids() -> list[str]:
    """Connector ids from modules.yaml, in file order."""
    return module_registry.enabled_ids("connectors", _MODULES_FILE)


def load_enabled(ids: list[str] | None = None) -> list[ModuleType]:
    """Import the enabled connector packages (assets and data, no jobs)."""
    return module_registry.import_each(__name__, enabled_ids() if ids is None else ids)


def load_enabled_jobs(ids: list[str] | None = None) -> list[ModuleType]:
    """Import `<id>.jobs` (JOBS, SCHEDULES, SENSORS) of the enabled connectors."""
    return module_registry.import_each(__name__, enabled_ids() if ids is None else ids, "jobs")

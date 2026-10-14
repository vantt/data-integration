"""Product packs: one package per pack under orchestration/packs/<id>/.

A pack is reusable product logic (CRM, HUG, finance, sales playbook) that runs on the data the
connectors bring in; the tenant only supplies its data and configuration. `packs:` in
orchestration/config/modules.yaml lists the enabled ids. A package exports plain lists (see
packs/README.md for the contract):

  <id>/__init__.py   ASSETS, NIGHTLY_ASSETS
  <id>/jobs.py       JOBS, SCHEDULES, SENSORS

A pack's dbt models live in transformation/models/packs/<id>/ and run inside the kernel's dbt
assets; a pack without Dagster code of its own exports empty lists.
"""
from __future__ import annotations

from types import ModuleType

from orchestration import module_registry

# Module attribute so tests can point the loader at another modules.yaml.
_MODULES_FILE = module_registry.MODULES_FILE


def enabled_ids() -> list[str]:
    """Pack ids from modules.yaml, in file order."""
    return module_registry.enabled_ids("packs", _MODULES_FILE)


def load_enabled(ids: list[str] | None = None) -> list[ModuleType]:
    """Import the enabled pack packages (assets, no jobs)."""
    return module_registry.import_each(__name__, enabled_ids() if ids is None else ids)


def load_enabled_jobs(ids: list[str] | None = None) -> list[ModuleType]:
    """Import `<id>.jobs` (JOBS, SCHEDULES, SENSORS) of the enabled packs."""
    return module_registry.import_each(__name__, enabled_ids() if ids is None else ids, "jobs")

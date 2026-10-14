"""Tenant overlays: per-business configuration under orchestration/tenants/<id>/config.py.

`tenants:` in orchestration/config/modules.yaml lists the tenant of this deployment. Shared code
(kernel, connectors, packs) reads tenant values through `setting(name)` and never carries a
default for them: a value that is neither in the environment nor in the tenant config is an
error (fail closed), not a silent fallback to another business's value.
"""
from __future__ import annotations

import os
from types import ModuleType

from orchestration import module_registry

# Module attribute so tests can point the loader at another modules.yaml.
_MODULES_FILE = module_registry.MODULES_FILE


class TenantConfigError(RuntimeError):
    """A tenant setting is missing or defined by more than one enabled tenant."""


def enabled_ids() -> list[str]:
    """Tenant ids from modules.yaml, in file order."""
    return module_registry.enabled_ids("tenants", _MODULES_FILE)


def load_configs(ids: list[str] | None = None) -> list[ModuleType]:
    """Import `<id>.config` of the enabled tenants."""
    return module_registry.import_each(__name__, enabled_ids() if ids is None else ids, "config")


def setting(name: str) -> str:
    """Value of the tenant setting `name`.

    The environment variable of the same name wins when it is set (even to an empty string,
    exactly like `os.environ.get(name, default)`); otherwise the value comes from the
    `config.py` of the enabled tenant. Raises TenantConfigError when no enabled tenant defines
    it, or when two enabled tenants do.
    """
    if name in os.environ:
        return os.environ[name]
    ids = enabled_ids()
    values = {mod.__name__: getattr(mod, name) for mod in load_configs(ids) if hasattr(mod, name)}
    if len(values) == 1:
        return next(iter(values.values()))
    if not values:
        raise TenantConfigError(
            f"tenant setting {name} is not configured: set the environment variable {name} or "
            f"define {name} in orchestration/tenants/<tenant>/config.py of a tenant listed under "
            f"`tenants:` in orchestration/config/modules.yaml (enabled: {ids or 'none'})"
        )
    raise TenantConfigError(f"tenant setting {name} is defined by more than one tenant: {sorted(values)}")

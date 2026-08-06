"""action_catalog_port.py — domain port (Protocol) for reading the opportunity-type catalog."""
from __future__ import annotations

from typing import Protocol

from domain.entities.action_scenario import ActionScenario


class ActionCatalogPort(Protocol):
    """Outbound port for reading cache.wh_action_scenario_registry."""

    def list_catalog(self) -> list[ActionScenario]:
        """Return the full (action_type, mart) catalog, ordered for display grouping.
        Returns [] when the table is absent (Phase 01/02 not yet deployed) rather
        than raising — a stale/missing catalog is a visibility gap, not a crash."""
        ...

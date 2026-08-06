"""action_catalog_repository.py — read-only adapter over cache.wh_action_scenario_registry.

Graceful-empty: OperationalError for a missing table (Phase 01/02 not yet deployed to
this environment) → [], never raised — matches the cache_repository.py house rule.
Python is never the writer here; crm/sync/reverse_etl_warehouse_to_crm.py owns writes.
"""
from __future__ import annotations

import sqlite3

from domain.entities.action_scenario import ActionScenario


class SQLiteActionCatalogRepository:
    """Read adapter for cache.wh_action_scenario_registry."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def list_catalog(self) -> list[ActionScenario]:
        sql = """
            SELECT action_type, mart, enabled, scenario_group, description_vi
            FROM cache.wh_action_scenario_registry
            ORDER BY scenario_group, mart, action_type
        """
        try:
            rows = self._conn.execute(sql).fetchall()
        except sqlite3.OperationalError as exc:
            if "no such table" in str(exc).lower():
                return []
            raise
        return [
            ActionScenario(
                action_type=row["action_type"],
                mart=row["mart"],
                enabled=bool(row["enabled"]),
                scenario_group=row["scenario_group"],
                description_vi=row["description_vi"],
            )
            for row in rows
        ]

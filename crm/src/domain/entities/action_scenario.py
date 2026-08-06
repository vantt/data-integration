"""action_scenario.py — read model for the opportunity-type catalog (cache.wh_action_scenario_registry).

Pure dataclass; no HTTP/DB adapter imports. Populated by SQLiteActionCatalogRepository.
"""
from __future__ import annotations

from dataclasses import dataclass

# Shared mart-name literals — imported by both action_state_repository.py/
# action_catalog_repository.py (Phase 04, writes/reads) and cache_repository.py
# (Phase 05, matches crm_action_dismissal.source_mart) so the two sides cannot drift apart.
MART_CUSTOMER = "mart_customer_action_queue"
MART_SKU = "mart_customer_sku_action_queue"


@dataclass
class ActionScenario:
    """One (action_type, mart) row from the opportunity-type catalog.

    `enabled` is the GLOBAL kill-switch (seed_action_scenario_registry) — independent
    of any per-party suppression in crm_action_dismissal. A globally-disabled type
    (enabled=False) is never suggested to any customer regardless of per-party state.
    """
    action_type: str
    mart: str                # 'mart_customer_action_queue' | 'mart_customer_sku_action_queue'
    enabled: bool
    scenario_group: str
    description_vi: str

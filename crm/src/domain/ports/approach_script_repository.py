"""approach_script_repository.py — Port (Protocol) for ApproachScript reads.

Concrete adapters (FileApproachScriptRepository, future SQLite variant) implement
this interface via duck-typing — no inheritance required.
"""
from __future__ import annotations

from typing import Protocol

from domain.entities.approach_script import ApproachScript


class ApproachScriptRepository(Protocol):
    """Outbound port for reading AI approach scripts by customer_id."""

    def get_by_customer_id(self, customer_id: int) -> ApproachScript | None:
        """Return the script for customer_id, or None if not found."""
        ...

    def list_customer_ids(self) -> set[int]:
        """Return the set of customer_ids that have a script file.

        Called once per worklist load — no cache, so newly-dropped files are
        reflected on the next request without a server restart.
        """
        ...

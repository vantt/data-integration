"""hug_campaign_repository_adapter.py — OOP adapter wrapping hug.campaign_repository.

Thin wrapper that binds a sqlite3.Connection at construction and forwards all
calls to the pure-functional hug.campaign_repository module. Named with the
_adapter suffix to avoid a naming conflict with the wrapped module.
"""
from __future__ import annotations

import sqlite3

import hug.campaign_repository as _repo


class HugCampaignRepositoryAdapter:
    """OOP adapter for crm_hug_campaign CRUD and history snapshots.

    Receives a sqlite3.Connection at construction and delegates to the
    functional hug.campaign_repository module for all data-access logic.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    def list_campaigns(self, status: str | None = None) -> list[sqlite3.Row]:
        """Return campaigns ordered by priority ASC, optionally filtered by status."""
        return _repo.list_campaigns(self._conn, status)

    def get_campaign(self, campaign_id: str) -> sqlite3.Row | None:
        """Return the campaign row for campaign_id, or None if not found."""
        return _repo.get_campaign(self._conn, campaign_id)

    def list_history(self, campaign_id: str, limit: int = 20) -> list[sqlite3.Row]:
        """Return the most recent history snapshots for a campaign, newest first."""
        return _repo.list_history(self._conn, campaign_id, limit)

    def suggest_next_priority(self) -> int:
        """Return MAX(priority)+10 across active campaigns, or 10 if none exist."""
        return _repo.suggest_next_priority(self._conn)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def upsert_campaign(self, row: dict) -> sqlite3.Row:
        """Insert or replace a campaign row and write a history snapshot."""
        return _repo.upsert_campaign(self._conn, row)

    def archive_campaign(self, campaign_id: str) -> None:
        """Soft-delete a campaign by setting status='archived' and writing a snapshot."""
        _repo.archive_campaign(self._conn, campaign_id)

    def restore_snapshot(self, campaign_id: str, snapshot_id: int) -> sqlite3.Row:
        """Restore a campaign to a prior state captured in history."""
        return _repo.restore_snapshot(self._conn, campaign_id, snapshot_id)

    def find_overlapping_campaigns(
        self,
        targeting: dict,
        exclude_id: str | None = None,
    ) -> list[dict]:
        """Return active campaigns whose targeting overlaps with `targeting`."""
        from hug.campaign_overlap import find_overlapping_campaigns as _find
        return _find(self._conn, targeting, exclude_id=exclude_id)

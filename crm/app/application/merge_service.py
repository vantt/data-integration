"""merge_service.py — MergeService: party merge and undo orchestration.

Mirrors Go MergeService in crm/app/internal/application/merge_service.go.
All atomic persistence (re-point identities, set flags, write log) is delegated
to DedupRepository; this service handles validation and snapshot construction.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from domain.entities.party import MergeLog
from domain.ports.party_repository import PartyRepository
from domain.ports.dedup_repository import DedupRepository


# ---------------------------------------------------------------------------
# Snapshot schema (mirrors Go mergeSnapshot struct)
# ---------------------------------------------------------------------------

@dataclass
class _MergeSnapshot:
    """Pre-merge state stored in crm_party_merge_log.snapshot for undo."""
    merged_party_is_merged: bool
    merged_party_merged_into: Optional[str]
    reassigned_identity_ids: list[str]

    def to_json(self) -> str:
        return json.dumps({
            "merged_party_is_merged": self.merged_party_is_merged,
            "merged_party_merged_into": self.merged_party_merged_into,
            "reassigned_identity_ids": self.reassigned_identity_ids,
        })


# ---------------------------------------------------------------------------
# MergeService
# ---------------------------------------------------------------------------

class MergeService:
    """Orchestrates party merges and undos.

    Validation and snapshot construction live here.
    Atomic DB work (identity re-point, flag set, log insert) lives in DedupRepository.
    """

    def __init__(self, party_repo: PartyRepository, dedup_repo: DedupRepository) -> None:
        self._party_repo = party_repo
        self._dedup_repo = dedup_repo

    def merge(
        self,
        surviving_party_id: str,
        merged_party_id: str,
        reason: str,
        merged_by: Optional[str],
    ) -> str:
        """Absorb merged_party_id into surviving_party_id.

        Steps (mirrors Go Merge):
          1. Validate both parties exist and are not already merged.
          2. Gather identities of the merged party for snapshot.
          3. Build JSON snapshot (enough state to fully reverse the merge).
          4. Delegate atomic transaction to DedupRepository.merge().

        Returns the merge_id of the new log entry.
        Raises ValueError for invalid party states.
        """
        # Validate surviving party
        surviving = self._party_repo.get_by_id(surviving_party_id)
        if surviving is None:
            raise ValueError(f"merge: surviving party {surviving_party_id!r} not found")
        if surviving.is_merged:
            raise ValueError(
                f"merge: surviving party {surviving_party_id!r} already merged into {surviving.merged_into!r}"
            )

        # Validate merged party
        merged = self._party_repo.get_by_id(merged_party_id)
        if merged is None:
            raise ValueError(f"merge: merged party {merged_party_id!r} not found")
        if merged.is_merged:
            raise ValueError(
                f"merge: party {merged_party_id!r} is already merged into {merged.merged_into!r}"
            )

        # Gather identities of merged party for snapshot
        identities = self._party_repo.list_identities(merged_party_id)
        identity_ids = [i.identity_id for i in identities]

        snap = _MergeSnapshot(
            merged_party_is_merged=merged.is_merged,
            merged_party_merged_into=merged.merged_into,
            reassigned_identity_ids=identity_ids,
        )

        merge_id = self._dedup_repo.merge(
            surviving_party_id,
            merged_party_id,
            reason,
            merged_by,
            snap.to_json(),
        )
        return merge_id

    def undo_merge(self, merge_id: str, undone_by: Optional[str] = None) -> None:
        """Reverse a previously completed merge using the stored snapshot.

        Delegates to DedupRepository.undo_merge() which reads the JSON snapshot,
        restores identity ownership, clears merge flags, and marks the log row undone.
        undone_by is informational — stored in the log if the repo supports it.
        """
        self._dedup_repo.undo_merge(merge_id)

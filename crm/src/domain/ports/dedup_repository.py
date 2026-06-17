from __future__ import annotations

from typing import Protocol

from domain.entities.party import DedupCandidate, MergeLog


class DedupRepository(Protocol):
    """Outbound port for dedup candidates and merge-log operations."""

    def insert_candidate(self, candidate: DedupCandidate) -> None:
        """Add a new suspect-match pair if no pending/merged candidate already
        exists for the same (party_a, party_b) pair."""
        ...

    def candidate_exists(self, party_a: str, party_b: str) -> bool:
        """Return True if a non-rejected candidate already exists for the pair.
        Order-independent: (a, b) == (b, a)."""
        ...

    def list_candidates(self, status: str) -> list[DedupCandidate]:
        """Return dedup candidates filtered by status.
        Pass empty string to return all statuses."""
        ...

    def get_candidate(self, candidate_id: str) -> DedupCandidate | None:
        """Return a single candidate by ID, or None if not found."""
        ...

    def update_candidate_status(
        self,
        candidate_id: str,
        status: str,
        reviewed_by: str | None,
    ) -> None:
        """Set status, reviewed_by, reviewed_at on a candidate."""
        ...

    def merge(
        self,
        surviving_party_id: str,
        merged_party_id: str,
        reason: str,
        merged_by: str | None,
        snapshot: str,
    ) -> str:
        """Execute the full merge transaction:
        1. Re-point identities from merged_party_id → surviving_party_id (skip UNIQUE conflicts).
        2. Set merged party is_merged=True, merged_into=surviving_party_id.
        3. Insert a crm_party_merge_log row with a JSON snapshot.
        Returns the new merge_id."""
        ...

    def undo_merge(self, merge_id: str) -> None:
        """Restore party flags and identities from the JSON snapshot stored in
        crm_party_merge_log, then mark the log row as undone."""
        ...

    def get_merge_log(self, merge_id: str) -> MergeLog | None:
        """Retrieve a merge log entry by ID, or None if not found."""
        ...

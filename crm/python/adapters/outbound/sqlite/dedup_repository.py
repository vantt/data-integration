"""SQLite adapter: DedupRepository.

Implements domain.ports.DedupRepository using parameterised sqlite3 queries.
SQL constants and row mappers live in dedup_repository_queries.py.
merge() and undo_merge() run as atomic transactions.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Optional

from domain.entities.party import DedupCandidate, MergeLog
from adapters.outbound.sqlite.dedup_repository_queries import (
    SQL_INSERT_CANDIDATE,
    SQL_CANDIDATE_EXISTS,
    SQL_LIST_CANDIDATES_BY_STATUS,
    SQL_LIST_ALL_CANDIDATES,
    SQL_GET_CANDIDATE,
    SQL_UPDATE_CANDIDATE_STATUS,
    SQL_LIST_IDENTITY_IDS_BY_PARTY,
    SQL_REASSIGN_IDENTITY,
    SQL_MARK_MERGED_PARTY,
    SQL_INSERT_MERGE_LOG,
    SQL_GET_MERGE_LOG,
    SQL_RESTORE_MERGED_PARTY_FLAGS,
    SQL_STAMP_UNDONE_AT,
    row_to_candidate,
    row_to_merge_log,
)


class SQLiteDedupRepository:
    """DedupRepository backed by crm.db via a sqlite3.Connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ── Candidate CRUD ────────────────────────────────────────────────────────

    def insert_candidate(self, candidate: DedupCandidate) -> None:
        self._conn.execute(SQL_INSERT_CANDIDATE, (
            candidate.candidate_id,
            candidate.party_a,
            candidate.party_b,
            candidate.match_rule,
            candidate.match_score,
            candidate.status,
            candidate.created_at,
        ))

    def candidate_exists(self, party_a: str, party_b: str) -> bool:
        """True if a 'pending' candidate exists for the pair (order-independent)."""
        row = self._conn.execute(
            SQL_CANDIDATE_EXISTS, (party_a, party_b, party_b, party_a)
        ).fetchone()
        return bool(row and row[0] > 0)

    def list_candidates(self, status: str) -> list[DedupCandidate]:
        if status:
            rows = self._conn.execute(SQL_LIST_CANDIDATES_BY_STATUS, (status,)).fetchall()
        else:
            rows = self._conn.execute(SQL_LIST_ALL_CANDIDATES).fetchall()
        return [row_to_candidate(r) for r in rows]

    def get_candidate(self, candidate_id: str) -> Optional[DedupCandidate]:
        row = self._conn.execute(SQL_GET_CANDIDATE, (candidate_id,)).fetchone()
        return row_to_candidate(row) if row else None

    def update_candidate_status(
        self, candidate_id: str, status: str, reviewed_by: Optional[str]
    ) -> None:
        self._conn.execute(SQL_UPDATE_CANDIDATE_STATUS, (status, reviewed_by, candidate_id))

    # ── Merge transaction ─────────────────────────────────────────────────────

    def merge(
        self,
        surviving_party_id: str,
        merged_party_id: str,
        reason: str,
        merged_by: Optional[str],
        snapshot: str,
    ) -> str:
        """Atomic merge:
        1. Reassign all identities of merged_party_id → surviving_party_id.
        2. Set merged party is_merged=1, merged_into=surviving_party_id.
        3. Insert crm_party_merge_log with caller-supplied JSON snapshot.
        Returns new merge_id.
        """
        merge_id = str(uuid.uuid4())
        with self._conn:
            id_rows = self._conn.execute(
                SQL_LIST_IDENTITY_IDS_BY_PARTY, (merged_party_id,)
            ).fetchall()
            for id_row in id_rows:
                self._conn.execute(
                    SQL_REASSIGN_IDENTITY, (surviving_party_id, id_row["identity_id"])
                )
            self._conn.execute(SQL_MARK_MERGED_PARTY, (surviving_party_id, merged_party_id))
            self._conn.execute(SQL_INSERT_MERGE_LOG, (
                merge_id,
                surviving_party_id,
                merged_party_id,
                reason or None,
                merged_by,
                snapshot or None,
            ))
        return merge_id

    # ── Undo merge transaction ────────────────────────────────────────────────

    def undo_merge(self, merge_id: str) -> None:
        """Restore party flags and identities from the JSON snapshot in the merge log.

        Raises ValueError on double-undo or missing snapshot.
        """
        log_row = self._conn.execute(SQL_GET_MERGE_LOG, (merge_id,)).fetchone()
        if log_row is None:
            raise ValueError(f"dedup repo: merge log {merge_id!r} not found")
        if log_row["undone_at"] is not None:
            raise ValueError(f"merge {merge_id!r} already undone")
        if not log_row["snapshot"]:
            raise ValueError(f"dedup repo: merge {merge_id!r} has no snapshot — cannot undo")

        snap = json.loads(log_row["snapshot"])
        reassigned_ids: list[str] = snap.get("reassigned_identity_ids", [])
        was_merged: bool = snap.get("merged_party_is_merged", False)
        was_merged_into: Optional[str] = snap.get("merged_party_merged_into")
        merged_party_id: str = log_row["merged_party_id"]

        with self._conn:
            for identity_id in reassigned_ids:
                self._conn.execute(SQL_REASSIGN_IDENTITY, (merged_party_id, identity_id))
            self._conn.execute(SQL_RESTORE_MERGED_PARTY_FLAGS, (
                1 if was_merged else 0, was_merged_into, merged_party_id
            ))
            self._conn.execute(SQL_STAMP_UNDONE_AT, (merge_id,))

    # ── Merge log ─────────────────────────────────────────────────────────────

    def get_merge_log(self, merge_id: str) -> Optional[MergeLog]:
        row = self._conn.execute(SQL_GET_MERGE_LOG, (merge_id,)).fetchone()
        return row_to_merge_log(row) if row else None

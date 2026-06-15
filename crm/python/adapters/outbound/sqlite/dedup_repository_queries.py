"""SQL constants and row-mapper helpers for SQLiteDedupRepository.

Kept separate to hold dedup_repository.py under 200 lines.
All SQL uses ? placeholders — no f-string interpolation of user data.
"""
from __future__ import annotations

import sqlite3

from domain.entities.party import DedupCandidate, MergeLog

# ── SQL strings ───────────────────────────────────────────────────────────────

SQL_INSERT_CANDIDATE = (
    "INSERT INTO crm_dedup_candidate"
    " (candidate_id, party_a, party_b, match_rule, match_score, status, created_at)"
    " VALUES (?, ?, ?, ?, ?, ?, ?)"
)

SQL_CANDIDATE_EXISTS = (
    "SELECT COUNT(*) FROM crm_dedup_candidate"
    " WHERE status = 'pending'"
    "   AND ((party_a = ? AND party_b = ?) OR (party_a = ? AND party_b = ?))"
)

SQL_LIST_CANDIDATES_BY_STATUS = (
    "SELECT candidate_id, party_a, party_b, match_rule, match_score,"
    "       status, reviewed_by, reviewed_at, created_at"
    " FROM crm_dedup_candidate WHERE status = ?"
    " ORDER BY match_score DESC, created_at"
)

SQL_LIST_ALL_CANDIDATES = (
    "SELECT candidate_id, party_a, party_b, match_rule, match_score,"
    "       status, reviewed_by, reviewed_at, created_at"
    " FROM crm_dedup_candidate"
    " ORDER BY match_score DESC, created_at"
)

SQL_GET_CANDIDATE = (
    "SELECT candidate_id, party_a, party_b, match_rule, match_score,"
    "       status, reviewed_by, reviewed_at, created_at"
    " FROM crm_dedup_candidate WHERE candidate_id = ? LIMIT 1"
)

SQL_UPDATE_CANDIDATE_STATUS = (
    "UPDATE crm_dedup_candidate"
    " SET status = ?, reviewed_by = ?,"
    "     reviewed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
    " WHERE candidate_id = ?"
)

SQL_LIST_IDENTITY_IDS_BY_PARTY = (
    "SELECT identity_id FROM crm_party_identity WHERE party_id = ?"
)

SQL_REASSIGN_IDENTITY = (
    "UPDATE crm_party_identity SET party_id = ? WHERE identity_id = ?"
)

SQL_MARK_MERGED_PARTY = (
    "UPDATE crm_party SET is_merged = 1, merged_into = ? WHERE party_id = ?"
)

SQL_INSERT_MERGE_LOG = (
    "INSERT INTO crm_party_merge_log"
    " (merge_id, surviving_party_id, merged_party_id, reason, merged_by, snapshot, merged_at)"
    " VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"
)

SQL_GET_MERGE_LOG = (
    "SELECT merge_id, surviving_party_id, merged_party_id,"
    "       reason, merged_by, snapshot, merged_at, undone_at"
    " FROM crm_party_merge_log WHERE merge_id = ? LIMIT 1"
)

SQL_RESTORE_MERGED_PARTY_FLAGS = (
    "UPDATE crm_party SET is_merged = ?, merged_into = ? WHERE party_id = ?"
)

SQL_STAMP_UNDONE_AT = (
    "UPDATE crm_party_merge_log"
    " SET undone_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
    " WHERE merge_id = ?"
)

# ── Row mappers ───────────────────────────────────────────────────────────────

def row_to_candidate(row: sqlite3.Row) -> DedupCandidate:
    return DedupCandidate(
        candidate_id=row["candidate_id"],
        party_a=row["party_a"],
        party_b=row["party_b"],
        match_rule=row["match_rule"],
        match_score=row["match_score"],
        status=row["status"],
        reviewed_by=row["reviewed_by"],
        reviewed_at=row["reviewed_at"],
        created_at=row["created_at"],
    )


def row_to_merge_log(row: sqlite3.Row) -> MergeLog:
    return MergeLog(
        merge_id=row["merge_id"],
        surviving_party_id=row["surviving_party_id"],
        merged_party_id=row["merged_party_id"],
        reason=row["reason"] or "",
        merged_by=row["merged_by"],
        snapshot=row["snapshot"] or "",
        merged_at=row["merged_at"],
        undone_at=row["undone_at"],
    )

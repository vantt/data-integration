"""SQL constants and row-mapper helpers for SQLitePartyRepository.

Kept separate to hold party_repository.py under 200 lines.
All SQL uses ? placeholders — no f-string interpolation of user data.
"""
from __future__ import annotations

import sqlite3

from domain.entities.party import Party, PartyIdentity

# ── SQL strings ───────────────────────────────────────────────────────────────

SQL_FIND_BY_IDENTITY = (
    "SELECT p.party_id, p.party_type, p.display_name, p.primary_phone, p.primary_email,"
    "       p.status, p.is_merged, p.merged_into, p.created_at, p.updated_at"
    " FROM crm_party p"
    " JOIN crm_party_identity i ON i.party_id = p.party_id"
    " WHERE i.identity_type = ? AND i.identity_value = ?"
    " LIMIT 1"
)

SQL_CREATE_PARTY = (
    "INSERT INTO crm_party"
    " (party_id, party_type, display_name, primary_phone, primary_email,"
    "  status, is_merged, merged_into, created_at, updated_at)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

SQL_GET_PARTY_BY_ID = (
    "SELECT party_id, party_type, display_name, primary_phone, primary_email,"
    "       status, is_merged, merged_into, created_at, updated_at"
    " FROM crm_party WHERE party_id = ? LIMIT 1"
)

SQL_UPDATE_PARTY = (
    "UPDATE crm_party"
    " SET display_name = ?, primary_phone = ?, primary_email = ?,"
    "     status = ?, is_merged = ?, merged_into = ?"
    " WHERE party_id = ?"
)

SQL_LIST_BY_PHONE = (
    "SELECT party_id, party_type, display_name, primary_phone, primary_email,"
    "       status, is_merged, merged_into, created_at, updated_at"
    " FROM crm_party WHERE primary_phone = ? AND is_merged = 0"
)

SQL_LIST_BY_EMAIL = (
    "SELECT party_id, party_type, display_name, primary_phone, primary_email,"
    "       status, is_merged, merged_into, created_at, updated_at"
    " FROM crm_party WHERE primary_email = ? AND is_merged = 0"
)

SQL_FTS_SEARCH = (
    "SELECT party_id FROM crm_party_fts"
    " WHERE crm_party_fts MATCH ?"
    " ORDER BY rank LIMIT 50"
)

SQL_UPSERT_IDENTITY = (
    "INSERT OR IGNORE INTO crm_party_identity"
    " (identity_id, party_id, source_system, identity_type, identity_value,"
    "  confidence, is_primary, verified_at, source_contact_quality, contact_quality, created_at)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)

SQL_LIST_IDENTITIES = (
    "SELECT identity_id, party_id, source_system, identity_type, identity_value,"
    "       confidence, is_primary, verified_at, source_contact_quality, contact_quality, created_at"
    " FROM crm_party_identity WHERE party_id = ?"
    " ORDER BY is_primary DESC, created_at"
)

SQL_UPDATE_CONTACT_QUALITY = (
    "UPDATE crm_party_identity SET contact_quality = ? WHERE identity_id = ?"
)

# ── Row mappers ───────────────────────────────────────────────────────────────

def row_to_party(row: sqlite3.Row) -> Party:
    return Party(
        party_id=row["party_id"],
        party_type=row["party_type"],
        display_name=row["display_name"] or "",
        primary_phone=row["primary_phone"] or "",
        primary_email=row["primary_email"] or "",
        status=row["status"],
        is_merged=bool(row["is_merged"]),
        merged_into=row["merged_into"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_identity(row: sqlite3.Row) -> PartyIdentity:
    return PartyIdentity(
        identity_id=row["identity_id"],
        party_id=row["party_id"],
        source_system=row["source_system"],
        identity_type=row["identity_type"],
        identity_value=row["identity_value"],
        confidence=row["confidence"],
        is_primary=bool(row["is_primary"]),
        verified_at=row["verified_at"],
        source_contact_quality=row["source_contact_quality"],
        contact_quality=row["contact_quality"],
        created_at=row["created_at"],
    )


def party_create_params(party: Party) -> tuple:
    return (
        party.party_id,
        party.party_type,
        party.display_name or None,
        party.primary_phone or None,
        party.primary_email or None,
        party.status,
        1 if party.is_merged else 0,
        party.merged_into,
        party.created_at,
        party.updated_at,
    )


def party_update_params(party: Party) -> tuple:
    return (
        party.display_name or None,
        party.primary_phone or None,
        party.primary_email or None,
        party.status,
        1 if party.is_merged else 0,
        party.merged_into,
        party.party_id,
    )


def identity_upsert_params(identity: PartyIdentity) -> tuple:
    return (
        identity.identity_id,
        identity.party_id,
        identity.source_system,
        identity.identity_type,
        identity.identity_value,
        identity.confidence,
        1 if identity.is_primary else 0,
        identity.verified_at,
        identity.source_contact_quality,
        identity.contact_quality,
        identity.created_at,
    )

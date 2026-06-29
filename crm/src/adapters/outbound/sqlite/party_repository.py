"""SQLite adapter: PartyRepository.

Implements domain.ports.PartyRepository using parameterised sqlite3 queries.
SQL constants and row mappers live in party_repository_queries.py.
No f-strings for SQL values — all user data goes through ? placeholders.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from domain.entities.party import Party, PartyIdentity
from adapters.outbound.sqlite.party_repository_queries import (
    SQL_FIND_BY_IDENTITY,
    SQL_CREATE_PARTY,
    SQL_GET_PARTY_BY_ID,
    SQL_UPDATE_PARTY,
    SQL_LIST_BY_PHONE,
    SQL_LIST_BY_EMAIL,
    SQL_FTS_SEARCH,
    SQL_UNIFIED_SEARCH,
    SQL_UPSERT_IDENTITY,
    SQL_LIST_IDENTITIES,
    SQL_UPDATE_CONTACT_QUALITY,
    SQL_LIST_ALL_PARTIES,
    SQL_COUNT_PARTIES,
    SQL_UPDATE_PARTY_ADDRESS,
    SQL_DEACTIVATE_IDENTITY,
    SQL_INSERT_IDENTITY_FULL,
    SQL_UPDATE_IDENTITY_INFO,
    row_to_party,
    row_to_identity,
    party_create_params,
    party_update_params,
    identity_upsert_params,
    identity_insert_full_params,
)


def _fts_quote(s: str) -> str:
    """Wrap s as a quoted FTS5 phrase; escape internal double-quotes by doubling them."""
    return '"' + s.replace('"', '""') + '"'


class SQLitePartyRepository:
    """PartyRepository backed by crm.db via a sqlite3.Connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ── Party CRUD ────────────────────────────────────────────────────────────

    def find_by_identity(self, identity_type: str, identity_value: str) -> Optional[Party]:
        row = self._conn.execute(SQL_FIND_BY_IDENTITY, (identity_type, identity_value)).fetchone()
        return row_to_party(row) if row else None

    def create(self, party: Party) -> Party:
        self._conn.execute(SQL_CREATE_PARTY, party_create_params(party))
        return party

    def get_by_id(self, party_id: str) -> Optional[Party]:
        row = self._conn.execute(SQL_GET_PARTY_BY_ID, (party_id,)).fetchone()
        return row_to_party(row) if row else None

    def update(self, party: Party) -> None:
        self._conn.execute(SQL_UPDATE_PARTY, party_update_params(party))
        self._conn.commit()

    def list_by_phone(self, phone: str) -> list[Party]:
        rows = self._conn.execute(SQL_LIST_BY_PHONE, (phone or None,)).fetchall()
        return [row_to_party(r) for r in rows]

    def list_all(self, offset: int, limit: int) -> tuple[list[Party], int]:
        total = self._conn.execute(SQL_COUNT_PARTIES).fetchone()[0]
        rows = self._conn.execute(SQL_LIST_ALL_PARTIES, (limit, offset)).fetchall()
        return [row_to_party(r) for r in rows], total

    def get_sapo_ids_for_parties(self, party_ids: list[str]) -> dict[str, int]:
        """Return {party_id: sapo_customer_id} for parties with a sapo_customer identity."""
        if not party_ids:
            return {}
        placeholders = ",".join("?" * len(party_ids))
        sql = (
            f"SELECT party_id, MIN(CAST(identity_value AS INTEGER)) AS customer_id"
            f" FROM crm_party_identity"
            f" WHERE identity_type = 'sapo_customer'"
            f" AND party_id IN ({placeholders})"
            f" GROUP BY party_id"
        )
        rows = self._conn.execute(sql, party_ids).fetchall()
        return {row[0]: row[1] for row in rows if row[1] is not None}

    def list_by_email(self, email: str) -> list[Party]:
        rows = self._conn.execute(SQL_LIST_BY_EMAIL, (email or None,)).fetchall()
        return [row_to_party(r) for r in rows]

    def search_by_name(self, query: str) -> list[str]:
        """FTS5 MATCH on crm_party_fts; returns party_ids ordered by rank."""
        if not query:
            return []
        rows = self._conn.execute(SQL_FTS_SEARCH, (_fts_quote(query),)).fetchall()
        return [r["party_id"] for r in rows]

    def search_unified(self, fts_query: str) -> list[str]:
        """FTS5 MATCH on crm_party_search; returns party_ids ordered by rank."""
        if not fts_query:
            return []
        cur = self._conn.execute(SQL_UNIFIED_SEARCH, (fts_query,))
        return [row[0] for row in cur.fetchall()]

    # ── Identity operations ───────────────────────────────────────────────────

    def upsert_identity(self, identity: PartyIdentity) -> None:
        self._conn.execute(SQL_UPSERT_IDENTITY, identity_upsert_params(identity))
        self._conn.commit()

    def list_identities(self, party_id: str) -> list[PartyIdentity]:
        rows = self._conn.execute(SQL_LIST_IDENTITIES, (party_id,)).fetchall()
        return [row_to_identity(r) for r in rows]

    def update_contact_quality(self, identity_id: str, contact_quality: str) -> None:
        self._conn.execute(SQL_UPDATE_CONTACT_QUALITY, (contact_quality, identity_id))
        self._conn.commit()

    def update_party_address(
        self,
        party_id: str,
        address_line: Optional[str],
        ward: Optional[str],
        district: Optional[str],
        province: Optional[str],
        address_note: Optional[str],
        updated_at: str,
    ) -> None:
        """Update address fields on crm_party (sets address_source='manual')."""
        self._conn.execute(
            SQL_UPDATE_PARTY_ADDRESS,
            (address_line or None, ward or None, district or None, province or None,
             address_note or None, updated_at, party_id),
        )
        self._conn.commit()

    def deactivate_identity(self, identity_id: str) -> None:
        """Mark an identity as invalid (contact_status='invalid')."""
        self._conn.execute(SQL_DEACTIVATE_IDENTITY, (identity_id,))
        self._conn.commit()

    def insert_identity_full(self, identity: PartyIdentity) -> None:
        """Insert a new identity with all migration 0008 fields. INSERT OR IGNORE on duplicate."""
        self._conn.execute(SQL_INSERT_IDENTITY_FULL, identity_insert_full_params(identity))
        self._conn.commit()

    def update_identity_info(
        self,
        identity_id: str,
        display_label: Optional[str],
        contact_status: str,
        is_preferred: bool,
    ) -> None:
        """Update display_label, contact_status, is_preferred on an existing identity."""
        self._conn.execute(
            SQL_UPDATE_IDENTITY_INFO,
            (display_label or None, contact_status or "active", 1 if is_preferred else 0, identity_id),
        )
        self._conn.commit()

    def create_with_identities(self, party: Party, identities: list[PartyIdentity]) -> Party:
        """Atomic insert: party row + all identity rows. Rolls back on any failure."""
        with self._conn:
            self.create(party)
            for identity in identities:
                # Call execute directly — upsert_identity() commits mid-transaction which breaks atomicity.
                self._conn.execute(SQL_UPSERT_IDENTITY, identity_upsert_params(identity))
        return party

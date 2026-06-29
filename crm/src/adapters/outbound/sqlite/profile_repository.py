"""SQLite adapter for CustomerProfile and Party360.

Implements ports.ProfileRepository using raw sqlite3 queries
ported from profile_queries.sql (Go sqlc source).
"""
from __future__ import annotations

import json
import sqlite3
from typing import Optional

from adapters.outbound.sqlite.connection import CRMDatabase
from domain.entities.profile import CustomerProfile, Party360, PartyTag


# ---------------------------------------------------------------------------
# Row → entity helpers
# ---------------------------------------------------------------------------

def _row_to_profile(row: sqlite3.Row) -> CustomerProfile:
    custom_raw = row["custom"]
    if isinstance(custom_raw, str) and custom_raw:
        try:
            custom = json.loads(custom_raw)
        except json.JSONDecodeError:
            custom = {}
    else:
        custom = {}

    address_raw = row["address"]
    if isinstance(address_raw, str) and address_raw:
        try:
            address = json.loads(address_raw)
        except json.JSONDecodeError:
            address = None
    else:
        address = None

    prefs_raw = row["preferences"]
    if isinstance(prefs_raw, str) and prefs_raw:
        try:
            preferences = json.loads(prefs_raw)
        except json.JSONDecodeError:
            preferences = None
    else:
        preferences = None

    return CustomerProfile(
        party_id=row["party_id"],
        owner_user_id=row["owner_user_id"],
        lifecycle_stage=row["lifecycle_stage"],
        acquisition_source=row["acquisition_source"],
        birthday=row["birthday"],
        address=address,
        preferences=preferences,
        custom=custom,
        consent_contact=row["consent_contact"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _parse_tags_json(tags_json: Optional[str], party_id: str) -> list[PartyTag]:
    if not tags_json:
        return []
    try:
        items = json.loads(tags_json)
    except (json.JSONDecodeError, TypeError):
        return []
    return [
        PartyTag(
            party_id=party_id,
            tag_id=t["tag_id"],
            name=t.get("name", ""),
            tagged_at="",
            category=t.get("category"),
            color=t.get("color"),
            display_label=t.get("display_label"),
        )
        for t in items
        if isinstance(t, dict) and t.get("tag_id")
    ]


def _row_to_party360(row: sqlite3.Row) -> Party360:
    keys = row.keys()
    return Party360(
        party_id=row["party_id"],
        party_type=row["party_type"],
        display_name=row["display_name"] or "",
        primary_phone=row["primary_phone"] or "",
        primary_email=row["primary_email"] or "",
        status=row["status"],
        is_merged=bool(row["is_merged"]),
        party_created_at=row["party_created_at"],
        party_updated_at=row["party_updated_at"],
        owner_user_id=row["owner_user_id"],
        lifecycle_stage=row["lifecycle_stage"],
        acquisition_source=row["acquisition_source"],
        birthday=row["birthday"],
        gender=row["gender"] if "gender" in keys else None,
        address=row["address"],
        preferences=row["preferences"],
        custom=row["custom"] or "",
        consent_contact=row["consent_contact"],
        profile_updated_at=row["profile_updated_at"] or "",
        address_line=row["address_line"] if "address_line" in keys else None,
        ward=row["ward"] if "ward" in keys else None,
        district=row["district"] if "district" in keys else None,
        province=row["province"] if "province" in keys else None,
        address_source=row["address_source"] if "address_source" in keys else "sapo_sync",
        address_note=row["address_note"] if "address_note" in keys else None,
        tags=_parse_tags_json(row["tags_json"] if "tags_json" in keys else None, row["party_id"]),
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class SQLiteProfileRepository:
    """Implements ProfileRepository port against crm.db."""

    def __init__(self, db: CRMDatabase) -> None:
        self._db = db

    # ── Queries (ported from profile_queries.sql) ─────────────────────────────

    _SQL_GET = """
        SELECT party_id, owner_user_id, lifecycle_stage, acquisition_source,
               birthday, address, preferences, custom,
               consent_enum AS consent_contact,
               created_at, updated_at
        FROM crm_customer_profile
        WHERE party_id = ?
        LIMIT 1
    """

    _SQL_UPSERT = """
        INSERT INTO crm_customer_profile (
          party_id, owner_user_id, lifecycle_stage, acquisition_source,
          birthday, gender, address, preferences, custom, consent_enum,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (party_id) DO UPDATE SET
          owner_user_id      = excluded.owner_user_id,
          lifecycle_stage    = excluded.lifecycle_stage,
          acquisition_source = excluded.acquisition_source,
          birthday           = excluded.birthday,
          gender             = excluded.gender,
          address            = excluded.address,
          preferences        = excluded.preferences,
          custom             = excluded.custom,
          consent_enum       = excluded.consent_enum,
          updated_at         = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    """

    _SQL_UPDATE_CUSTOM = """
        UPDATE crm_customer_profile
        SET custom     = ?,
            updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        WHERE party_id = ?
    """

    _SQL_GET_360 = """
        SELECT
          party_id, party_type, display_name, primary_phone, primary_email,
          status, is_merged, party_created_at, party_updated_at,
          owner_user_id, lifecycle_stage, acquisition_source, birthday, gender,
          address, preferences, custom, consent_contact, profile_updated_at,
          address_line, ward, district, province, address_source, address_note,
          tags_json
        FROM crm_party_360
        WHERE party_id = ?
        LIMIT 1
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def get_profile(self, party_id: str) -> Optional[CustomerProfile]:
        row = self._db.conn.execute(self._SQL_GET, (party_id,)).fetchone()
        if row is None:
            return None
        return _row_to_profile(row)

    def upsert_profile(self, profile: CustomerProfile) -> None:
        """INSERT OR UPDATE — maps Python types to SQLite column values."""
        address_json = json.dumps(profile.address) if profile.address else None
        prefs_json = json.dumps(profile.preferences) if profile.preferences else None
        custom_json = json.dumps(profile.custom) if profile.custom else "{}"
        self._db.conn.execute(self._SQL_UPSERT, (
            profile.party_id,
            profile.owner_user_id,
            profile.lifecycle_stage,
            profile.acquisition_source,
            profile.birthday,
            profile.gender,
            address_json,
            prefs_json,
            custom_json,
            profile.consent_contact,
            profile.created_at,
            profile.updated_at,
        ))

    def update_custom_json(self, party_id: str, custom_json: str) -> None:
        """Replace the custom column; caller is responsible for merging values."""
        self._db.conn.execute(self._SQL_UPDATE_CUSTOM, (custom_json, party_id))

    def get_party360(self, party_id: str) -> Optional[Party360]:
        row = self._db.conn.execute(self._SQL_GET_360, (party_id,)).fetchone()
        if row is None:
            return None
        return _row_to_party360(row)

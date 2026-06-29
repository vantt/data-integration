"""SQLite adapter for CustomFieldDef.

Implements ports.CustomFieldRepository using raw sqlite3 queries
ported from the custom field sections of tag_queries.sql (Go sqlc source).
"""
from __future__ import annotations

import json
import sqlite3
from typing import Optional

from adapters.outbound.sqlite.connection import CRMDatabase
from domain.entities.profile import CustomFieldDef


# ---------------------------------------------------------------------------
# Row → entity helper
# ---------------------------------------------------------------------------

def _row_to_def(row: sqlite3.Row) -> CustomFieldDef:
    options_raw = row["options"]
    if isinstance(options_raw, str) and options_raw:
        try:
            options = json.loads(options_raw)
        except json.JSONDecodeError:
            options = None
    else:
        options = None

    return CustomFieldDef(
        field_id=row["field_id"],
        entity_type=row["entity_type"],
        field_key=row["field_key"],
        label=row["label"],
        data_type=row["data_type"],
        options=options,
        is_required=bool(row["is_required"]),
        is_active=bool(row["is_active"]),
        sort_order=int(row["sort_order"]),
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class SQLiteCustomFieldRepository:
    """Implements CustomFieldRepository port against crm.db."""

    def __init__(self, db: CRMDatabase) -> None:
        self._db = db

    # ── SQL (ported from tag_queries.sql custom field sections) ───────────────

    _SQL_LIST_ACTIVE = """
        SELECT field_id, entity_type, field_key, label, data_type,
               options, is_required, is_active, sort_order
        FROM crm_custom_field_def
        WHERE is_active = 1
        ORDER BY sort_order, field_key
    """

    _SQL_LIST_ACTIVE_BY_TYPE = """
        SELECT field_id, entity_type, field_key, label, data_type,
               options, is_required, is_active, sort_order
        FROM crm_custom_field_def
        WHERE entity_type = ? AND is_active = 1
        ORDER BY sort_order, field_key
    """

    _SQL_LIST_ALL_BY_TYPE = """
        SELECT field_id, entity_type, field_key, label, data_type,
               options, is_required, is_active, sort_order
        FROM crm_custom_field_def
        WHERE entity_type = ?
        ORDER BY sort_order, field_key
    """

    _SQL_GET = """
        SELECT field_id, entity_type, field_key, label, data_type,
               options, is_required, is_active, sort_order
        FROM crm_custom_field_def
        WHERE field_id = ?
        LIMIT 1
    """

    _SQL_INSERT = """
        INSERT INTO crm_custom_field_def (
          field_id, entity_type, field_key, label, data_type,
          options, is_required, is_active, sort_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    _SQL_UPDATE = """
        UPDATE crm_custom_field_def
        SET label       = ?,
            options     = ?,
            is_required = ?,
            is_active   = ?,
            sort_order  = ?
        WHERE field_id = ?
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def list_active_defs(self, entity_type: Optional[str] = None) -> list[CustomFieldDef]:
        """Return all active custom field definitions, optionally filtered by entity_type."""
        if entity_type:
            rows = self._db.conn.execute(self._SQL_LIST_ACTIVE_BY_TYPE, (entity_type,)).fetchall()
        else:
            rows = self._db.conn.execute(self._SQL_LIST_ACTIVE).fetchall()
        return [_row_to_def(r) for r in rows]

    def list_all_defs(self, entity_type: str) -> list[CustomFieldDef]:
        """Return active + inactive defs for entity_type."""
        rows = self._db.conn.execute(self._SQL_LIST_ALL_BY_TYPE, (entity_type,)).fetchall()
        return [_row_to_def(r) for r in rows]

    def get_def(self, field_id: str) -> Optional[CustomFieldDef]:
        row = self._db.conn.execute(self._SQL_GET, (field_id,)).fetchone()
        return _row_to_def(row) if row else None

    def create_def(self, defn: CustomFieldDef) -> CustomFieldDef:
        """Insert a new definition; returns the same object (no DB-generated fields)."""
        options_json = json.dumps(defn.options) if defn.options else None
        self._db.conn.execute(self._SQL_INSERT, (
            defn.field_id,
            defn.entity_type,
            defn.field_key,
            defn.label,
            defn.data_type,
            options_json,
            int(defn.is_required),
            int(defn.is_active),
            defn.sort_order,
        ))
        return defn

    def update_def(self, field_id: str, **kwargs) -> None:
        """Patch label, options, is_required, is_active, sort_order on an existing def.

        Fetches current state then applies only the supplied keyword overrides
        so callers don't need to hold the full object.
        """
        current = self.get_def(field_id)
        if current is None:
            raise ValueError(f"custom_field_repository: field_id not found: {field_id}")

        label = kwargs.get("label", current.label)
        options = kwargs.get("options", current.options)
        is_required = kwargs.get("is_required", current.is_required)
        is_active = kwargs.get("is_active", current.is_active)
        sort_order = kwargs.get("sort_order", current.sort_order)

        options_json = json.dumps(options) if options else None
        self._db.conn.execute(self._SQL_UPDATE, (
            label,
            options_json,
            int(is_required),
            int(is_active),
            sort_order,
            field_id,
        ))

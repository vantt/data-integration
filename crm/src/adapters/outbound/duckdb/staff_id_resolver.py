"""staff_id_resolver.py — resolve Sapo staff_id (account_id) from email via dim_staff.

Used at user provisioning time to auto-populate crm_app_user.staff_id.
Fails silently (returns None) when olap.duckdb is unavailable or dim_staff is absent.
"""
from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)

_SQL = "SELECT staff_id FROM main_marts.dim_staff WHERE lower(trim(email)) = lower(trim(?)) LIMIT 1"


class StaffIdResolver:
    """Lookup Sapo account_id from warehouse dim_staff by normalized email."""

    def __init__(self, olap_path: str) -> None:
        self._olap_path = olap_path

    def resolve(self, email: str) -> Optional[int]:
        """Return Sapo staff_id for email, or None if not found / warehouse unavailable."""
        if not email or not self._olap_path:
            return None
        try:
            from adapters.outbound.duckdb.connection import open_olap
            conn = open_olap(self._olap_path)
            if conn is None:
                return None
            try:
                row = conn.execute(_SQL, [email]).fetchone()
                return int(row[0]) if row and row[0] is not None else None
            finally:
                conn.close()
        except Exception as exc:
            log.debug("staff_id_resolver: email=%r: %s", email, exc)
            return None

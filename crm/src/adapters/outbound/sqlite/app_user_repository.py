"""app_user_repository.py — SQLiteAppUserRepository: adapter for crm_app_user table.

Ports app_user_queries.sql + AppUserRepo (Go) to Python.
Operates on the main crm.db connection (no cache.* prefix needed).
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from domain.entities.app_user import AppUser


class SQLiteAppUserRepository:
    """SQLite adapter for crm_app_user persistence and lookup."""

    _SELECT = (
        "SELECT user_id, email, full_name, role, is_active, created_at, updated_at, lark_user_id "
        "FROM crm_app_user"
    )

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_by_id(self, user_id: str) -> Optional[AppUser]:
        """Return the AppUser with the given UUID, or None if not found."""
        sql = f"{self._SELECT} WHERE user_id = ? LIMIT 1"
        row = self._conn.execute(sql, (user_id,)).fetchone()
        return _row_to_user(row) if row else None

    def get_by_email(self, email: str) -> Optional[AppUser]:
        """Return the AppUser with the given email, or None if not found."""
        sql = f"{self._SELECT} WHERE email = ? LIMIT 1"
        row = self._conn.execute(sql, (email,)).fetchone()
        return _row_to_user(row) if row else None

    def list_users(self, is_active: Optional[bool] = None) -> list[AppUser]:
        """Return all users, optionally filtered by is_active, ordered by full_name."""
        if is_active is None:
            sql = f"{self._SELECT} ORDER BY full_name"
            rows = self._conn.execute(sql).fetchall()
        else:
            sql = f"{self._SELECT} WHERE is_active = ? ORDER BY full_name"
            rows = self._conn.execute(sql, (1 if is_active else 0,)).fetchall()
        return [_row_to_user(r) for r in rows]

    # ── Convenience wrappers matching the port interface ──────────────────────

    def get_by_email_active(self, email: str) -> Optional[AppUser]:
        """Return active user by email only."""
        user = self.get_by_email(email)
        return user if user and user.is_active else None

    def list_active(self) -> list[AppUser]:
        """Return all active users ordered by full_name (port-compatible)."""
        return self.list_users(is_active=True)

    # ── Mutations ──────────────────────────────────────────────────────────────

    def create(self, user: AppUser) -> AppUser:
        """Insert a new AppUser row. Raises sqlite3.IntegrityError on duplicate email/id."""
        sql = (
            "INSERT INTO crm_app_user "
            "(user_id, email, full_name, role, is_active, created_at, updated_at, lark_user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )
        with self._conn:
            self._conn.execute(sql, (
                user.user_id,
                user.email,
                user.full_name,
                user.role,
                1 if user.is_active else 0,
                user.created_at,
                user.updated_at,
                user.lark_user_id,
            ))
        return user

    def update(self, user_id: str, **kwargs: object) -> None:
        """Update one or more columns on crm_app_user for the given user_id.

        Accepted kwargs: email, full_name, role, is_active, staff_id, updated_at.
        Raises ValueError when no valid kwargs are supplied.
        """
        # Hardcoded whitelist — only column names in this set are interpolated into SQL.
        # User-supplied values are always passed as query parameters (?), never interpolated.
        _ALLOWED = {"email", "full_name", "role", "is_active", "updated_at", "lark_user_id"}
        fields = {k: v for k, v in kwargs.items() if k in _ALLOWED}
        if not fields:
            raise ValueError(f"update() requires at least one of: {_ALLOWED}")

        # Coerce is_active bool → int for SQLite
        if "is_active" in fields:
            fields["is_active"] = 1 if fields["is_active"] else 0

        set_clause = ", ".join(f"{col} = ?" for col in fields)
        values = list(fields.values()) + [user_id]
        sql = f"UPDATE crm_app_user SET {set_clause} WHERE user_id = ?"
        with self._conn:
            self._conn.execute(sql, values)


# ── Row mapper ─────────────────────────────────────────────────────────────────

def _row_to_user(row: sqlite3.Row) -> AppUser:
    return AppUser(
        user_id=row["user_id"],
        email=row["email"],
        full_name=row["full_name"],
        role=row["role"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        lark_user_id=row["lark_user_id"],
    )

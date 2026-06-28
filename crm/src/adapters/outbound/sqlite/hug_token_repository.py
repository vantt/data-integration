"""hug_token_repository.py — OOP adapter wrapping hug.repository (functional module).

Thin wrapper that binds a sqlite3.Connection at construction and forwards all
calls to the pure-functional hug.repository module. The original module is
unchanged; this class exists to make the token store injectable via HugTokenPort.
"""
from __future__ import annotations

import sqlite3

import hug.repository as _repo


class HugTokenRepository:
    """OOP adapter for hug_token operations.

    Receives a sqlite3.Connection at construction and delegates to the
    functional hug.repository module for all data-access logic.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Mint operations
    # ------------------------------------------------------------------

    def mint_batch(
        self,
        count: int,
        *,
        batch_id: str,
        op_type: str = "package_insert",
    ) -> list[str]:
        """Generate `count` unique tokens as status='printed' and return them."""
        return _repo.mint_batch(self._conn, count, batch_id=batch_id, op_type=op_type)

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------

    def get_token(self, token: str) -> sqlite3.Row | None:
        """Return the hug_token row for `token`, or None."""
        return _repo.get_token(self._conn, token)

    def list_batch(self, batch_id: str) -> list[sqlite3.Row]:
        """Return all rows in a mint batch, ordered by creation."""
        return _repo.list_batch(self._conn, batch_id)

    def list_recent_batches(self, limit: int = 20) -> list[sqlite3.Row]:
        """Return recent batches with token counts (for the print picker)."""
        return _repo.list_recent_batches(self._conn, limit)

    def counts_by_status(self) -> dict[str, int]:
        """Return {status: count} across the whole master."""
        return _repo.counts_by_status(self._conn)

    # ------------------------------------------------------------------
    # Claim / push operations
    # ------------------------------------------------------------------

    def bind_token(
        self,
        token: str,
        *,
        order_code: str,
        is_gift: bool = False,
        channel: str | None = None,
        campaign_hint: str | None = None,
        bind_session_id: str | None = None,
        bind_attributes: dict | None = None,
    ) -> sqlite3.Row:
        """Bind a printed token to a Sapo order_code (claim). Returns the bound row."""
        return _repo.bind_token(
            self._conn,
            token,
            order_code=order_code,
            is_gift=is_gift,
            channel=channel,
            campaign_hint=campaign_hint,
            bind_session_id=bind_session_id,
            bind_attributes=bind_attributes,
        )

    def mark_pushed(self, token: str) -> None:
        """Record that a bound token has been pushed to the D1 edge cache."""
        _repo.mark_pushed(self._conn, token)

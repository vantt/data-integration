"""hug_voucher_repository_adapter.py — OOP adapter wrapping hug.voucher_repository.

Thin wrapper that binds a sqlite3.Connection at construction and forwards all
calls to the pure-functional hug.voucher_repository module. Named with the
_adapter suffix to avoid a naming conflict with the wrapped module.
"""
from __future__ import annotations

import sqlite3

import hug.voucher_repository as _repo


class HugVoucherRepositoryAdapter:
    """OOP adapter for crm_hug_voucher issuance ledger operations.

    Receives a sqlite3.Connection at construction and delegates to the
    functional hug.voucher_repository module for all data-access logic.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def record_issuance(
        self,
        *,
        code: str,
        customer_id: str,
        campaign_id: str,
        token: str | None = None,
        min_order: int | None = None,
        sku_guard: str | None = None,
        issued_at: str | None = None,
    ) -> bool:
        """Insert a voucher issuance row. Returns True if newly inserted."""
        return _repo.record_issuance(
            self._conn,
            code=code,
            customer_id=customer_id,
            campaign_id=campaign_id,
            token=token,
            min_order=min_order,
            sku_guard=sku_guard,
            issued_at=issued_at,
        )

    def mark_redeemed(
        self,
        *,
        code: str,
        customer_id: str,
        order_code: str,
        redeemed_at: str | None = None,
    ) -> bool:
        """Set redeemed_at and order_code. Returns True if the row was updated."""
        return _repo.mark_redeemed(
            self._conn,
            code=code,
            customer_id=customer_id,
            order_code=order_code,
            redeemed_at=redeemed_at,
        )

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_issuance(self, code: str, customer_id: str) -> sqlite3.Row | None:
        """Return the issuance row for (code, customer_id), or None if not found."""
        return _repo.get_issuance(self._conn, code, customer_id)

    def list_unredeemed(self, campaign_id: str | None = None) -> list[sqlite3.Row]:
        """Return all rows where redeemed_at IS NULL."""
        return _repo.list_unredeemed(self._conn, campaign_id)

    def attribution_rows(self, campaign_id: str | None = None) -> list[sqlite3.Row]:
        """Query v_hug_voucher_attribution for issued/redeemed counts."""
        return _repo.attribution_rows(self._conn, campaign_id)

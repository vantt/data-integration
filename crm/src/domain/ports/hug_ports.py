"""hug_ports.py — domain ports (Protocols) for the Hug subsystem.

Three ports mirror the three hug data-access modules:
  HugTokenPort    — hug_token mint/bind/push lifecycle
  HugCampaignPort — crm_hug_campaign CRUD + history
  HugVoucherPort  — crm_hug_voucher issuance ledger
"""
from __future__ import annotations

import sqlite3
from typing import Protocol


class HugTokenPort(Protocol):
    """Outbound port for hug_token operations (mint, bind, push)."""

    def mint_batch(
        self,
        count: int,
        *,
        batch_id: str,
        op_type: str = "package_insert",
    ) -> list[str]:
        """Generate `count` unique tokens as status='printed' and return them."""
        ...

    def get_token(self, token: str) -> sqlite3.Row | None:
        """Return the hug_token row for `token`, or None."""
        ...

    def list_batch(self, batch_id: str) -> list[sqlite3.Row]:
        """Return all rows in a mint batch, ordered by creation."""
        ...

    def list_recent_batches(self, limit: int = 20) -> list[sqlite3.Row]:
        """Return recent batches with token counts (for the print picker)."""
        ...

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
        ...

    def mark_pushed(self, token: str) -> None:
        """Record that a bound token has been pushed to the D1 edge cache."""
        ...

    def counts_by_status(self) -> dict[str, int]:
        """Return {status: count} across the whole master."""
        ...


class HugCampaignPort(Protocol):
    """Outbound port for crm_hug_campaign CRUD and history."""

    def list_campaigns(self, status: str | None = None) -> list[sqlite3.Row]:
        """Return campaigns ordered by priority ASC, optionally filtered by status."""
        ...

    def get_campaign(self, campaign_id: str) -> sqlite3.Row | None:
        """Return the campaign row for campaign_id, or None if not found."""
        ...

    def upsert_campaign(self, row: dict) -> sqlite3.Row:
        """Insert or replace a campaign row and write a history snapshot."""
        ...

    def archive_campaign(self, campaign_id: str) -> None:
        """Soft-delete a campaign by setting status='archived'."""
        ...

    def list_history(self, campaign_id: str, limit: int = 20) -> list[sqlite3.Row]:
        """Return the most recent history snapshots for a campaign, newest first."""
        ...

    def restore_snapshot(self, campaign_id: str, snapshot_id: int) -> sqlite3.Row:
        """Restore a campaign to a prior state captured in history."""
        ...

    def suggest_next_priority(self) -> int:
        """Return MAX(priority)+10 across active campaigns, or 10 if none exist."""
        ...

    def find_overlapping_campaigns(
        self,
        targeting: dict,
        exclude_id: str | None = None,
    ) -> list[dict]:
        """Return active campaigns whose targeting can overlap with `targeting`.

        Each entry is {campaign_id, name, priority}.
        exclude_id skips the campaign being edited (avoid self-overlap).
        """
        ...


class HugVoucherPort(Protocol):
    """Outbound port for crm_hug_voucher issuance ledger."""

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
        ...

    def mark_redeemed(
        self,
        *,
        code: str,
        customer_id: str,
        order_code: str,
        redeemed_at: str | None = None,
    ) -> bool:
        """Set redeemed_at and order_code. Returns True if updated."""
        ...

    def get_issuance(self, code: str, customer_id: str) -> sqlite3.Row | None:
        """Return the issuance row for (code, customer_id), or None."""
        ...

    def list_unredeemed(self, campaign_id: str | None = None) -> list[sqlite3.Row]:
        """Return all rows where redeemed_at IS NULL."""
        ...

    def attribution_rows(self, campaign_id: str | None = None) -> list[sqlite3.Row]:
        """Query v_hug_voucher_attribution for issued/redeemed counts."""
        ...

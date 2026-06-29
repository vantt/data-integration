"""Application service — Customer list query assembly.

Thin facade over the three repositories that screen_customer_list previously
received directly. Centralises the data-fetching boundary so business rules
(ownership filters, audit logging, etc.) can be added here without touching
the screen adapter layer.
"""
from __future__ import annotations

from typing import Optional, Protocol

from domain.entities.party import Party


# ── Internal port protocols ────────────────────────────────────────────────────


class _PartyPort(Protocol):
    def list_all(self, offset: int, limit: int) -> tuple[list[Party], int]: ...
    def search_unified(self, q: str) -> list[str]: ...
    def get_by_id(self, party_id: str) -> Optional[Party]: ...
    def find_by_identity(self, identity_type: str, identity_value: str) -> Optional[Party]: ...
    def get_sapo_ids_for_parties(self, party_ids: list[str]) -> dict[str, int]: ...


class _RFMPort(Protocol):
    def get_rfm_for_customer_ids(self, customer_ids: list[int]) -> dict[int, dict]: ...


class _TierPort(Protocol):
    def get_tiers_batch(self, customer_ids: list[int]) -> dict[int, str]: ...


# ── Service ────────────────────────────────────────────────────────────────────


class CustomerListQueryService:
    """Aggregates party, RFM, and tier data for the customer list screen.

    Business rules that apply to the customer list (e.g. ownership filters,
    audit logging) should be added here, not in the screen adapter.
    """

    def __init__(
        self,
        parties: _PartyPort,
        rfm_loader: Optional[_RFMPort] = None,
        tier_loader: Optional[_TierPort] = None,
    ) -> None:
        self._parties = parties
        self._rfm_loader = rfm_loader
        self._tier_loader = tier_loader

    def list_all(self, offset: int, limit: int) -> tuple[list[Party], int]:
        """Return a paginated party list and the total count."""
        return self._parties.list_all(offset, limit)

    def search_unified(self, q: str) -> list[str]:
        """Return party_ids matching the FTS query string."""
        return self._parties.search_unified(q)

    def get_by_id(self, party_id: str) -> Optional[Party]:
        """Return a party by primary key, or None."""
        return self._parties.get_by_id(party_id)

    def find_by_identity(
        self, identity_type: str, identity_value: str
    ) -> Optional[Party]:
        """Return the party that owns the given identity, or None."""
        return self._parties.find_by_identity(identity_type, identity_value)

    def get_sapo_ids_for_parties(self, party_ids: list[str]) -> dict[str, int]:
        """Return {party_id: sapo_customer_id} for the given party_ids."""
        return self._parties.get_sapo_ids_for_parties(party_ids)

    def get_rfm_for_customer_ids(self, customer_ids: list[int]) -> dict[int, dict]:
        """Return RFM data keyed by customer_id; empty dict when unavailable."""
        if self._rfm_loader is None:
            return {}
        return self._rfm_loader.get_rfm_for_customer_ids(customer_ids)

    def get_tiers_batch(self, customer_ids: list[int]) -> dict[int, str]:
        """Return strategic tier keyed by customer_id; empty dict when unavailable."""
        if self._tier_loader is None:
            return {}
        return self._tier_loader.get_tiers_batch(customer_ids)

"""HTTP adapter — Insight endpoint.

GET /api/parties/{id}/insight — returns CustomerInsight + ActionQueueItems.

Graceful-empty contract: when cache.db has no wh_* tables yet the endpoint
returns {"insight": null} with HTTP 200, not 500.
Auth: DEFERRED — LAN-trust only.
"""
from __future__ import annotations

import dataclasses
import logging

from fastapi import APIRouter, HTTPException

from domain.ports.cache_repository import CacheRepository
from domain.ports.party_repository import PartyRepository

log = logging.getLogger(__name__)


def make_insight_router(party_repo: PartyRepository, cache_repo: CacheRepository) -> APIRouter:
    """Factory — returns a router with repositories closed over."""
    router = APIRouter(prefix="/api")

    @router.get("/parties/{party_id}/insight")
    def get_insight(party_id: str):
        """GET /api/parties/{id}/insight — CustomerInsight + ActionQueueItems.

        Returns {"insight": null} (HTTP 200) when cache is empty.
        Returns 404 when the party has no sapo_customer identity.
        """
        # Resolve sapo_customer identity → numeric customer_id.
        try:
            identities = party_repo.list_identities(party_id)
        except Exception as exc:
            log.error("insight: list_identities party=%s: %s", party_id, exc)
            raise HTTPException(status_code=500, detail="failed to resolve identity")

        customer_id: int | None = None
        for ident in identities:
            if ident.identity_type == "sapo_customer":
                try:
                    customer_id = int(ident.identity_value)
                    break
                except (ValueError, TypeError):
                    continue

        if customer_id is None:
            raise HTTPException(status_code=404, detail="no sapo_customer identity for this party")

        try:
            cache = cache_repo.get_customer_insight(customer_id)
        except Exception as exc:
            log.error("insight: get_customer_insight party=%s cid=%d: %s", party_id, customer_id, exc)
            raise HTTPException(status_code=500, detail="failed to get insight")

        # None means cache is empty — return null gracefully (HTTP 200).
        return {"insight": dataclasses.asdict(cache) if cache is not None else None}

    return router

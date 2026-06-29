"""HTTP adapter — Approach-script endpoint.

GET /api/parties/{id}/approach-script — returns AI approach script for S14 Call Mode.

Graceful-empty contract:
  - Party has sapo_customer identity but no script file → {"script": null, "meta": null} HTTP 200
  - Party has no sapo_customer identity → HTTP 404
Auth: DEFERRED — LAN-trust only.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from domain.ports.approach_script_repository import ApproachScriptRepository
from domain.ports.party_repository import PartyRepository

log = logging.getLogger(__name__)


def make_approach_script_router(
    party_repo: PartyRepository,
    approach_repo: ApproachScriptRepository,
) -> APIRouter:
    """Factory — returns a router with repositories closed over."""
    router = APIRouter(prefix="/api")

    @router.get("/parties/{party_id}/approach-script")
    def get_approach_script(party_id: str):
        """GET /api/parties/{id}/approach-script — AI approach script for S14 Call Mode.

        Response contract:
          {"script": <data dict> | null, "meta": {"recommended": bool, "confidence": str|null, "refreshed_at": str} | null}

        Returns {"script": null, "meta": null} (HTTP 200) when no script file exists.
        Returns 404 when the party has no sapo_customer identity.
        """
        # Resolve sapo_customer identity → numeric customer_id.
        try:
            identities = party_repo.list_identities(party_id)
        except Exception as exc:
            log.error("approach_script: list_identities party=%s: %s", party_id, exc)
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
            script = approach_repo.get_by_customer_id(customer_id)
        except Exception as exc:
            log.error("approach_script: get_by_customer_id party=%s cid=%d: %s", party_id, customer_id, exc)
            raise HTTPException(status_code=500, detail="failed to get approach script")

        # None means no script file — return null gracefully (HTTP 200).
        if script is None:
            return {"script": None, "meta": None}

        return {
            "script": script.data,
            "meta": {
                "recommended": script.recommended,
                "confidence": script.confidence,
                "refreshed_at": script.refreshed_at,
            },
        }

    return router

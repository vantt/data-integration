"""Sapo page-metadata count helper for reconciliation.

Issues a single cheap GET request (page=1, limit=1) to a Sapo admin endpoint
and returns the `metadata.total` integer — the source-of-truth count for
reconciliation assets.

Live API is gated behind RECON_LIVE_API=1 env flag so that imports and CI
never trigger a real Sapo call.

Public API:
    count_orders(modified_on_min, modified_on_max) -> int | None
    count_customers(created_on_min, created_on_max) -> int | None
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Guard: live calls only when explicitly enabled
_LIVE_API_ENABLED = os.environ.get("RECON_LIVE_API", "").strip() == "1"


def _get_client():
    """Lazy-import SapoClient to avoid startup cost when live API disabled."""
    try:
        from sapo.client import get_sapo_client  # type: ignore[import]
    except ImportError:
        from ingestion.src.sapo.client import get_sapo_client  # type: ignore[import]
    return get_sapo_client()


def _fetch_metadata_total(
    endpoint: str,
    params: dict,
) -> Optional[int]:
    """Issue GET {base_url}/{endpoint} with params, return metadata.total or None.

    Handles 401/403 by triggering a session refresh once before failing.
    Handles 429 by logging; caller should implement backoff if needed.
    """
    if not _LIVE_API_ENABLED:
        logger.debug(
            "api_count: RECON_LIVE_API not set — skipping live call to %s", endpoint
        )
        return None

    try:
        client = _get_client()
        url = f"{client.base_url}/{endpoint}"
        session = client.session

        resp = session.get(url, params={**params, "page": 1, "limit": 1}, timeout=15)

        if resp.status_code in (401, 403):
            logger.warning("api_count: auth error %d — refreshing session", resp.status_code)
            session = client.refresh_session(session)
            resp = session.get(url, params={**params, "page": 1, "limit": 1}, timeout=15)

        if resp.status_code == 429:
            logger.warning("api_count: rate-limited (429) on %s", endpoint)
            return None

        resp.raise_for_status()
        data = resp.json()
        total = data.get("metadata", {}).get("total")
        if total is None:
            logger.warning("api_count: metadata.total missing from %s response", endpoint)
        return int(total) if total is not None else None

    except Exception as exc:  # noqa: BLE001
        logger.error("api_count: failed to fetch %s — %s", endpoint, exc)
        return None


def count_orders(
    modified_on_min: datetime,
    modified_on_max: datetime,
) -> Optional[int]:
    """Return total orders modified within [modified_on_min, modified_on_max).

    Times must be UTC-aware datetimes (pipeline timezone convention).
    Returns None when RECON_LIVE_API is unset or the call fails.
    """
    params = {
        "modified_on_min": modified_on_min.strftime("%Y-%m-%dT%H:%M:%S"),
        "modified_on_max": modified_on_max.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return _fetch_metadata_total("orders.json", params)


def count_customers(
    created_on_min: datetime,
    created_on_max: datetime,
) -> Optional[int]:
    """Return total customers created within [created_on_min, created_on_max).

    NOTE: Sapo customers API does NOT reliably support modified_on filtering;
    use created_on window instead (per research/sapo-page-metadata-verification.md).
    Returns None when RECON_LIVE_API is unset or the call fails.
    """
    params = {
        "created_on_min": created_on_min.strftime("%Y-%m-%dT%H:%M:%S"),
        "created_on_max": created_on_max.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    return _fetch_metadata_total("customers.json", params)

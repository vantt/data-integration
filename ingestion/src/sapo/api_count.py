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


def sum_revenue_orders(
    created_on_min: datetime,
    created_on_max: datetime,
    exclude_statuses: Optional[list[str]] = None,
) -> Optional[float]:
    """Sum $.total from orders created within [created_on_min, created_on_max).

    Paginates through all orders and sums `total` field (net revenue after discount).
    Excludes orders with status in `exclude_statuses` (e.g. ['cancelled', 'voided']).
    Returns None when RECON_LIVE_API is unset or the call fails.

    WARNING: This can issue many API calls for high-volume windows. Use sparingly.
    Rate limit: Sapo standard tier = 40 req/min. We add 1.5s delay between pages.
    """
    import time

    if not _LIVE_API_ENABLED:
        logger.debug("api_count: RECON_LIVE_API not set — skipping sum_revenue_orders")
        return None

    if exclude_statuses is None:
        exclude_statuses = ["cancelled", "voided"]

    # Pre-compute lowercase set for efficient lookup
    exclude_set = {s.lower() for s in exclude_statuses}

    try:
        client = _get_client()
        url = f"{client.base_url}/orders.json"
        session = client.session

        params = {
            "created_on_min": created_on_min.strftime("%Y-%m-%dT%H:%M:%S"),
            "created_on_max": created_on_max.strftime("%Y-%m-%dT%H:%M:%S"),
            "limit": 250,
            "page": 1,
        }

        total_revenue = 0.0
        order_count = 0
        max_pages = 200  # safety limit: 200 * 250 = 50,000 orders max

        while params["page"] <= max_pages:
            resp = session.get(url, params=params, timeout=30)

            if resp.status_code in (401, 403):
                logger.warning("sum_revenue_orders: auth error — refreshing session")
                session = client.refresh_session(session)
                resp = session.get(url, params=params, timeout=30)

            if resp.status_code == 429:
                logger.warning("sum_revenue_orders: rate-limited (429) at page %d", params["page"])
                return None

            resp.raise_for_status()
            data = resp.json()
            orders = data.get("orders", [])

            if not orders:
                break

            for order in orders:
                status = order.get("status", "").lower()
                if status in exclude_set:
                    continue
                order_total = order.get("total", 0) or 0
                total_revenue += float(order_total)
                order_count += 1

            metadata = data.get("metadata", {})
            current_page = metadata.get("page", params["page"])
            total_pages = metadata.get("total_page", 1)

            if current_page >= total_pages:
                break

            params["page"] += 1
            # Rate limit protection: 1.5s delay = ~40 req/min
            time.sleep(1.5)

        # Warn if we hit the page limit (data may be truncated)
        if params["page"] > max_pages:
            logger.warning(
                "sum_revenue_orders: hit max_pages limit (%d), data may be truncated",
                max_pages
            )

        logger.info(
            "sum_revenue_orders: summed %d orders across %d pages, total=%.2f VND",
            order_count, params["page"], total_revenue
        )
        return total_revenue

    except Exception as exc:
        logger.error("sum_revenue_orders: failed — %s", exc)
        return None

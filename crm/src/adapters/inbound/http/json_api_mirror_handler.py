"""json_api_mirror_handler.py — JSON API mirror for order and customer detail.

Mirrors detailView's:
  GET /api/orders/{order_code}     → full OrderDetail as JSON
  GET /api/customers/{party_id}    → full Party as JSON

Intended for programmatic consumers (scripts, other services).
No auth, no pagination — thin read-only mirror only.
"""
from __future__ import annotations

import dataclasses
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)


def make_json_api_mirror_router(orders, parties) -> APIRouter:
    """Return an APIRouter with /api/orders and /api/customers endpoints.

    Args:
        orders: Optional DuckDBOrderRepository with get_order_detail(code) method.
                Pass None when olap.duckdb is unavailable — endpoints return 503.
        parties: SQLitePartyRepository with get_by_id(party_id) method.
    """
    r = APIRouter()

    @r.get("/api/orders/{order_code}")
    async def get_order(order_code: str):
        if orders is None:
            return JSONResponse(
                status_code=503,
                content={"error": "order data unavailable", "code": order_code},
            )
        try:
            detail = orders.get_order_detail(order_code)
        except Exception as exc:
            log.warning("json_api: get_order %r failed: %s", order_code, exc)
            return JSONResponse(status_code=503, content={"error": "upstream error"})

        if detail is None:
            return JSONResponse(
                status_code=404,
                content={"error": "order not found", "code": order_code},
            )
        return dataclasses.asdict(detail)

    @r.get("/api/customers/{party_id}")
    async def get_customer(party_id: str):
        try:
            party = parties.get_by_id(party_id)
        except Exception as exc:
            log.warning("json_api: get_customer %r failed: %s", party_id, exc)
            return JSONResponse(status_code=503, content={"error": "upstream error"})

        if party is None:
            return JSONResponse(
                status_code=404,
                content={"error": "customer not found", "id": party_id},
            )
        return dataclasses.asdict(party)

    return r

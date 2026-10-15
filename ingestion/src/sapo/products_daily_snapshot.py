"""Sapo products: nightly full capture of prices and stock positions (append-only raw).

The incremental products batch (`products.py`) only re-reads a product when Sapo moves its
`modified_on`, and Sapo changes stock and sometimes prices without moving it. This capture
reads EVERY page of products.json each night and stores a compact copy of each product in
`sapo_v2_raw/product_daily_snapshot`. The table is the only record of past prices and stock
positions (Sapo keeps no history of them): it is append-only, never rewritten, never dropped.

Envelope per product (one row):
    entity_id, entity_type='product', ingest_method='daily_snapshot',
    captured_at       UTC start of the run, one value for the whole run
    capture_run_id    one value for the whole run
    modified_on       product modified_on reported by Sapo
    payload_hash      md5 of the compact payload (sorted keys)
    payload           {id, modified_on, variants: [{id, sku, variant_prices, inventories}]}
    year, month       ICT calendar month of captured_at (also the file partition)

All or nothing: `scan_catalogue` reads the whole catalogue in memory before anything is handed
to dlt, so a failure on any page raises before a single row is extracted or loaded.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import dlt

try:
    from .products import fetch_products_page
except ImportError:
    from sapo.products import fetch_products_page

ICT = ZoneInfo("Asia/Ho_Chi_Minh")
TABLE_NAME = "product_daily_snapshot"
INGEST_METHOD = "daily_snapshot"
# Below this share of the Sapo catalogue total the capture is logged and reported as WARN.
COVERAGE_WARN_RATIO = 0.98

COLUMNS = {
    "entity_id": {"data_type": "text", "nullable": False},
    "entity_type": {"data_type": "text"},
    "ingest_method": {"data_type": "text"},
    "captured_at": {"data_type": "timestamp", "nullable": False},
    "capture_run_id": {"data_type": "text", "nullable": False},
    "modified_on": {"data_type": "text"},
    "payload_hash": {"data_type": "text"},
    "payload": {"data_type": "json"},
    "year": {"data_type": "text"},
    "month": {"data_type": "text"},
}


@dataclass
class CatalogueScan:
    products: List[Dict[str, Any]]  # deduplicated on id, in first-seen order
    pages: int                      # non-empty pages read
    sapo_total: Optional[int]       # metadata.total reported by Sapo (largest seen)
    duplicates: int                 # rows dropped because the id was already seen


def ict_partition(captured_at: datetime) -> Dict[str, str]:
    """`year`/`month` of the ICT calendar day of `captured_at` (UTC-aware)."""
    local = captured_at.astimezone(ICT)
    return {"year": str(local.year), "month": str(local.month)}


def coverage_ratio(captured: int, sapo_total: Optional[int]) -> Optional[float]:
    """Share of the Sapo catalogue captured; None when Sapo reported no usable total."""
    if not sapo_total or sapo_total <= 0:
        return None
    return captured / sapo_total


def compact_product(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only what price and stock history need."""
    return {
        "id": raw.get("id"),
        "modified_on": raw.get("modified_on"),
        "variants": [
            {
                "id": v.get("id"),
                "sku": v.get("sku"),
                "variant_prices": v.get("variant_prices") or [],
                "inventories": v.get("inventories") or [],
            }
            for v in (raw.get("variants") or [])
        ],
    }


def _newer(candidate: Dict[str, Any], current: Dict[str, Any]) -> bool:
    # Sapo timestamps share one ISO-8601 UTC format, so string order is time order.
    return (candidate.get("modified_on") or "") > (current.get("modified_on") or "")


def scan_catalogue(
    client: Any,
    page_size: int = 50,
    max_pages: int = 200,
    fetch_page: Callable[..., Dict[str, Any]] = fetch_products_page,
    sleep: Callable[[float], None] = time.sleep,
) -> CatalogueScan:
    """Read products.json from page 1 to the first empty page, with no cursor and no early stop.

    Errors propagate (after the per-page retries of `fetch_page`): the caller must not load a
    partial catalogue. An empty page is retried once before it ends the scan. A product seen on
    two pages (Sapo re-sorts when a product is edited during the scan) is kept once, with the
    largest `modified_on`.
    """
    session = client.session
    by_id: Dict[Any, Dict[str, Any]] = {}
    pages = 0
    duplicates = 0
    sapo_total: Optional[int] = None
    empty_retried = False
    page = 1

    while page <= max_pages:
        data = fetch_page(client, session, page, page_size)
        total = (data.get("metadata") or {}).get("total")
        if isinstance(total, int):
            sapo_total = max(sapo_total or 0, total)

        rows = data.get("products") or []
        if not rows:
            if not empty_retried:
                empty_retried = True
                sleep(2)
                continue
            break
        empty_retried = False
        pages += 1

        for raw in rows:
            pid = raw.get("id")
            if pid is None:
                continue
            if pid in by_id:
                duplicates += 1
                if _newer(raw, by_id[pid]):
                    by_id[pid] = raw
            else:
                by_id[pid] = raw
        page += 1
    else:
        print(f"[WARN] products daily snapshot: stopped at max_pages={max_pages} before an empty page")

    return CatalogueScan(
        products=list(by_id.values()), pages=pages, sapo_total=sapo_total, duplicates=duplicates
    )


def build_envelopes(
    products: List[Dict[str, Any]],
    captured_at: datetime,
    capture_run_id: str,
) -> List[Dict[str, Any]]:
    """One envelope per product; every row carries the same captured_at and capture_run_id."""
    if captured_at.tzinfo is None:
        raise ValueError("captured_at must be timezone-aware (UTC)")
    captured_utc = captured_at.astimezone(timezone.utc)
    partition = ict_partition(captured_utc)
    envelopes = []
    for raw in products:
        payload = compact_product(raw)
        payload_hash = hashlib.md5(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()
        envelopes.append({
            "entity_id": str(raw["id"]),
            "entity_type": "product",
            "ingest_method": INGEST_METHOD,
            "captured_at": captured_utc,
            "capture_run_id": capture_run_id,
            "modified_on": raw.get("modified_on"),
            "payload_hash": payload_hash,
            "payload": payload,
            **partition,
        })
    return envelopes


def new_capture_run_id() -> str:
    return uuid.uuid4().hex


def product_daily_snapshot_resource(envelopes: List[Dict[str, Any]]):
    """dlt resource over already-scanned envelopes. Append, no primary key: never merged."""
    return dlt.resource(
        envelopes,
        name=TABLE_NAME,
        write_disposition="append",
        columns=COLUMNS,
    )

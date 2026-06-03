"""
Sapo Inventory Transactions v2 Source — Date-Windowed Batch Sync
Unified Transaction Log Strategy (Envelope Schema)

Endpoint: GET {base_url}/reports/inventories/transaction.json
Params: page, limit (max 250), start_date, end_date (UTC ISO Z)
Required headers: X-Requested-With, Referer, Accept

Response shape:
  {
    "metadata": {"total": int, "page": int, "limit": int},
    "items": [{
      issued_at_utc, log_root_id, log_type, log_type_name,
      trans_type, trans_type_name, trans_object_id, trans_object_code,
      action, product_id, product_name, product_category, variant_id,
      variant_name, sku, barcode, unit, location_id, location_label,
      import_quantity, import_amount, export_quantity, export_amount,
      onhand, amount, mac, total_mac, source
    }, ...],
    "summary": {...}   <- ignored
  }

entity_id = md5(json.dumps(item, sort_keys=True))  # content-addressed: distinct payload = distinct row
"""

import dlt
import requests
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from typing import Iterator, List, Dict, Any, Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

try:
    from ._inventory_v2_window import (
        compute_hour_window,
        compute_day_window,
        month_windows,
    )
    from .client import get_sapo_client
except ImportError:
    from sapo._inventory_v2_window import (
        compute_hour_window,
        compute_day_window,
        month_windows,
    )
    from sapo.client import get_sapo_client

# Required AJAX headers for the report endpoint
_AJAX_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/plain, */*",
}


@dlt.source
def sapo_inventory_transactions_v2_source(
    window_mode: str = "hour",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    backfill_start: str = "2021-05-01",
    page_size: int = 250,
    max_pages: int = 1000,
    full_refresh: bool = False,
):
    """
    Sapo inventory transactions v2 source.

    Args:
        window_mode: "hour" | "day" | "backfill" | "custom"
        start_date:  UTC ISO string (required for window_mode="custom")
        end_date:    UTC ISO string (required for window_mode="custom")
        backfill_start: First date for backfill mode (YYYY-MM-DD, default 2021-05-01)
        page_size:   Items per API page (max 250)
        max_pages:   Safety cap per window
        full_refresh: Accepted but NO-OP for windowed source (logged)
    """
    return _inventory_transactions_v2(
        window_mode=window_mode,
        start_date=start_date,
        end_date=end_date,
        backfill_start=backfill_start,
        page_size=page_size,
        max_pages=max_pages,
        full_refresh=full_refresh,
    )


@dlt.resource(
    primary_key="entity_id",
    write_disposition="append",
    name="inventory_transaction_v2",
    columns={
        "entity_id":        {"data_type": "text"},
        "entity_type":      {"data_type": "text"},
        "ingest_method":    {"data_type": "text", "partition": True},
        "event_type":       {"data_type": "text"},
        "event_timestamp":  {"data_type": "timestamp"},
        "payload_hash":     {"data_type": "text"},
        "year":             {"data_type": "text", "partition": True},
        "month":            {"data_type": "text", "partition": True},
        "payload":          {"data_type": "json"},
        "sync_metadata":    {"data_type": "json"},
    },
)
def _inventory_transactions_v2(
    window_mode: str = "hour",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    backfill_start: str = "2021-05-01",
    page_size: int = 250,
    max_pages: int = 1000,
    full_refresh: bool = False,
) -> Iterator[List[Dict[str, Any]]]:
    """
    Yields lists of envelope dicts, one list per API page per window.

    Window modes:
      hour     — previous + current hour (default, for scheduler)
      day      — today ICT [00:00:00 .. 23:59:59]
      backfill — all calendar-month windows from backfill_start through now
      custom   — single window from start_date to end_date (UTC ISO Z strings)
    """

    if full_refresh:
        print("[>>] inventory_transactions_v2: full_refresh=True received but IGNORED "
              "(windowed source has no cursor; window params control the data range).")

    client = get_sapo_client()
    base_url = client.base_url
    session = client.session
    request_delay = client.request_delay

    # Build Referer header (constant for this resource)
    referer = f"{base_url}/reports/inventories/transaction"
    ajax_headers = {**_AJAX_HEADERS, "Referer": referer}

    # Resolve windows list: list of (start_utc_iso, end_utc_iso)
    windows = _build_windows(window_mode, start_date, end_date, backfill_start)
    print(f"[>>] inventory_transactions_v2: mode={window_mode}, {len(windows)} window(s), "
          f"page_size={page_size}")

    url = f"{base_url}/reports/inventories/transaction.json"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def fetch_page(page_num: int, w_start: str, w_end: str) -> Dict[str, Any]:
        """Fetch a single page with retry, auth-refresh, and 429 handling."""
        if request_delay > 0:
            time.sleep(request_delay)

        params = {
            "page": page_num,
            "limit": page_size,
            "start_date": w_start,
            "end_date": w_end,
        }

        resp = session.get(url, params=params, headers=ajax_headers, timeout=30)

        if resp.status_code in (401, 403):
            print("[~] Session expired, refreshing cookies...")
            client.refresh_session(session)
            resp = session.get(url, params=params, headers=ajax_headers, timeout=30)
            if resp.status_code in (401, 403):
                raise requests.HTTPError(
                    f"Auth failed after refresh: {resp.status_code}", response=resp
                )

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 60))
            print(f"[..] Rate limited (429). Waiting {retry_after}s...")
            time.sleep(retry_after)
            resp = session.get(url, params=params, headers=ajax_headers, timeout=30)

        resp.raise_for_status()
        return resp.json()

    for win_idx, (w_start, w_end) in enumerate(windows, start=1):
        print(f"[>>] Window {win_idx}/{len(windows)}: {w_start} → {w_end}")
        consecutive_errors = 0
        MAX_ERRORS = 3
        pages_fetched = 0
        total_rows_window = 0

        for page_num in range(1, max_pages + 1):
            try:
                data = fetch_page(page_num, w_start, w_end)
                consecutive_errors = 0
            except Exception as exc:
                print(f"[ERR] Window {win_idx} page {page_num}: {exc}")
                consecutive_errors += 1
                if consecutive_errors >= MAX_ERRORS:
                    print(f"[ERR] Too many consecutive errors in window {win_idx}, skipping rest.")
                    break
                continue

            metadata = data.get("metadata", {})
            items = data.get("items", [])

            # Determine pages needed on first page
            if page_num == 1:
                total = metadata.get("total", 0)
                pages_needed = math.ceil(total / page_size) if total and page_size else 1
                print(f"[i]  Window {win_idx}: total={total}, pages_needed={pages_needed}")
            else:
                pages_needed = max_pages  # continue until empty or max_pages

            if not items:
                print(f"[i]  Window {win_idx} page {page_num}: 0 items, done.")
                break

            envelopes = _build_envelopes(items, w_start, w_end)
            pages_fetched += 1
            total_rows_window += len(envelopes)

            print(f"[i]  Window {win_idx} page {page_num}: "
                  f"{len(items)} items → {len(envelopes)} envelopes")

            if envelopes:
                yield envelopes

            # Stop when we've fetched all known pages
            if page_num >= pages_needed:
                break

        print(f"[OK] Window {win_idx} done: {pages_fetched} pages, "
              f"{total_rows_window} envelopes yielded.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_windows(
    window_mode: str,
    start_date: Optional[str],
    end_date: Optional[str],
    backfill_start: str,
) -> List[tuple]:
    """Map window_mode to a list of (start_utc_iso, end_utc_iso) tuples."""
    if window_mode == "hour":
        return [compute_hour_window()]
    elif window_mode == "day":
        return [compute_day_window()]
    elif window_mode == "backfill":
        return month_windows(backfill_start_date_str=backfill_start)
    elif window_mode == "custom":
        if not start_date or not end_date:
            raise ValueError(
                "window_mode='custom' requires both --start and --end arguments."
            )
        return [(start_date, end_date)]
    else:
        raise ValueError(
            f"Unknown window_mode={window_mode!r}. "
            "Choose from: hour, day, backfill, custom"
        )


def _build_envelopes(
    items: List[Dict[str, Any]],
    window_start: str,
    window_end: str,
) -> List[Dict[str, Any]]:
    """Convert raw API items into envelope dicts. Skips items missing issued_at_utc."""
    envelopes = []
    processing_ts = datetime.utcnow().isoformat()

    for item in items:
        issued_at_utc = item.get("issued_at_utc")
        if not issued_at_utc:
            continue

        try:
            dt = datetime.fromisoformat(issued_at_utc.replace("Z", "+00:00"))
        except ValueError:
            print(f"[!] Cannot parse issued_at_utc={issued_at_utc!r}, skipping.")
            continue

        payload_hash = hashlib.md5(
            json.dumps(item, sort_keys=True).encode("utf-8")
        ).hexdigest()

        event_type = item.get("trans_type_name") or item.get("log_type_name") or "unknown"

        envelope = {
            # content-addressed id — distinct payload (incl. onhand running balance) = distinct row;
            # identical re-fetch dedups naturally; business grain decided later in std layer.
            "entity_id":       payload_hash,
            "entity_type":     "inventory_transaction",
            "ingest_method":   "batch_sync",
            "event_type":      event_type,
            "event_timestamp": issued_at_utc,
            "payload_hash":    payload_hash,
            "year":            str(dt.year),
            "month":           str(dt.month),
            "payload":         item,
            "sync_metadata": {
                "source_system":        "sapo",
                "source":               "batch_sync",
                "source_version":       "v2",
                "event_timestamp":      issued_at_utc,
                "processing_timestamp": processing_ts,
                "window_start":         window_start,
                "window_end":           window_end,
            },
        }
        envelopes.append(envelope)

    return envelopes

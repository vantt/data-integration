"""
DLT Source Template — Pattern A (Custom API, Envelope Schema)

Thay thế trước khi dùng:
  {SOURCE}        → tên source (sapo, shopify, ...)
  {ENTITY}        → tên entity (order, customer, product, ...)
  {ENTITY_TYPE}   → string entity type trong envelope ("order", "customer", ...)
  {API_ENDPOINT}  → path endpoint API ("/orders.json", "/customers.json", ...)
  {RESPONSE_KEY}  → key trong API response chứa list items ("orders", "customers", ...)
  {CURSOR_FIELD}  → field dùng để sort/track changes ("modified_on", "created_on", ...)

Auth:
  - Session-based (Sapo): dùng SharedCookieManager — xem src/sapo/client.py
  - Token-based: thêm header `Authorization: Bearer {token}` vào session
"""

import dlt
import hashlib
import json
import time
import requests
from typing import Iterator, Dict, Any, List
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# ─── Envelope column schema (chuẩn — không thay đổi) ──────────────────────────
_ENVELOPE_COLUMNS = {
    "entity_id":       {"data_type": "text"},
    "entity_type":     {"data_type": "text"},
    "ingest_method":   {"data_type": "text", "partition": True},
    "event_type":      {"data_type": "text"},
    "event_timestamp": {"data_type": "timestamp"},
    "payload_hash":    {"data_type": "text"},
    "year":            {"data_type": "text", "partition": True},
    "month":           {"data_type": "text", "partition": True},
    "payload":         {"data_type": "json"},
    "sync_metadata":   {"data_type": "json"},
}


# ─── Source (outer) ────────────────────────────────────────────────────────────

@dlt.source
def {SOURCE}_{ENTITY}_source(
    max_pages: int = 1000,
    page_size: int = 100,
    min_overlap_items: int = 500,
):
    """
    dlt source cho {ENTITY} từ {SOURCE}.
    Trả về resource để dlt xử lý state và schema.
    """
    return {ENTITY}(
        max_pages=max_pages,
        page_size=page_size,
        min_overlap_items=min_overlap_items,
    )


# ─── Resource (inner) ──────────────────────────────────────────────────────────

@dlt.resource(
    primary_key="entity_id",
    write_disposition="append",
    name="{ENTITY}",
    columns=_ENVELOPE_COLUMNS,
)
def {ENTITY}(
    max_pages: int = 1000,
    page_size: int = 100,
    min_overlap_items: int = 500,
    # Incremental cursor — path trong envelope record
    first_timestamp=dlt.sources.incremental("sync_metadata.event_timestamp"),
) -> Iterator[List[Dict[str, Any]]]:
    """
    Load {ENTITY} incrementally theo DESC strategy với early-stop.

    Output: danh sách envelope records theo chuẩn Unified Envelope Schema.
    """
    # ── Init client / session ─────────────────────────────────────────────────
    # Option A: Session-based auth (Sapo pattern)
    from src.{SOURCE}.client import get_{SOURCE}_client
    client = get_{SOURCE}_client()
    base_url = client.base_url
    request_delay = client.request_delay
    session = client.session

    # Option B: Token-based auth (thay Option A)
    # session = requests.Session()
    # session.headers.update({"Authorization": f"Bearer {dlt.secrets['sources.{SOURCE}.api_token']}"})
    # base_url = dlt.config["sources.{SOURCE}.base_url"]
    # request_delay = float(dlt.config.get("sources.{SOURCE}.request_delay", 1.0))

    # ── State ─────────────────────────────────────────────────────────────────
    last_value = first_timestamp.last_value
    page = 1
    consecutive_old_items = 0
    consecutive_errors = 0
    empty_retries = 0
    MAX_ERRORS = 3

    print(f"Starting incremental load for {ENTITY} from: {last_value}")
    print(f"Config: page_size={page_size}, min_overlap_items={min_overlap_items}")

    # ── Page fetcher với retry ────────────────────────────────────────────────
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def fetch_page(page_num: int, sess: requests.Session) -> Dict[str, Any]:
        """Fetch single page với exponential backoff + inline status handling."""
        url = f"{base_url}{API_ENDPOINT}"

        if request_delay > 0:
            time.sleep(request_delay)

        params = {
            "page": page_num,
            "limit": page_size,
            "sort_by": f"{CURSOR_FIELD} desc",  # DESC để early-stop hoạt động
        }

        response = sess.get(url, params=params, timeout=30)

        # 401/403 — session hết hạn, refresh và retry một lần
        if response.status_code in (401, 403):
            print("Session expired, refreshing...")
            client.refresh_session(sess)  # xóa nếu dùng token-based auth
            response = sess.get(url, params=params, timeout=30)
            if response.status_code in (401, 403):
                raise requests.HTTPError(
                    f"Auth failed after refresh: {response.status_code}",
                    response=response,
                )

        # 429 — rate limit, đợi theo Retry-After header
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"Rate limited (429). Waiting {retry_after}s...")
            time.sleep(retry_after)
            response = sess.get(url, params=params, timeout=30)

        response.raise_for_status()
        return response.json()

    # ── Pagination loop ───────────────────────────────────────────────────────
    while page <= max_pages:
        try:
            data = fetch_page(page, session)
            consecutive_errors = 0

            items = data.get("{RESPONSE_KEY}", [])

            # Empty page: retry một lần tránh false early-stop do network fluke
            if not items:
                if empty_retries < 1:
                    empty_retries += 1
                    print(f"Page {page}: empty, retrying once...")
                    time.sleep(2)
                    continue
                print(f"Page {page}: empty after retry, stopping.")
                break
            empty_retries = 0

            # Lọc items mới và build envelope
            new_envelopes = []
            for raw_item in items:
                cursor_value = raw_item.get("{CURSOR_FIELD}") or raw_item.get("created_on")
                if not cursor_value:
                    continue

                if last_value is None or cursor_value > last_value:
                    envelope = _build_envelope(raw_item, "{ENTITY_TYPE}", "batch_sync", "{CURSOR_FIELD}")
                    if envelope:
                        new_envelopes.append(envelope)
                        consecutive_old_items = 0
                else:
                    consecutive_old_items += 1

            print(
                f"Page {page}: {len(new_envelopes)}/{len(items)} new | "
                f"old stream: {consecutive_old_items}/{min_overlap_items}"
            )

            if new_envelopes:
                yield new_envelopes

            # Early-stop: đủ safety buffer → dừng scan
            if consecutive_old_items >= min_overlap_items:
                print(f"Early stop: {consecutive_old_items} consecutive old items.")
                break

            page += 1

        except Exception as e:
            print(f"Error at page {page}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= MAX_ERRORS:
                print("Too many consecutive errors. Stopping.")
                break
            # Không increment page — retry cùng page


# ─── Envelope builder ─────────────────────────────────────────────────────────

def _build_envelope(
    raw_item: Dict[str, Any],
    entity_type: str,
    ingest_method: str,  # "batch_sync" | "webhook" | "history_log"
    cursor_field: str,
) -> Dict[str, Any] | None:
    """
    Chuẩn hóa raw API response thành Unified Envelope Schema.
    Trả về None nếu không parse được timestamp.
    """
    cursor_value = raw_item.get(cursor_field) or raw_item.get("created_on")
    if not cursor_value:
        return None

    try:
        dt = datetime.fromisoformat(cursor_value.replace("Z", "+00:00"))
    except ValueError:
        print(f"Could not parse timestamp: {cursor_value}")
        return None

    # Payload hash để detect changes và idempotency
    payload_hash = hashlib.md5(
        json.dumps(raw_item, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "entity_id":       str(raw_item.get("id")),
        "entity_type":     entity_type,
        "ingest_method":   ingest_method,
        "event_type":      "snapshot",
        "event_timestamp": cursor_value,
        "payload_hash":    payload_hash,
        "year":            str(dt.year),
        "month":           str(dt.month),
        "payload":         raw_item,
        "sync_metadata": {
            "source_system":         "{SOURCE}",
            "event_timestamp":       cursor_value,
            "processing_timestamp":  datetime.utcnow().isoformat(),
            "original_event_id":     None,  # N/A cho batch sync
        },
    }

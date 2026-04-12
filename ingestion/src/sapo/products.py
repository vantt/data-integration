"""
Sapo Products Source - Batch Sync Implementation
Unified Transaction Log Strategy (Envelope Schema)

SAPO Product Response Structure:
    URL: /admin/products.json?page=1&limit=50&sort_by=modified_on&sort_direction=desc
    {
        "metadata": {"total": 558, "page": 1, "limit": 50},
        "products": [
            {
                "id": 222855174,
                "tenant_id": 445355,
                "created_on": "2025-09-25T05:01:12Z",
                "modified_on": "2025-09-25T08:29:49Z",
                "status": "active",
                "brand": null,
                "name": "...",
                "category_id": 1674761,
                "category": "...",
                "category_code": "PGN00003",
                "product_type": "normal",
                "opt1": "...", "opt2": null, "opt3": null,
                "tags": "",
                "medicine": false,
                "variants": [{ ... variant_prices, inventories ... }],
                "options": [{ ... }],
                "images": [{ ... }],
            }
        ]
    }

Nested arrays stored as JSON in payload:
  - variants (contains variant_prices, inventories per variant)
  - options
  - images
  - product_medicines
"""

import dlt
import requests
from typing import Iterator, Dict, Any, List
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)


@dlt.source
def sapo_products_source(
    max_pages: int = 100,
    page_size: int = 50,
    min_overlap_items: int = 100
):
    """Sapo products source function."""
    return products(
        max_pages=max_pages,
        page_size=page_size,
        min_overlap_items=min_overlap_items
    )


@dlt.resource(
    primary_key="entity_id",
    write_disposition="append",
    name="product",
    columns={
        "entity_id": {"data_type": "text"},
        "entity_type": {"data_type": "text"},
        "payload": {"data_type": "json"},
        "sync_metadata": {"data_type": "json"},
        "ingest_method": {"data_type": "text", "partition": True},
        "event_type": {"data_type": "text"},
        "event_timestamp": {"data_type": "timestamp"},
        "payload_hash": {"data_type": "text"},
        "year": {"data_type": "text", "partition": True},
        "month": {"data_type": "text", "partition": True}
    }
)
def products(
    max_pages: int = 100,
    page_size: int = 50,
    min_overlap_items: int = 100,
    first_timestamp=dlt.sources.incremental("sync_metadata.event_timestamp")
) -> Iterator[List[Dict[Any, Any]]]:
    """
    Load products incrementally using DESC strategy.

    Sorted by modified_on DESC so newest changes come first.
    Early-stop when min_overlap_items consecutive old items are seen.
    """

    import hashlib
    import json

    try:
        from .client import get_sapo_client
    except ImportError:
        from sapo.client import get_sapo_client

    client = get_sapo_client()
    base_url = client.base_url
    request_delay = client.request_delay

    # State
    page = 1
    consecutive_old_items = 0
    consecutive_errors = 0
    MAX_ERRORS = 3
    empty_retries = 0

    last_value = first_timestamp.last_value
    print(f"[>>] Starting Products incremental load from: {last_value}")
    print(f"   Config: page_size={page_size}, min_overlap_items={min_overlap_items}")

    session = client.session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def fetch_page_with_retry(page_num: int, current_session) -> Dict[str, Any]:
        """Fetch single page with exponential backoff retry."""
        url = f"{base_url}/products.json"

        if request_delay > 0:
            import time
            time.sleep(request_delay)

        params = {
            "page": page_num,
            "limit": page_size,
            "sort_by": "modified_on",
            "sort_direction": "desc",
        }

        response = current_session.get(url, params=params, timeout=30)

        if response.status_code in (401, 403):
            print("[~] Session expired, refreshing cookies...")
            client.refresh_session(current_session)
            response = current_session.get(url, params=params, timeout=30)
            if response.status_code in (401, 403):
                raise requests.HTTPError(
                    f"Auth failed after refresh: {response.status_code}",
                    response=response
                )

        if response.status_code == 429:
            import time
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"[..] Rate limited (429). Waiting {retry_after}s...")
            time.sleep(retry_after)
            response = current_session.get(url, params=params, timeout=30)

        response.raise_for_status()
        return response.json()

    while page <= max_pages:
        try:
            data = fetch_page_with_retry(page, session)
            consecutive_errors = 0

            products_data = data.get("products", [])

            if not products_data:
                if empty_retries < 1:
                    empty_retries += 1
                    print(f"[!] Page {page}: Empty, retrying once...")
                    import time
                    time.sleep(2)
                    continue
                print(f"[x] Page {page}: Empty after retry, stopping.")
                break
            empty_retries = 0

            new_envelopes = []

            for raw_product in products_data:
                product_modified_on = raw_product.get("modified_on")
                if not product_modified_on:
                    product_modified_on = raw_product.get("created_on")
                if not product_modified_on:
                    continue

                if last_value is None or product_modified_on > last_value:
                    try:
                        dt = datetime.fromisoformat(
                            product_modified_on.replace("Z", "+00:00")
                        )
                        entity_id = raw_product.get("id")

                        payload_str = json.dumps(raw_product, sort_keys=True)
                        payload_hash = hashlib.md5(
                            payload_str.encode('utf-8')
                        ).hexdigest()

                        envelope = {
                            "entity_id": str(entity_id),
                            "entity_type": "product",
                            "ingest_method": "batch_sync",
                            "event_type": "snapshot",
                            "event_timestamp": product_modified_on,
                            "payload_hash": payload_hash,
                            "year": str(dt.year),
                            "month": str(dt.month),
                            "payload": raw_product,
                            "sync_metadata": {
                                "source_system": "sapo",
                                "event_timestamp": product_modified_on,
                                "processing_timestamp": datetime.utcnow().isoformat(),
                                "original_event_id": None
                            }
                        }

                        new_envelopes.append(envelope)
                        consecutive_old_items = 0
                    except ValueError:
                        print(f"[!] Could not parse modified_on: {product_modified_on}")
                        continue
                else:
                    consecutive_old_items += 1

            print(
                f"[i] Page {page}: {len(new_envelopes)}/{len(products_data)} new. "
                f"Old stream: {consecutive_old_items}/{min_overlap_items}"
            )

            if new_envelopes:
                yield new_envelopes

            if consecutive_old_items >= min_overlap_items:
                print(
                    f"[OK] Early stop triggered. Safety buffer satisfied "
                    f"({consecutive_old_items} old items seen)."
                )
                break

            page += 1

        except Exception as e:
            print(f"[ERR] Error at page {page}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= MAX_ERRORS:
                print("Too many errors. Stopping.")
                break

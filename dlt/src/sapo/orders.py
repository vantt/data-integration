"""
Sapo Orders Source - Production Implementation
DESC Strategy with Full Features
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
def sapo_orders_source(
    max_pages: int = 1000, 
    page_size: int = 250, 
    min_overlap_items: int = 500
):
    """
    Sapo source function.
    """
    return orders(
        max_pages=max_pages, 
        page_size=page_size, 
        min_overlap_items=min_overlap_items
    )

@dlt.resource(
    primary_key="id",
    write_disposition="append",
    table_format="delta",
    name="order", # Renamed from orders
    columns={
        "id": {"data_type": "bigint"},
        # ... (other cols remain same, checked via diff)
        "code": {"data_type": "text"},
        "created_on": {"data_type": "timestamp"},
        "modified_on": {"data_type": "timestamp"},
        "tenant_id": {"data_type": "bigint"},
        "location_id": {"data_type": "bigint"},
        "issued_on": {"data_type": "timestamp"},
        "total": {"data_type": "double"},
        "total_tax": {"data_type": "double"},
        "total_discount": {"data_type": "double"},
        "status": {"data_type": "text"},
        "payment_status": {"data_type": "text"},
        "fulfillment_status": {"data_type": "text"},
        "customer_id": {"data_type": "bigint"},
        "account_id": {"data_type": "bigint"},
        "assignee_id": {"data_type": "bigint"},
        "entity_type": {"data_type": "text"}, # Partition removed
        "source": {"data_type": "text", "partition": True},
        "year": {"data_type": "text", "partition": True},
        "month": {"data_type": "text", "partition": True},
        # Prevent normalization of nested fields
        "customer_data": {"data_type": "json"},
        "discount_items": {"data_type": "json"},
        "order_line_items": {"data_type": "json"},
        "fulfillments": {"data_type": "json"},
        "returns": {"data_type": "json"},
        "prepayments": {"data_type": "json"},
        "tags": {"data_type": "json"},
        "order_return_exchange": {"data_type": "json"},
        "order_returns": {"data_type": "json"},
        "promotion_redemptions": {"data_type": "json"}
    }
)
def orders(
    max_pages: int = 1000,
    page_size: int = 250,
    min_overlap_items: int = 500,
    created_on=dlt.sources.incremental("created_on")
) -> Iterator[List[Dict[Any, Any]]]:
    """
    Load orders incrementally using DESC strategy

    Strategy:
    1. Sort DESC (newest first)
    2. Filter client-side by created_on > checkpoint
    3. Early stop with Items-based overlap safety
    """

    # Initialize client
    try:
        from .client import get_sapo_client
    except ImportError:
        from sapo.client import get_sapo_client

    client = get_sapo_client()
    base_url = client.base_url
    request_delay = client.request_delay

    # State
    page = 1
    # Count consecutive old items to determine safety buffer
    consecutive_old_items = 0
    consecutive_errors = 0
    MAX_ERRORS = 3

    last_value = created_on.last_value
    print(f"🚀 Starting incremental load from: {last_value}")
    print(f"   Config: page_size={page_size}, min_overlap_items={min_overlap_items}")

    session = client.session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def fetch_page_with_retry(page_num: int, current_session) -> Dict[str, Any]:
        """Fetch single page with exponential backoff retry"""
        url = f"{base_url}/orders.json"

        # Apply rate limiting delay
        if request_delay > 0:
            import time
            time.sleep(request_delay)

        params = {
            "page": page_num,
            "limit": page_size,
            "sort_by": "created_on",
            "order": "desc"
        }

        params["sort_by"] = "created_on desc"

        response = current_session.get(url, params=params, timeout=30)

        if response.status_code == 401 or response.status_code == 403:
             # Cookies might be expired if session management missed it
             # Force refresh
             print("🔄 Session expired, refreshing cookies...")

             # Refresh using client helper
             client.refresh_session(current_session)

             print(f"↻ Retrying with new session info. UA: {current_session.headers.get('User-Agent')}")
             response = current_session.get(url, params=params, timeout=30)

        response.raise_for_status()
        return response.json()

    while page <= max_pages:
        try:
            data = fetch_page_with_retry(page, session)
            consecutive_errors = 0

            # Sapo response structure: {"orders": [...], "metadata": {...}}
            orders_data = data.get("orders", [])

            if not orders_data:
                print(f"📭 Page {page}: Empty")
                break

            # Filter new items
            new_orders = []

            for order in orders_data:
                # User's created_on format check needed?
                # Usually ISO. dlt handles string comparison for ISO timestamps correctly.
                order_created_on = order.get("created_on")

                # Check for None just in case
                if not order_created_on:
                    continue

                if last_value is None or order_created_on > last_value:
                    # New Item found - Enrich with partition columns
                    try:
                        # created_on format example: "2024-01-15T08:30:00Z"
                        dt = datetime.fromisoformat(order_created_on.replace("Z", "+00:00"))
                        order["year"] = str(dt.year)
                        order["month"] = str(dt.month)
                        order["source"] = "batch_sync"
                        order["entity_type"] = "order"

                        new_orders.append(order)

                        # IMPORTANT: Reset counter because we found a gap-filler!
                        consecutive_old_items = 0
                    except ValueError:
                        print(f"⚠️ Could not parse created_on: {order_created_on}")
                        continue
                else:
                    # Old Item found
                    consecutive_old_items += 1
            
            print(f"📄 Page {page}: {len(new_orders)}/{len(orders_data)} new. Old stream: {consecutive_old_items}/{min_overlap_items}")

            if new_orders:
                yield new_orders
            
            # Early stop based on ITEMS count, not pages
            if consecutive_old_items >= min_overlap_items:
                print(f"✅ Early stop triggered. Safety buffer satistied ({consecutive_old_items} old items seen).")
                break

            page += 1

        except Exception as e:
            print(f"❌ Error at page {page}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= MAX_ERRORS:
                 print("Too many errors. Stopping.")
                 break
            page += 1 # Skip page or retry? If retry needed, use tenacity. Here we skip to avoid infinite stuck.

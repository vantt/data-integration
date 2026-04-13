"""
Sapo Orders Source - Production Implementation
Unified Transaction Log Strategy (Envelope Schema)

SAPO Order Response Structure:
   {
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
        "ingest_method": {"data_type": "text", "partition": True},
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
    page_size: int = 100,
    min_overlap_items: int = 500,
    full_refresh: bool = False
):
    """
    Sapo source function.
    """
    return orders(
        max_pages=max_pages,
        page_size=page_size,
        min_overlap_items=min_overlap_items,
        full_refresh=full_refresh
    )

@dlt.resource(
    primary_key="entity_id",
    write_disposition="append",
    name="order", 
    columns={
        "entity_id": {"data_type": "text"},
        "entity_type": {"data_type": "text"},
        "payload": {"data_type": "json"},
        "sync_metadata": {"data_type": "json"},
        # Retention of Partition Columns at Root Level
        "ingest_method": {"data_type": "text", "partition": True},
        "event_type": {"data_type": "text"},
        "event_timestamp": {"data_type": "timestamp"},
        "payload_hash": {"data_type": "text"},
        "year": {"data_type": "text", "partition": True},
        "month": {"data_type": "text", "partition": True}
    }
)
def orders(
    max_pages: int = 1000,
    page_size: int = 100,
    min_overlap_items: int = 500,
    full_refresh: bool = False,
    first_timestamp=dlt.sources.incremental("sync_metadata.event_timestamp")
) -> Iterator[List[Dict[Any, Any]]]:
    """
    Load orders incrementally using DESC strategy.
    
    Outputs standardized Envelope Schema:
    {
        "entity_id": str,
        "entity_type": "order",
        "entity_id": str,
        "entity_type": "order",
        "payload": json_dict,
        "sync_metadata": { ... },
        "ingest_method": "batch_sync",
        "event_type": "snapshot",
        "payload_hash": "md5...",
        "year": YYYY,
        "month": MM
    }
    """
    
    import hashlib
    import json

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
    empty_retries = 0

    last_value = None if full_refresh else first_timestamp.last_value
    print(f"🚀 Starting incremental load from: {last_value} {'[FULL REFRESH — cursor ignored]' if full_refresh else ''}")
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
            "sort_by": "modified_on desc",            
        }

        # params["sort_by"] = "created_on desc" # Duplicate assignment? existing code had this.

        response = current_session.get(url, params=params, timeout=30)

        if response.status_code == 401 or response.status_code == 403:
            # Cookies might be expired if session management missed it
            # Force refresh
             print("🔄 Session expired, refreshing cookies...")
             # Refresh using client helper
             client.refresh_session(current_session)

             print(f"↻ Retrying with new session info. UA: {current_session.headers.get('User-Agent')}")
             response = current_session.get(url, params=params, timeout=30)
             if response.status_code in (401, 403):
                 raise requests.HTTPError(f"Auth failed after refresh: {response.status_code}", response=response)

        if response.status_code == 429:
            import time
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"⏳ Rate limited (429). Waiting {retry_after}s...")
            time.sleep(retry_after)
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
                if empty_retries < 1:
                    empty_retries += 1
                    print(f"⚠️ Page {page}: Empty, retrying once...")
                    import time
                    time.sleep(2)
                    continue
                print(f"📭 Page {page}: Empty after retry, stopping.")
                break
            empty_retries = 0  # reset on successful page

            # Filter new items
            new_envelopes = []

            for raw_order in orders_data:
                # Use modified_on for change tracking
                order_modified_on = raw_order.get("modified_on")
                
                # Fallback to created_on if modified_on is missing (unlikely)
                if not order_modified_on:
                    order_modified_on = raw_order.get("created_on")

                if not order_modified_on:
                    continue

                if last_value is None or order_modified_on > last_value:
                    try:
                        # 1. Parse Timestamp
                        dt = datetime.fromisoformat(order_modified_on.replace("Z", "+00:00"))
                        
                        # 2. Construct Envelope
                        entity_id = raw_order.get("id")
                        
                        # Calculate Payload Hash
                        payload_str = json.dumps(raw_order, sort_keys=True)
                        payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()

                        envelope = {
                            "entity_id": str(entity_id),
                            "entity_type": "order",
                            "ingest_method": "batch_sync",
                            "event_type": "snapshot",
                            "event_timestamp": order_modified_on,
                            "payload_hash": payload_hash,
                            "year": str(dt.year),
                            "month": str(dt.month),
                            "payload": raw_order, # Full raw data
                            "sync_metadata": {
                                "source_system": "sapo",
                                "source": "batch_sync", # Deprecated but kept for backward compat inside JSON if needed, or remove? Plan says remove 'source' from Envelop root, but inside sync_metadata we can keep 'source_system'. Let's follow the plan:
                                # "source_system": "sapo", 
                                # Wait, plan said 'source' in sync_metadata is replaced by 'source_system'. 
                                # Code below:
                                "source_system": "sapo",
                                "event_timestamp": order_modified_on, # Syncing by Modified Time
                                "processing_timestamp": datetime.utcnow().isoformat(),
                                "original_event_id": None # Not applicable for batch
                            }
                        }

                        new_envelopes.append(envelope)
                        consecutive_old_items = 0
                    except ValueError:
                        print(f"⚠️ Could not parse modified_on: {order_modified_on}")
                        continue
                else:
                    # Old Item found
                    consecutive_old_items += 1
            
            print(f"📄 Page {page}: {len(new_envelopes)}/{len(orders_data)} new. Old stream: {consecutive_old_items}/{min_overlap_items}")

            if new_envelopes:
                yield new_envelopes
            
            # Early stop
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
            # Do NOT increment page — retry the same page

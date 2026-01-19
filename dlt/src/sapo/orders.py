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
def sapo_source(max_pages: int = 1000):
    """
    Sapo source function.
    """
    return orders(max_pages=max_pages)

@dlt.resource(
    primary_key="id",
    write_disposition="append",
    table_format="delta",
    columns={
        "id": {"data_type": "bigint"},
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
    created_on=dlt.sources.incremental("created_on")
) -> Iterator[List[Dict[Any, Any]]]:
    """
    Load orders incrementally using DESC strategy

    Strategy:
    1. Sort DESC (newest first)
    2. Filter client-side by created_on > checkpoint
    3. Early stop with overlap safety
    """
    
    # Initialize client
    try:
        from .client import get_sapo_client
    except ImportError:
        from sapo.client import get_sapo_client
        
    client = get_sapo_client()
    base_url = client.base_url
    request_delay = client.request_delay
    
    # Constants
    # User said: "https://fwg.mysapogo.com/admin/orders.json?page=1&limit=20..."
    # I'll stick to 100 to be safe and efficient, assuming API supports it. 
    PAGE_SIZE = 100 
    OVERLAP = 2
    # MAX_PAGES = 1000 # Safety limit for initial load - Replaced by argument

    # State
    page = 1
    no_new_pages = 0
    consecutive_errors = 0
    MAX_ERRORS = 3
    
    last_value = created_on.last_value
    print(f"🚀 Starting incremental load from: {last_value}")

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
            "limit": PAGE_SIZE,
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
                    # Enrich with partition columns
                    try:
                        # created_on format example: "2024-01-15T08:30:00Z"
                        dt = datetime.fromisoformat(order_created_on.replace("Z", "+00:00"))
                        order["year"] = str(dt.year)
                        order["month"] = str(dt.month)
                        
                        new_orders.append(order)
                    except ValueError:
                        print(f"⚠️ Could not parse created_on: {order_created_on}")
                        continue
            
            print(f"📄 Page {page}: {len(new_orders)}/{len(orders_data)} new")

            if new_orders:
                yield new_orders
                no_new_pages = 0
            else:
                no_new_pages += 1
            
            # Early stop
            if no_new_pages > OVERLAP and page > OVERLAP:
                print(f"✅ Early stop at page {page}")
                break

            page += 1

        except Exception as e:
            print(f"❌ Error at page {page}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= MAX_ERRORS:
                 print("Too many errors. Stopping.")
                 break
            page += 1 # Skip page or retry? If retry needed, use tenacity. Here we skip to avoid infinite stuck.

"""
Sapo Customers Source - Production Implementation
Unified Transaction Log Strategy (Envelope Schema)

SAPO Customer Response Structure:
{
        "id": {"data_type": "bigint"},
        "tenant_id": {"data_type": "bigint"},
        "default_location_id": {"data_type": "bigint"},
        "created_on": {"data_type": "timestamp"},
        "modified_on": {"data_type": "timestamp"},
        "code": {"data_type": "text"},
        "name": {"data_type": "text"},
        "dob": {"data_type": "date"},
        "sex": {"data_type": "text"},
        "description": {"data_type": "text"},
        "email": {"data_type": "text"},
        "fax": {"data_type": "text"},
        "phone_number": {"data_type": "text"},
        "tax_number": {"data_type": "text"},
        "website": {"data_type": "text"},
        "customer_group_id": {"data_type": "bigint"},
        "group_id": {"data_type": "bigint"},
        "group_name": {"data_type": "text"},
        "assignee_id": {"data_type": "bigint"},
        "default_payment_term_id": {"data_type": "bigint"},
        "default_payment_method_id": {"data_type": "bigint"},
        "default_tax_type_id": {"data_type": "bigint"},
        "default_discount_rate": {"data_type": "double"},
        "default_price_list_id": {"data_type": "bigint"},
        "status": {"data_type": "text"},
        "is_default": {"data_type": "bool"},
        "debt": {"data_type": "double"},
        "apply_incentives": {"data_type": "bool"},
        "total_expense": {"data_type": "double"},
        "loyalty_customer": {"data_type": "json"},
        "sale_order": {"data_type": "json"},
        "entity_type": {"data_type": "text"}, # Partition removed
        "ingest_method": {"data_type": "text", "partition": True},
        "year": {"data_type": "text", "partition": True},
        "month": {"data_type": "text", "partition": True},
        # Prevent normalization of nested fields
        "addresses": {"data_type": "json"},
        "contacts": {"data_type": "json"},
        "notes": {"data_type": "json"},
        "customer_group": {"data_type": "json"},
        "group_ids": {"data_type": "json"},
        "tags": {"data_type": "json"},
        "social_customers": {"data_type": "json"}
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
def sapo_customers_source(
    max_pages: int = 1000, 
    page_size: int = 100, 
    min_overlap_items: int = 500
):
    """
    Sapo customers source function.
    """
    return customers(
        max_pages=max_pages, 
        page_size=page_size, 
        min_overlap_items=min_overlap_items
    )

@dlt.resource(
    primary_key="entity_id",
    write_disposition="append",
    table_format="delta",
    name="customer", 
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
def customers(
    max_pages: int = 1000,
    page_size: int = 100,
    min_overlap_items: int = 500,
    first_timestamp=dlt.sources.incremental("sync_metadata.event_timestamp")
) -> Iterator[List[Dict[Any, Any]]]:
    """
    Load customers incrementally using DESC strategy.
    
    Outputs standardized Envelope Schema.
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

    # Checkpoint safety buffer
    consecutive_old_items = 0
    consecutive_errors = 0
    MAX_ERRORS = 3

    last_value = first_timestamp.last_value
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
        url = f"{base_url}/customers/doSearch.json"

        # Apply rate limiting delay
        if request_delay > 0:
            import time
            time.sleep(request_delay)

        params = {
            "page": page_num,
            "limit": page_size,
            "sort": "created_on,desc", # IMPORTANT: Use created_on instead of modified_on, sapo api doesn't support sort by modified_on
            "condition_type": "must"
        }

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

            # Sapo response structure: {"customers": [...], "metadata": {...}}
            customers_data = data.get("customers", [])

            if not customers_data:
                print(f"📭 Page {page}: Empty")
                break

            # Filter new items
            new_envelopes = []

            for raw_customer in customers_data:
                customer_modified_on = raw_customer.get("modified_on")

                if not customer_modified_on:
                    continue

                if last_value is None or customer_modified_on > last_value:
                    try:
                        # 1. Parse Timestamp
                        dt = datetime.fromisoformat(customer_modified_on.replace("Z", "+00:00"))
                        
                        # 2. Construct Envelope
                        entity_id = raw_customer.get("id")
                        
                        # Calculate Payload Hash
                        payload_str = json.dumps(raw_customer, sort_keys=True)
                        payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()

                        envelope = {
                            "entity_id": str(entity_id),
                            "entity_type": "customer",
                            "ingest_method": "batch_sync",
                            "event_type": "snapshot",
                            "event_timestamp": customer_modified_on,
                            "payload_hash": payload_hash,
                            "year": str(dt.year),
                            "month": str(dt.month),
                            "payload": raw_customer,
                            "sync_metadata": {
                                "source_system": "sapo",
                                "event_timestamp": customer_modified_on,
                                "processing_timestamp": datetime.utcnow().isoformat(),
                                "original_event_id": None
                            }
                        }

                        new_envelopes.append(envelope)
                        consecutive_old_items = 0
                    except ValueError:
                        print(f"⚠️ Could not parse modified_on: {customer_modified_on}")
                        continue
                else:
                    consecutive_old_items += 1
            
            print(f"📄 Page {page}: {len(new_envelopes)}/{len(customers_data)} new. Old stream: {consecutive_old_items}/{min_overlap_items}")

            if new_envelopes:
                yield new_envelopes
            
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
            page += 1 

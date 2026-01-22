"""
Sapo History Log Source
Fetches activity logs from Sapo to track changes on entities.
Unified Transaction Log Strategy (Envelope Schema)
"""

import dlt
import requests
import time
import hashlib
import json
from typing import Iterator, Dict, Any, List, Optional
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

def infer_uri(root_type: str, root_id: int) -> Optional[str]:
    """
    Infers the URI for a Sapo entity based on its type and ID.
    """
    if not root_type or not root_id:
        return None
        
    r_type = root_type.lower().strip()
    
    mappings = {
        'order': 'orders',
        'customer': 'customers',
        'product': 'products',
        'variant': 'variants',
        'collect': 'collects',
        'custom_collection': 'custom_collections',
        'smart_collection': 'smart_collections',
        'page': 'pages',
        'blog': 'blogs',
        'article': 'articles',
        'fulfillment': 'fulfillments',
        'purchase_order': 'purchase_orders',
        'stock_adjustment': 'stock_adjustments',
        'delivery_service_provider': 'delivery_service_providers',
        'order_return': 'order_returns',
        'fulfillment_print_forms': 'fulfillment_print_forms',
        'account_authentication': 'account_authentications',
    }
    
    resource = mappings.get(r_type)
    if resource:
        return f"/admin/{resource}/{root_id}.json"
    
    return f"/admin/{r_type}s/{root_id}.json"

@dlt.source
def sapo_history_log_source(
    max_pages: int = 1000, 
    page_size: int = 100,
    min_overlap_items: int = 50,
    limit: int = None,
    debug: bool = False
):
    """
    Sapo history log source function.
    """
    return history_log(
        max_pages=max_pages, 
        page_size=page_size, 
        min_overlap_items=min_overlap_items,
        limit=limit,
        debug=debug
    )

@dlt.resource(
    primary_key="entity_id",
    write_disposition="append",
    table_format="delta",
    columns={
        "entity_id": {"data_type": "text"},
        "entity_type": {"data_type": "text"},
        "payload": {"data_type": "json"},
        "sync_metadata": {"data_type": "json"},
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
def history_log(
    max_pages: int = 1000,
    page_size: int = 20,
    min_overlap_items: int = 50,
    limit: int = None,
    debug: bool = False,
    first_timestamp=dlt.sources.incremental("sync_metadata.event_timestamp")
) -> Iterator[List[Dict[Any, Any]]]:
    """
    Load history logs incrementally and output Envelope Schema.

    Strategy:
    1. API returns logs sorted by newest first (DESC).
    2. We iterate pages 1, 2, 3... (moving backwards in time).
    3. We maintain an incremental state `occur_at` (max date seen previously).
    4. If we encounter items OLDER than `occur_at`, we count them.
    5. If we see `min_overlap_items` old items, we stop.
    """

    try:
        from .client import get_sapo_client
    except ImportError:
        from sapo.client import get_sapo_client

    client = get_sapo_client()
    base_url = client.base_url

    # Special URL for logs as per request
    # "https://fwg.mysapogo.com/admin/settings/get_logs"
    # Usually clients configure base_url to be .../admin. 
    # We need to append "settings/get_logs"
    
    # Check if base_url ends with /admin, if so utilize it
    # If client.base_url already has /orders or similar, we might need to strip.
    # Safe bet: assume client.base_url is top level admin api root or reconstruct.
    # The client.base_url in `client.py` defaults to `https://{domain}/admin`.
    domain_base = base_url.rsplit('/admin', 1)[0]
    logs_url = f"{client.base_url}/settings/get_logs"
    
    print(f"🚀 Starting History Log load from: {logs_url}")
    last_value = first_timestamp.last_value
    print(f"   State (Last occur_at): {last_value}")
    print(f"   Config: page_size={page_size}, min_overlap_items={min_overlap_items}, limit={limit}, debug={debug}")

    session = client.session
    request_delay = client.request_delay

    page = 1
    consecutive_old_items = 0
    consecutive_errors = 0
    MAX_ERRORS = 3
    
    # Statistics
    stats = {
        "processed": 0,
        "yielded": 0,
        "skipped_no_occur_at": 0,
        "skipped_not_new": 0,
        "skipped_parse_error": 0,
        "skipped_no_uri_or_payload": 0,
        "fetched_success": 0,
        "fetched_failure": 0
    }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def fetch_page_with_retry(page_num: int, current_session) -> Dict[str, Any]:

        # Apply rate limiting delay
        if request_delay > 0:
            time.sleep(request_delay)

        params = {
            "page": page_num,
            "limit": page_size
        }

        response = current_session.get(logs_url, params=params, timeout=30)

        # Check for redirects
        if response.url.find("/login") != -1:
            print(f"⚠️ Redirected to login page: {response.url}")
        elif "accessdenied" in response.url:
            raise PermissionError(f"❌ Access Denied: The user does not have permission to access {logs_url}. Redirected to: {response.url}")

            
        if response.status_code == 401 or response.status_code == 403:
             print("🔄 Session expired, refreshing cookies...")
             client.refresh_session(current_session)
             print(f"↻ Retrying with new session...")
             response = current_session.get(logs_url, params=params, timeout=30)
        
        response.raise_for_status()
        return response.json()
    
    def fetch_entity_data(uri: str, current_session) -> Optional[Dict[str, Any]]:
        """Fetching full entity state"""
        if not uri:
            return None
        target_url = f"{domain_base}{uri}"
        try:
            if request_delay > 0:
                time.sleep(request_delay)
            resp = current_session.get(target_url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                return None
        except Exception:
            return None

    while page <= max_pages:
        try:
            data = fetch_page_with_retry(page, session)
            consecutive_errors = 0
            # User response structure: { "logs": [...], "pageModel": {...} }
            logs_list = data.get("logs", [])
            
            if not logs_list:
                print(f"📭 Page {page}: Empty")
                break
            
            new_envelopes = []
            
            for item in logs_list:
                item_occur_at = item.get("occurAt")

                stats["processed"] += 1
                if not item_occur_at:
                    stats["skipped_no_occur_at"] += 1
                    continue
                
                # Check Limit Early
                if limit and (stats["yielded"] + len(new_envelopes)) >= limit:
                    # We have enough pending envelopes to reach the limit
                    # Stop processing this page
                    # The yield loop below will yield up to limit and stop
                    if debug:
                        print(f"   🛑 Limit of {limit} will be reached with current batch.")
                    break
                
                # Check Incremental
                is_new = False
                if last_value is None:
                    is_new = True
                else:
                    # String comparison for ISO 8601 works
                    if item_occur_at > last_value:
                        is_new = True
                    else:
                        is_new = False
                
                if debug and not is_new:
                     # Verbose: show we skipped
                     # print(f"   Skipold: {item_occur_at} <= {last_value}")
                     pass

                if is_new:
                    try:
                        # 1. Parse Date for Partitioning
                        dt = datetime.fromisoformat(item_occur_at.replace("Z", "+00:00"))
                        
                        # 2. Prepare Envelope
                        root_id = item.get("rootId")
                        root_type = item.get("rootType", "").lower() # Normalize
                        inferred_uri = infer_uri(root_type, root_id)
                        
                        if debug:
                            print(f"   Item {item.get('id')} [{item_occur_at}] -> {root_type}:{root_id}")
                            if not inferred_uri:
                                print(f"   ⚠️ Could not infer URI for {root_type}:{root_id}")

                        # Fetch Entity State (Payload)
                        entity_payload = None
                        if inferred_uri:
                            if debug:
                                print(f"   🔎 Fetching entity: {inferred_uri}")
                            raw_entity_data = fetch_entity_data(inferred_uri, session)
                            if raw_entity_data:
                                stats["fetched_success"] += 1
                                # Often the data is wrapped { "order": { ... } }
                                # We want the inner dict if possible?
                                # `webhook` puts { ... } directly.
                                # `orders.py` puts { ... } directly.
                                # `fetch_entity_data` returns { "order": { ... } } usually.
                                # Let's try to unwrap if 1 key matches singular entity type?
                                # For safety, let's keep it as is, or normalize later.
                                # The Unified Schema expects `payload` to be THE entity.
                                # If I have { "order": {...} }, I should probably unwrap it to match Batch Sync which returns {...}.
                                keys = list(raw_entity_data.keys())
                                if len(keys) == 1 and keys[0].lower() == root_type:
                                    entity_payload = raw_entity_data[keys[0]]
                                else:
                                    entity_payload = raw_entity_data
                            else:
                                stats["fetched_failure"] += 1
                                if debug:
                                    print(f"      ❌ Failed to fetch {inferred_uri}")
                        
                        if not entity_payload:
                             if debug:
                                 print(f"   ⚠️ Skipping {root_type} {root_id}: No entity data found.")
                             stats["skipped_no_uri_or_payload"] += 1
                             continue

                        # Calculate Payload Hash
                        payload_str = json.dumps(entity_payload, sort_keys=True)
                        payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()

                        envelope = {
                            "entity_id": str(root_id),
                            "entity_type": root_type,
                            "ingest_method": "history_log",
                            "event_type": str(item.get("actionName")),
                            "event_timestamp": item_occur_at,
                            "payload_hash": payload_hash,
                            "year": str(dt.year),
                            "month": str(dt.month),
                            "payload": entity_payload,
                            "sync_metadata": {
                                "source_system": "sapo",
                                "source": "history_log",
                                "event_timestamp": item_occur_at,
                                "processing_timestamp": datetime.utcnow().isoformat(),
                                "original_event_id": str(item.get("id")),
                                # Store other log details if needed
                                "actor_name": item.get("actorName"),
                                "description": item.get("description")
                            }
                        }
                        
                        if debug:
                             print(f"      ✅ Prepared envelope for {root_type}:{root_id}")

                        new_envelopes.append(envelope)
                        consecutive_old_items = 0 
                    except ValueError:
                        print(f"⚠️ Date parse error: {item_occur_at}")
                        stats["skipped_parse_error"] += 1
                        continue
                else:
                    stats["skipped_not_new"] += 1
                    consecutive_old_items += 1
            
            print(f"📄 Page {page}: {len(new_envelopes)}/{len(logs_list)} new. Safety overlap: {consecutive_old_items}/{min_overlap_items}")

            if new_envelopes:
                for env in new_envelopes:
                    if limit and stats["yielded"] >= limit:
                        print(f"🛑 Limit of {limit} reached.")
                        break

                    # Dynamic Table Name Routing based on entity_type
                    raw_type = env["entity_type"]
                    if raw_type in ["order", "orders"]:
                        table_name = "order"
                    elif raw_type in ["customer", "customers"]:
                        table_name = "customer"
                    elif raw_type in ["product", "products"]:
                        table_name = "product"
                    else:
                        table_name = raw_type if raw_type else "history_log"
                    
                    yield dlt.mark.with_table_name(env, table_name)
                    stats["yielded"] += 1
            
            if limit and stats["yielded"] >= limit:
                break
            
            if consecutive_old_items >= min_overlap_items:
                 print(f"✅ Early stop triggered. Reached {consecutive_old_items} old items.")
                 break
            
            page += 1
            
        except Exception as e:
            print(f"❌ Error at page {page}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= MAX_ERRORS:
                print("Too many errors, giving up.")
                break
            page += 1

    print("\n📊 Run Summary:")
    print(f"Items Processed from API: {stats['processed']}")
    print(f"Items Yielded:            {stats['yielded']}")
    print(f"Entities Fetched Successfully: {stats['fetched_success']}")
    print(f"Skipped (No occurAt):      {stats['skipped_no_occur_at']}")
    print(f"Skipped (Not New):         {stats['skipped_not_new']}")
    print(f"Skipped (Parse Error):     {stats['skipped_parse_error']}")
    print(f"Skipped (No URI/Payload):  {stats['skipped_no_uri_or_payload']}")


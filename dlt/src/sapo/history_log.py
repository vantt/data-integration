"""
Sapo History Log Source
Fetches activity logs from Sapo to track changes on entities.
"""

import dlt
import requests
import time
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
    
    Args:
        root_type: The type of the entity (e.g., 'order', 'customer', 'product')
        root_id: The ID of the entity
        
    Returns:
        The inferred API URI string, or None if unknown.
    """
    if not root_type or not root_id:
        return None
        
    # Normalize type just in case
    r_type = root_type.lower().strip()
    
    mappings = {
        'order': 'orders',
        'customer': 'customers',
        'product': 'products',
        'variant': 'variants', # Note: variants usually need product_id context for full path, but checking single resource access
        'collect': 'collects',
        'custom_collection': 'custom_collections',
        'smart_collection': 'smart_collections',
        'page': 'pages',
        'blog': 'blogs',
        'article': 'articles',
        # Add more mappings as discovered
    }
    
    resource = mappings.get(r_type)
    if resource:
        return f"/admin/{resource}/{root_id}.json"
    
    # Fallback/Generic heuristic: add 's' ?
    # Safest is to return generic structure or None
    return f"/admin/{r_type}s/{root_id}.json"

@dlt.source
def sapo_history_log_source(
    max_pages: int = 1000, 
    page_size: int = 20, # API fixed limit seems to be 20 for this endpoint? User said limit=20.
    min_overlap_items: int = 50
):
    """
    Sapo history log source function.
    """
    return history_log(
        max_pages=max_pages, 
        page_size=page_size, 
        min_overlap_items=min_overlap_items
    )

@dlt.resource(
    primary_key="id",
    write_disposition="append",
    table_format="delta",
    columns={
        "id": {"data_type": "bigint"},
        "tenant_id": {"data_type": "bigint"},
        "occur_at": {"data_type": "timestamp"},
        "entity_type": {"data_type": "text"}, # Partition removed (handled by table name)
        "root_id": {"data_type": "bigint"},
        "action_name": {"data_type": "text"},
        "source": {"data_type": "text", "partition": True},
        "year": {"data_type": "text", "partition": True},
        "month": {"data_type": "text", "partition": True},
        # Metadata
        "inferred_uri": {"data_type": "text"},
        # Raw data (json)
        "description_data": {"data_type": "json"},
        "data": {"data_type": "json"}
    }
)
def history_log(
    max_pages: int = 1000,
    page_size: int = 20,
    min_overlap_items: int = 50,
    occur_at=dlt.sources.incremental("occur_at")
) -> Iterator[List[Dict[Any, Any]]]:
    """
    Load history logs incrementally.
    
    Strategy:
    1. API returns logs sorted by newest first (DESC).
    2. We iterate pages 1, 2, 3... (moving backwards in time).
    3. We maintain an incremental state `occur_at` (max date seen previously).
    4. If we encounter items OLDER than `occur_at`, we count them.
    5. If we see `min_overlap_items` old items, we stop.
    """

    # Initialize client
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
    
    logs_url = f"{client.base_url}/settings/get_logs"
    
    print(f"🚀 Starting History Log load from: {logs_url}")
    last_value = occur_at.last_value
    print(f"   State (Last occur_at): {last_value}")
    print(f"   Config: page_size={page_size}, min_overlap_items={min_overlap_items}")

    session = client.session
    request_delay = client.request_delay

    page = 1
    consecutive_old_items = 0
    consecutive_errors = 0
    MAX_ERRORS = 3

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

    while page <= max_pages:
        try:
            data = fetch_page_with_retry(page, session)
            consecutive_errors = 0
            
            # User response structure: { "logs": [...], "pageModel": {...} }
            logs_list = data.get("logs", [])
            
            if not logs_list:
                print(f"📭 Page {page}: Empty")
                break
            
            new_items_batch = []
            
            for item in logs_list:
                item_occur_at = item.get("occurAt")
                
                # Check cleanliness
                if not item_occur_at:
                    continue
                
                # Normalize key names to snake_case for consistency with schema? 
                # DLT might do this automatically if we defined columns, but let's be explicit with the ones we rely on.
                # Actually, DLT's `columns` def simply types them. The dict keys must match.
                # The user provided JSON has camelCase: `occurAt`, `rootType` etc.
                # But our schema uses `occur_at`, `root_type`.
                # We should re-map or update schema. 
                # Best practice: Transform to snake_case in python to match analytics standards.
                
                transformed_item = {
                    "id": item.get("id"),
                    "tenant_id": item.get("tenantId"),
                    "occur_at": item.get("occurAt"),
                    "entity_type": item.get("rootType"), # Renamed from root_type
                    "root_id": item.get("rootId"),
                    "action_name": item.get("actionName"),
                    "description": item.get("description"),
                    "method": item.get("method"),
                    "user_agent": item.get("userAgent"),
                    "ip_address": item.get("ipAddress"),
                    "actor_id": item.get("actorId"),
                    "actor_name": item.get("actorName"),
                    "actor_source": item.get("actorSource"),
                    "description_data": item.get("descriptionData"), # Complex
                    "data": item.get("data") # Complex
                }

                # Infer URI
                transformed_item["inferred_uri"] = infer_uri(transformed_item["entity_type"], transformed_item["root_id"])

                # Incremental Logic
                is_new = False
                if last_value is None:
                    is_new = True
                else:
                    # String comparison for ISO 8601 works
                    if item_occur_at > last_value:
                        is_new = True
                    else:
                        is_new = False
                
                if is_new:
                    # Enrich partition cols
                    try:
                        # "2026-01-20T08:04:22Z"
                        dt = datetime.fromisoformat(item_occur_at.replace("Z", "+00:00"))
                        transformed_item["year"] = str(dt.year)
                        transformed_item["month"] = str(dt.month)
                        transformed_item["source"] = "history_log"
                        
                        new_items_batch.append(transformed_item)
                        consecutive_old_items = 0 
                    except ValueError:
                        print(f"⚠️ Date parse error: {item_occur_at}")
                        continue
                else:
                    consecutive_old_items += 1
            
            print(f"📄 Page {page}: {len(new_items_batch)}/{len(logs_list)} new. Safety overlap: {consecutive_old_items}/{min_overlap_items}")

            if new_items_batch:
                # Yield with dynamic table name based on entity_type
                for item in new_items_batch:
                    raw_type = item.get("entity_type", "").lower()
                    # Enforce singular naming for known entities
                    # If unknown, keep as is (or default to history_log?)
                    if raw_type in ["order", "orders"]:
                        table_name = "order"
                    elif raw_type in ["customer", "customers"]:
                        table_name = "customer"
                    elif raw_type in ["product", "products"]:
                        table_name = "product"
                    else:
                        table_name = raw_type if raw_type else "history_log"
                    
                    yield dlt.mark.with_table_name(item, table_name)
            
            # Early stop
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

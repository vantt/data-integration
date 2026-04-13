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
import random
from typing import Iterator, Dict, Any, List, Optional
from datetime import datetime
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result
)

# ---------------------------------------------------------------------------
# Entity Registry
# Each entry defines how to fetch and route a Sapo entity from history log.
#
#   api_resource : URL path segment for JSON API  /admin/{api_resource}/{id}.json
#   table        : destination table in data lake (None = use root_type as-is)
#   resolve      : "standard"  — fetch /admin/{api_resource}/{root_id}.json
#                  "parent"    — root_id is a child; extract parent ID from log's
#                                `uri` field (e.g. customer_address → customer)
#                  "skip"      — do not fetch (low-value / non-fetchable entity)
#
# Verified against live Sapo JSON endpoints (cookie-based, same as orders).
# Web UI routes may differ (e.g. /admin/shipments/ vs /admin/fulfillments/).
# ---------------------------------------------------------------------------
ENTITY_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --- Core business entities (have batch pipelines) ---
    "order":              {"api_resource": "orders",              "table": "order"},
    "customer":           {"api_resource": "customers",           "table": "customer"},
    "product":            {"api_resource": "products",            "table": "product"},
    "account":            {"api_resource": "accounts",            "table": "account"},

    # --- Logistics & inventory (history_log only) ---
    # Fulfillment = packing slip (kho đóng gói). Shipment info is nested inside.
    # Web UI: /admin/fulfillments (kho) and /admin/shipments (vận chuyển) = same entity.
    "fulfillment":        {"api_resource": "fulfillments",        "table": "fulfillment"},
    "purchase_order":     {"api_resource": "purchase_orders",     "table": "purchase_order"},
    "order_return":       {"api_resource": "order_returns",       "table": "order_return"},
    "stock_adjustment":   {"api_resource": "stock_adjustments",   "table": "stock_adjustment"},

    # --- Reference / config entities ---
    "customer_group":     {"api_resource": "customer_groups",     "table": "customer_group"},
    "price_list":         {"api_resource": "price_lists",         "table": "price_list"},

    # --- Resolved via parent entity ---
    # customer_address: rootId = address_id, but we re-fetch the parent customer.
    # The log's `uri` field contains /admin/customers/{customer_id}/addresses.json
    "customer_address":   {"api_resource": None, "table": "customer", "resolve": "parent",
                           "parent_uri_pattern": "/addresses.json",
                           "parent_uri_replace": ".json"},

    # --- Content / CMS (never observed in history log — URLs unverified) ---
    "page":               {"api_resource": "pages",               "table": "page"},
    "blog":               {"api_resource": "blogs",               "table": "blog"},
    "article":            {"api_resource": "articles",            "table": "article"},
    "custom_collection":  {"api_resource": "custom_collections",  "table": "custom_collection"},
    "smart_collection":   {"api_resource": "smart_collections",   "table": "smart_collection"},
    "collect":            {"api_resource": "collects",            "table": "collect"},
    "variant":            {"api_resource": "variants",            "table": "variant"},

    # --- Low-value / non-fetchable — skip ---
    "fulfillment_print_forms":  {"resolve": "skip"},
    "account_authentication":   {"resolve": "skip"},
    "tenant_role":              {"resolve": "skip"},
    "policy":                   {"resolve": "skip"},
}


def infer_uri(root_type: str, root_id: int, log_item: Optional[Dict] = None) -> Optional[str]:
    """
    Build the JSON API fetch URI for an entity from the history log.

    Returns None when the entity should be skipped or cannot be resolved.
    For "parent" resolve types, extracts the parent URI from the log item's `uri` field.
    """
    if not root_type or not root_id:
        return None

    r_type = root_type.lower().strip()
    entry = ENTITY_REGISTRY.get(r_type)

    if not entry:
        # Unknown type — attempt default pluralisation
        return f"/admin/{r_type}s/{root_id}.json"

    resolve = entry.get("resolve", "standard")

    if resolve == "skip":
        return None

    if resolve == "parent" and log_item:
        source_uri = log_item.get("uri", "")
        pattern = entry.get("parent_uri_pattern", "")
        replacement = entry.get("parent_uri_replace", "")
        if source_uri and pattern and pattern in source_uri:
            return source_uri.replace(pattern, replacement)
        return None

    api_resource = entry.get("api_resource")
    if api_resource:
        return f"/admin/{api_resource}/{root_id}.json"

    return None


def get_table_name(root_type: str) -> str:
    """Resolve the destination table name for an entity type."""
    r_type = root_type.lower().strip() if root_type else ""
    entry = ENTITY_REGISTRY.get(r_type)
    if entry and entry.get("table"):
        return entry["table"]
    return r_type or "unknown"

@dlt.source
def sapo_history_log_source(
    max_pages: int = 1000,
    page_size: int = 100,
    min_overlap_items: int = 50,
    limit: int = None,
    debug: bool = False,
    full_refresh: bool = False
):
    """
    Sapo history log source function.
    """
    return history_log(
        max_pages=max_pages,
        page_size=page_size,
        min_overlap_items=min_overlap_items,
        limit=limit,
        debug=debug,
        full_refresh=full_refresh
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
    full_refresh: bool = False,
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

    When full_refresh=True, the incremental cursor is ignored — all items
    are treated as new. Data is APPENDED (never deleted); dedup in dbt.
    """

    try:
        from .client import get_sapo_client
    except ImportError:
        from sapo.client import get_sapo_client

    client = get_sapo_client()
    base_url = client.base_url
    domain_base = base_url.rsplit('/admin', 1)[0]
    logs_url = f"{client.base_url}/settings/get_logs"

    last_value = None if full_refresh else first_timestamp.last_value

    print(f"🚀 Starting History Log load from: {logs_url}")
    print(f"   State (Last occur_at): {last_value} {'[FULL REFRESH — cursor ignored]' if full_refresh else ''}")
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

    def _delay_with_jitter():
        """Apply rate-limiting delay with random jitter to avoid predictable patterns."""
        if request_delay > 0:
            jitter = random.uniform(0, request_delay * 0.3)
            time.sleep(request_delay + jitter)

    def _handle_auth_response(response, current_session, context: str):
        """
        Check for auth issues (redirect to login, 401, 403).
        Returns refreshed response on recoverable auth failure, or raises.
        """
        if "accessdenied" in response.url:
            raise PermissionError(
                f"Access Denied for {context}. Redirected to: {response.url}"
            )
        if "/login" in response.url or response.status_code in (401, 403):
            print(f"🔄 Session expired ({context}), refreshing cookies...")
            client.refresh_session(current_session)
            return None  # Signal caller to retry
        return response

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, PermissionError))
    )
    def fetch_page_with_retry(page_num: int, current_session) -> Dict[str, Any]:
        _delay_with_jitter()
        params = {"page": page_num, "limit": page_size}
        response = current_session.get(logs_url, params=params, timeout=30)

        checked = _handle_auth_response(response, current_session, f"page {page_num}")
        if checked is None:
            # Session refreshed — retry immediately
            _delay_with_jitter()
            response = current_session.get(logs_url, params=params, timeout=30)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 30))
            print(f"⚠️ Rate limited on page {page_num}, waiting {retry_after}s...")
            time.sleep(retry_after)
            raise requests.RequestException("429 rate limited")

        response.raise_for_status()
        return response.json()

    def _should_retry_entity(result):
        """Retry on None (transient failure), but not on __not_found or valid data."""
        return result is None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=3, max=15),
        retry=retry_if_result(_should_retry_entity) | retry_if_exception_type(requests.RequestException)
    )
    def _fetch_entity_inner(target_url: str, uri: str, current_session) -> Optional[Dict[str, Any]]:
        """Inner fetch with tenacity retry. Returns None to signal retry."""
        _delay_with_jitter()
        resp = current_session.get(target_url, timeout=15)
        _delay_with_jitter()
        resp = current_session.get(target_url, timeout=15)

        checked = _handle_auth_response(resp, current_session, uri)
        if checked is None:
            return None  # Session refreshed → tenacity retries

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 30))
            print(f"⚠️ Rate limited on {uri}, waiting {retry_after}s...")
            time.sleep(retry_after)
            raise requests.RequestException("429 rate limited")

        if resp.status_code == 404:
            return {"__not_found": True}  # Not retryable

        if resp.status_code == 200:
            return resp.json()

        return None  # Other errors → tenacity retries

    def fetch_entity_data(uri: str, current_session) -> Optional[Dict[str, Any]]:
        """Fetch full entity state. Wraps retry logic, returns None on final failure."""
        if not uri:
            return None
        target_url = f"{domain_base}{uri}"
        try:
            return _fetch_entity_inner(target_url, uri, current_session)
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
                
                if is_new:
                    # Any new item (even if later skipped) proves we haven't
                    # paginated past the new-data frontier yet.
                    consecutive_old_items = 0
                    try:
                        # 1. Parse Date for Partitioning
                        dt = datetime.fromisoformat(item_occur_at.replace("Z", "+00:00"))
                        
                        # 2. Prepare Envelope
                        root_id = item.get("rootId")
                        root_type = item.get("rootType", "").lower() # Normalize

                        # Resolve fetch URI via entity registry
                        inferred_uri = infer_uri(root_type, root_id, log_item=item)

                        if inferred_uri is None:
                            # Registry returned None — either "skip" type or unresolvable parent
                            entry = ENTITY_REGISTRY.get(root_type, {})
                            if entry.get("resolve") == "skip":
                                if debug:
                                    print(f"   Skipping low-value type: {root_type}")
                            else:
                                if debug:
                                    print(f"   ⚠️ Could not resolve URI for {root_type}:{root_id}")
                            stats["skipped_no_uri_or_payload"] += 1
                            continue

                        if debug:
                            print(f"   🔎 {item.get('id')} [{item_occur_at}] {root_type}:{root_id} -> {inferred_uri}")
                        try:
                            raw_entity_data = fetch_entity_data(inferred_uri, session)
                        except Exception as fetch_err:
                            if debug:
                                print(f"      ❌ Fetch error {inferred_uri}: {fetch_err}")
                            stats["fetched_failure"] += 1
                            continue

                        # Handle non-retryable 404 (deleted entity)
                        if isinstance(raw_entity_data, dict) and raw_entity_data.get("__not_found"):
                            if debug:
                                print(f"      ⚠️ 404 Not Found: {inferred_uri}")
                            stats["fetched_failure"] += 1
                            continue

                        entity_payload = None
                        if raw_entity_data:
                            stats["fetched_success"] += 1
                            # API returns wrapped: {"order": {...}}, {"customer": {...}}, etc.
                            # Unwrap if single top-level key whose value is a dict.
                            keys = list(raw_entity_data.keys())
                            if len(keys) == 1 and isinstance(raw_entity_data[keys[0]], dict):
                                entity_payload = raw_entity_data[keys[0]]
                            else:
                                entity_payload = raw_entity_data
                        else:
                            stats["fetched_failure"] += 1
                            if debug:
                                print(f"      ❌ Failed to fetch {inferred_uri} after retries")

                        if not entity_payload:
                             if debug:
                                 print(f"   ⚠️ Skipping {root_type} {root_id}: No entity data found.")
                             stats["skipped_no_uri_or_payload"] += 1
                             continue

                        # Calculate Payload Hash
                        payload_str = json.dumps(entity_payload, sort_keys=True)
                        payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()

                        # For "parent" resolve (e.g. customer_address → customer),
                        # use the payload's actual id as entity_id, and the table's entity type.
                        entry = ENTITY_REGISTRY.get(root_type, {})
                        effective_entity_id = str(entity_payload.get("id", root_id))
                        effective_entity_type = entry.get("table", root_type)

                        envelope = {
                            "entity_id": effective_entity_id,
                            "entity_type": effective_entity_type,
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

                    # Route to destination table via entity registry
                    table_name = get_table_name(env["entity_type"])
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


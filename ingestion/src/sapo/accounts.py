"""
Sapo Accounts Source - Batch Sync Implementation
Unified Transaction Log Strategy (Envelope Schema)

SAPO Account Response Structure:
{
    "metadata": {"total":30,"page":1,"limit":2},
    "accounts": [
        {
            "id": 1280476,
            "tenant_id": 445355,
            "modified_on": "2026-01-19T05:03:59Z",
            "created_on": "2026-01-19T05:02:47Z",
            "full_name": "Văn Operator",
            "email": null,
            "mobile": "0355514031",
            "status": "active",
            ...
        }
    ]
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
def sapo_accounts_source(
    max_pages: int = 100, 
    page_size: int = 50
):
    """
    Sapo Accounts source function.
    """
    return accounts(
        max_pages=max_pages, 
        page_size=page_size
    )

@dlt.resource(
    primary_key="entity_id",
    write_disposition="append",
    table_format="delta",
    name="account", 
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
def accounts(
    max_pages: int = 100,
    page_size: int = 50,
    first_timestamp=dlt.sources.incremental("sync_metadata.event_timestamp")
) -> Iterator[List[Dict[Any, Any]]]:
    """
    Load accounts incrementally.
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
    # For accounts, overlapping isn't as critical as orders but we use standard logic
    consecutive_errors = 0
    MAX_ERRORS = 3

    last_value = first_timestamp.last_value
    print(f"🚀 Starting incremental load for Accounts from: {last_value}")

    session = client.session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def fetch_page_with_retry(page_num: int, current_session) -> Dict[str, Any]:
        """Fetch single page with exponential backoff retry"""
        url = f"{base_url}/accounts.json"

        # Apply rate limiting delay
        if request_delay > 0:
            import time
            time.sleep(request_delay)

        params = {
            "page": page_num,
            "limit": page_size,
            # Sapo Accounts API might not support Sort By Modified desc, usually just ID or Created.
            # Assuming standard list endpoint behavior. 
            # If Sort isn't supported, fully reloading or relying on natural order (usually ID asc or Created asc) might be needed.
            # Checking docs/standard: Sapo list usually default sort by ID/Created.
            # FOR SAFETY: Fetch ALL (since accounts list is small) or assume standard pagination.
            # NOTE: User provided url `accounts.json?limit=xx&page=y`.
        }

        response = current_session.get(url, params=params, timeout=30)

        if response.status_code == 401 or response.status_code == 403:
             print("🔄 Session expired, refreshing cookies...")
             client.refresh_session(current_session)
             response = current_session.get(url, params=params, timeout=30)

        response.raise_for_status()
        return response.json()

    while page <= max_pages:
        try:
            data = fetch_page_with_retry(page, session)
            consecutive_errors = 0

            # Sapo response structure: {"accounts": [...], "metadata": {...}}
            items_data = data.get("accounts", [])

            if not items_data:
                print(f"📭 Page {page}: Empty")
                break

            new_envelopes = []

            for raw_item in items_data:
                # Use modified_on for change tracking
                item_modified_on = raw_item.get("modified_on")
                if not item_modified_on:
                    item_modified_on = raw_item.get("created_on")

                if not item_modified_on:
                     # If no timestamps, force ingest (or skip?)
                     continue

                # Incremental Check
                if last_value is None or item_modified_on > last_value:
                    try:
                        # 1. Parse Timestamp
                        dt = datetime.fromisoformat(item_modified_on.replace("Z", "+00:00"))
                        
                        # 2. Construct Envelope
                        entity_id = raw_item.get("id")
                        
                        # Calculate Payload Hash
                        payload_str = json.dumps(raw_item, sort_keys=True)
                        payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()

                        envelope = {
                            "entity_id": str(entity_id),
                            "entity_type": "account",
                            "ingest_method": "batch_sync",
                            "event_type": "snapshot",
                            "event_timestamp": item_modified_on,
                            "payload_hash": payload_hash,
                            "year": str(dt.year),
                            "month": str(dt.month),
                            "payload": raw_item,
                            "sync_metadata": {
                                "source_system": "sapo",
                                "event_timestamp": item_modified_on, # Syncing by Modified Time
                                "processing_timestamp": datetime.utcnow().isoformat(),
                            }
                        }

                        new_envelopes.append(envelope)
                    except ValueError:
                         pass
            
            print(f"📄 Page {page}: {len(new_envelopes)}/{len(items_data)} new/updated.")

            if new_envelopes:
                yield new_envelopes
            else:
                 # If no new envelopes, AND we are assuming sorted desc, we could stop.
                 # BUT if API returns ASC order (default), we must read ALL pages.
                 # Given Accounts are small (usually < 100), safer to read all.
                 pass

            page += 1

        except Exception as e:
            print(f"❌ Error at page {page}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= MAX_ERRORS:
                 break
            page += 1

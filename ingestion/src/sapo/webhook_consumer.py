"""
Sapo Webhook Consumer Source
Consumes webhooks from Cloudflare D1 and dispatches them to dynamic tables.
Unified Transaction Log Strategy (Envelope Schema)
"""

import dlt
import requests
import json
import time
import hashlib
from typing import Iterator, Dict, Any, List, Optional
from datetime import datetime

class CloudflareWorkerClient:
    def __init__(self, worker_url: str):
        self.worker_url = worker_url.rstrip('/')

    def poll_messages(self, source_system: str = None, limit: int = 100) -> list:
        """
        Polls for new messages from the worker.
        """
        params = {'limit': limit}
        if source_system:
            params['source_system'] = source_system
        
        url = f"{self.worker_url}/poll"
        try:
            response = requests.get(url, params=params, timeout=30)
            # print(f"Response Status: {response.status_code}")
            # print(f"Response Text: {response.text}")
            response.raise_for_status()
            data = response.json()
            return data.get('messages', [])
        except requests.exceptions.RequestException as e:
            print(f"Error polling messages: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return []

    def batch_ack(self, message_ids: list):
        """
        Acknowledges a batch of messages, deleting them from the source.
        """
        if not message_ids:
            return

        url = f"{self.worker_url}/ack-batch"
        try:
            response = requests.post(url, json={'ids': message_ids}, timeout=30)
            response.raise_for_status()
            print(f"Successfully acknowledged {len(message_ids)} messages.")
        except requests.exceptions.RequestException as e:
            print(f"Error acknowledging messages: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")

@dlt.source
def sapo_webhook_source(worker_url: str, source_system: str = None, poll_limit: int = 100):
    """
    DLT Source that consumes messages from Cloudflare D1 and dispatches to tables.
    """
    return webhook_dispatcher(worker_url, source_system, poll_limit)

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
def webhook_dispatcher(worker_url: str, source_system: str = None, poll_limit: int = 100) -> Iterator[Any]:
    """
    Polls messages and yields them with dynamic table names using Envelope Schema.
    """
    client = CloudflareWorkerClient(worker_url)
    
    print(f"Polling D1 Webhooks from {worker_url}...")
    
    messages = client.poll_messages(source_system=source_system, limit=poll_limit)
    
    if not messages:
        return

    print(f"Received {len(messages)} messages.")
    
    ids_to_ack = []
    
    for msg in messages:
        try:
            # 1. Capture ID for ACK
            msg_id = msg.get('msg_id') or msg.get('id')
            if msg_id:
                ids_to_ack.append(msg_id)
            
            # 2. Determine Entity Type
            entity_type = msg.get('entity_type', 'unknown')
            
            # Singularize
            et_lower = entity_type.lower()
            if et_lower in ['order', 'orders']:
                table_name = 'order'
            elif et_lower in ['customer', 'customers']:
                table_name = 'customer'
            elif et_lower in ['product', 'products']:
                table_name = 'product'
            else:
                table_name = et_lower
            
            # 3. Parse Payload
            # The 'payload' column in D1 is a JSON string containing the wrapper:
            # { "source_system": "...", "entity_type": "...", "action": "...", "received_at": "...", "payload": { ...real_data... } }
            raw_payload_str = msg.get('payload')
            wrapper = {}
            if isinstance(raw_payload_str, str):
                try:
                    wrapper = json.loads(raw_payload_str)
                except json.JSONDecodeError:
                    print(f"⚠️ Failed to decode payload for {msg_id}. Skipping. Raw content: {raw_payload_str[:100]}...")
                    continue
            elif isinstance(raw_payload_str, dict):
                wrapper = raw_payload_str
            else:
                print(f"Unexpected payload type for {msg_id}: {type(raw_payload_str)}. Skipping.")
                continue
            
            # Extract Inner Payload (The actual Entity)
            inner_payload = wrapper.get('payload')
            if not isinstance(inner_payload, dict):
                 # Fallback: maybe the wrapper IS the payload if structure changed?
                 # But based on index.ts, it is nested.
                 print(f"⚠️ No inner payload dict found for {msg_id}. Wrapper keys: {wrapper.keys()}. Skipping.")
                 continue

            # 4. Extract Entity ID
            entity_id = inner_payload.get('id')
            if not entity_id:
                print(f"⚠️ No entity ID in inner payload for {msg_id}. Payload keys: {inner_payload.keys()}. Skipping.")
                continue

            # 5. Metadata & Partitioning
            # received_at is in the WRAPPER, not the D1 row message
            received_at_str = wrapper.get('received_at')
            if received_at_str:
                try:
                    dt = datetime.fromisoformat(received_at_str.replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.utcnow()
            else:
                dt = datetime.utcnow()

            # 6. Construct Envelope
            
            # Calculate Payload Hash
            payload_str = json.dumps(inner_payload, sort_keys=True)
            payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()
            
            event_type = wrapper.get("action", "unknown")

            envelope = {
                "entity_id": str(entity_id),
                "entity_type": table_name,
                "ingest_method": "webhook",
                "event_type": event_type,
                "event_timestamp": received_at_str or datetime.utcnow().isoformat(),
                "payload_hash": payload_hash,
                "year": str(dt.year),
                "month": str(dt.month),
                "payload": inner_payload, # Use the unwrapped entity data
                "sync_metadata": {
                    "source_system": source_system or "sapo", # Use arg or default
                    "event_timestamp": received_at_str or datetime.utcnow().isoformat(),
                    "processing_timestamp": datetime.utcnow().isoformat(),
                    "original_event_id": str(msg_id)
                }
            }

            yield dlt.mark.with_table_name(envelope, table_name)
            
        except Exception as e:
            print(f"Error processing message {msg.get('msg_id')}: {e}")
            # Continue to next message, don't break batch
    
    # 7. ACK processed messages
    # In dlt resource, we yield items. The pipeline runs.
    # We should ACK *after* successful yield? 
    # Technically dlt runs extraction first. If we ACK here, it means we ACK when extracted.
    # If load fails later, we lose data? 
    # Ideally we use `dlt.state` or similar, but for now, ACK-ing after yield is 'at-most-once' risk.
    # To do 'at-least-once' safely, we should ideally ACK in a later stage or separate step.
    # However, given this is an immediate generator, if this function finishes without error, 
    # it means items were yielded to the pipeline.
    # A safer approach is to ACK only if we are sure?
    # For now, let's ACK here. If `pipeline.run` crashes *during* load, we might have ACKed data that wasn't saved.
    # IMPROVEMENT: Use `dlt` state or post-load hook. 
    # Current limitation: We ACK immediately after fetching/yielding in this batch.
    
    if ids_to_ack:
        client.batch_ack(ids_to_ack)

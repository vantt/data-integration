"""
Sapo Webhook Consumer Source
Consumes webhooks from Cloudflare D1 and dispatches them to dynamic tables.
Unified Transaction Log Strategy (Envelope Schema)
"""

import dlt
import requests
import json
import time
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
        "source": {"data_type": "text", "partition": True},
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
            # Important for Envelope: `payload` MUST be a dict (the entity)
            raw_payload = msg.get('payload')
            if isinstance(raw_payload, str):
                try:
                    payload_dict = json.loads(raw_payload)
                except json.JSONDecodeError:
                    print(f"⚠️ Failed to decode payload for {msg_id}. Skipping.")
                    continue
            elif isinstance(raw_payload, dict):
                payload_dict = raw_payload
            else:
                payload_dict = {}

            # 4. Extract Entity ID
            # Usually in payload['id']
            entity_id = payload_dict.get('id')
            if not entity_id:
                # Fallback to msg_id if no entity id? No, that breaks the "Entity Log" concept.
                # If we cannot identify the entity, it's garbage.
                print(f"⚠️ No entity ID in payload for {msg_id}. Skipping.")
                continue

            # 5. Metadata & Partitioning
            received_at_str = msg.get('received_at')
            if received_at_str:
                try:
                    dt = datetime.fromisoformat(received_at_str.replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.utcnow()
            else:
                dt = datetime.utcnow()

            # 6. Construct Envelope
            envelope = {
                "entity_id": str(entity_id),
                "entity_type": table_name, # Normalized type
                "source": "webhook",
                "year": str(dt.year),
                "month": str(dt.month),
                "payload": payload_dict,
                "sync_metadata": {
                    "source": "webhook",
                    "event_type": msg.get("action", "unknown"), # e.g. orders/create
                    "event_timestamp": received_at_str or datetime.utcnow().isoformat(),
                    "processing_timestamp": datetime.utcnow().isoformat(),
                    "original_event_id": str(msg_id),
                    "topic": msg.get("topic"),
                    "webhook_id": msg.get("webhook_id")
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

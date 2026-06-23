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
from datetime import datetime, timezone

class CloudflareWorkerClient:
    def __init__(self, worker_url: str):
        self.worker_url = worker_url.rstrip('/')
        self.session = requests.Session()
        # Cloudflare Bot Fight Mode blocks default python-requests UA (error-1010).
        self.session.headers.update({"User-Agent": "DataIntegration-Worker/1.0"})

    def poll_messages(self, source_system: str = None, limit: int = 100) -> list:
        """
        Polls for new messages from the worker.
        """
        params = {'limit': limit}
        if source_system:
            params['source_system'] = source_system

        url = f"{self.worker_url}/poll"
        try:
            response = self.session.get(url, params=params, timeout=30)
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
        Raises on failure so the caller can decide to retry or alert.
        """
        if not message_ids:
            return

        url = f"{self.worker_url}/ack-batch"
        try:
            response = self.session.post(url, json={'ids': message_ids}, timeout=30)
            response.raise_for_status()
            print(f"Successfully acknowledged {len(message_ids)} messages.")
        except requests.exceptions.RequestException as e:
            print(f"Error acknowledging messages: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            raise  # Let caller decide on retry/alert

class PendingAck:
    """Holds client + message IDs that must be ACKed after a successful dlt load."""
    def __init__(self, client: "CloudflareWorkerClient"):
        self.client = client
        self.ids: List[Any] = []

    def ack(self) -> None:
        """Send batch ACK. Raises on failure so the caller can decide to retry/alert."""
        if self.ids:
            self.client.batch_ack(self.ids)


def build_sapo_webhook_source(
    worker_url: str,
    source_system: str = None,
    poll_limit: int = 100,
) -> tuple:
    """
    Returns (dlt_source, pending_ack).

    Caller MUST call pending_ack.ack() AFTER pipeline.run() returns successfully
    to achieve at-least-once delivery.  If pipeline.run() raises, do NOT ack —
    messages stay in D1 and will be re-delivered on the next poll.
    """
    client = CloudflareWorkerClient(worker_url)
    pending = PendingAck(client)
    source = _sapo_webhook_source_internal(client, pending, source_system, poll_limit)
    return source, pending


# Legacy single-return entry-point kept for backward compatibility.
# WARNING: ACK fires during extraction (before load completes) → at-most-once risk.
# Prefer build_sapo_webhook_source() for at-least-once semantics.
@dlt.source
def sapo_webhook_source(worker_url: str, source_system: str = None, poll_limit: int = 100):
    """
    DLT Source that consumes messages from Cloudflare D1 and dispatches to tables.
    """
    return webhook_dispatcher(worker_url, source_system, poll_limit)


@dlt.source
def _sapo_webhook_source_internal(
    client: "CloudflareWorkerClient",
    pending: PendingAck,
    source_system: str = None,
    poll_limit: int = 100,
):
    return _webhook_dispatcher_internal(client, pending, source_system, poll_limit)


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
def _webhook_dispatcher_internal(
    client: "CloudflareWorkerClient",
    pending: PendingAck,
    source_system: str = None,
    poll_limit: int = 100,
) -> Iterator[Any]:
    """
    Internal dispatcher used by build_sapo_webhook_source().
    Yields envelopes; does NOT ack — the caller acks after pipeline.run().
    """
    print(f"Polling D1 Webhooks from {client.worker_url}...")
    messages = client.poll_messages(source_system=source_system, limit=poll_limit)

    if not messages:
        return

    print(f"Received {len(messages)} messages.")

    for msg in messages:
        try:
            msg_id = msg.get('msg_id') or msg.get('id')
            entity_type = msg.get('entity_type', 'unknown')
            et_lower = entity_type.lower()
            if et_lower in ['order', 'orders']:
                table_name = 'order'
            elif et_lower in ['customer', 'customers']:
                table_name = 'customer'
            elif et_lower in ['product', 'products']:
                table_name = 'product'
            else:
                table_name = et_lower

            raw_payload_str = msg.get('payload')
            wrapper = {}
            if isinstance(raw_payload_str, str):
                try:
                    wrapper = json.loads(raw_payload_str)
                except json.JSONDecodeError:
                    print(f"⚠️ Failed to decode payload for {msg_id}. Skipping. Raw: {raw_payload_str[:100]}...")
                    continue
            elif isinstance(raw_payload_str, dict):
                wrapper = raw_payload_str
            else:
                print(f"Unexpected payload type for {msg_id}: {type(raw_payload_str)}. Skipping.")
                continue

            inner_payload = wrapper.get('payload')
            if not isinstance(inner_payload, dict):
                print(f"⚠️ No inner payload dict for {msg_id}. Wrapper keys: {list(wrapper.keys())}. Skipping.")
                continue

            entity_id = inner_payload.get('id')
            if not entity_id:
                print(f"⚠️ No entity ID in inner payload for {msg_id}. Payload keys: {list(inner_payload.keys())}. Skipping.")
                continue

            received_at_str = wrapper.get('received_at')
            if received_at_str:
                try:
                    dt = datetime.fromisoformat(received_at_str.replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.now(timezone.utc)
            else:
                dt = datetime.now(timezone.utc)

            payload_str = json.dumps(inner_payload, sort_keys=True)
            payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()
            event_type = wrapper.get("action", "unknown")
            now_utc = datetime.now(timezone.utc).isoformat()

            envelope = {
                "entity_id": str(entity_id),
                "entity_type": table_name,
                "ingest_method": "webhook",
                "event_type": event_type,
                "event_timestamp": received_at_str or now_utc,
                "payload_hash": payload_hash,
                "year": str(dt.year),
                "month": str(dt.month),
                "payload": inner_payload,
                "sync_metadata": {
                    "source_system": source_system or "sapo_v2",
                    "event_timestamp": received_at_str or now_utc,
                    "processing_timestamp": now_utc,
                    "original_event_id": str(msg_id)
                }
            }

            if msg_id:
                pending.ids.append(msg_id)
            yield dlt.mark.with_table_name(envelope, table_name)

        except Exception as e:
            print(f"Error processing message {msg.get('msg_id')}: {e}")


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
    Legacy dispatcher.  Kept for backward compatibility with existing Dagster sensors
    that call sapo_webhook_source() directly.
    ACK fires after extraction (before load) — at-most-once semantics.
    Prefer build_sapo_webhook_source() for at-least-once delivery.
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
            msg_id = msg.get('msg_id') or msg.get('id')
            entity_type = msg.get('entity_type', 'unknown')
            et_lower = entity_type.lower()
            if et_lower in ['order', 'orders']:
                table_name = 'order'
            elif et_lower in ['customer', 'customers']:
                table_name = 'customer'
            elif et_lower in ['product', 'products']:
                table_name = 'product'
            else:
                table_name = et_lower

            raw_payload_str = msg.get('payload')
            wrapper = {}
            if isinstance(raw_payload_str, str):
                try:
                    wrapper = json.loads(raw_payload_str)
                except json.JSONDecodeError:
                    print(f"⚠️ Failed to decode payload for {msg_id}. Skipping. Raw: {raw_payload_str[:100]}...")
                    continue
            elif isinstance(raw_payload_str, dict):
                wrapper = raw_payload_str
            else:
                print(f"Unexpected payload type for {msg_id}: {type(raw_payload_str)}. Skipping.")
                continue

            inner_payload = wrapper.get('payload')
            if not isinstance(inner_payload, dict):
                print(f"⚠️ No inner payload dict for {msg_id}. Wrapper keys: {list(wrapper.keys())}. Skipping.")
                continue

            entity_id = inner_payload.get('id')
            if not entity_id:
                print(f"⚠️ No entity ID in inner payload for {msg_id}. Payload keys: {list(inner_payload.keys())}. Skipping.")
                continue

            received_at_str = wrapper.get('received_at')
            if received_at_str:
                try:
                    dt = datetime.fromisoformat(received_at_str.replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.now(timezone.utc)
            else:
                dt = datetime.now(timezone.utc)

            payload_str = json.dumps(inner_payload, sort_keys=True)
            payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()
            event_type = wrapper.get("action", "unknown")
            now_utc = datetime.now(timezone.utc).isoformat()

            envelope = {
                "entity_id": str(entity_id),
                "entity_type": table_name,
                "ingest_method": "webhook",
                "event_type": event_type,
                "event_timestamp": received_at_str or now_utc,
                "payload_hash": payload_hash,
                "year": str(dt.year),
                "month": str(dt.month),
                "payload": inner_payload,
                "sync_metadata": {
                    "source_system": source_system or "sapo_v2",
                    "event_timestamp": received_at_str or now_utc,
                    "processing_timestamp": now_utc,
                    "original_event_id": str(msg_id)
                }
            }

            if msg_id:
                ids_to_ack.append(msg_id)
            yield dlt.mark.with_table_name(envelope, table_name)

        except Exception as e:
            print(f"Error processing message {msg.get('msg_id')}: {e}")

    # ACK after extraction (at-most-once — use build_sapo_webhook_source for at-least-once)
    if ids_to_ack:
        client.batch_ack(ids_to_ack)

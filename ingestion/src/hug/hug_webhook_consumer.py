"""
Hug Webhook Consumer

Polls Cloudflare D1 queue for source_system='hug' events and lands them
into two parquet datasets:
  - hug_scan       (entity_type='scan')
  - hug_optin_event (entity_type='optin')

Key difference from the Sapo consumer: Hug events are keyed by 'token',
not 'id'. The generic sapo_webhook_source silently drops any event whose
inner payload lacks an 'id' field. This module handles that correctly by
using 'token' as the entity_id for hug events, while leaving sapo untouched.

Reuses CloudflareWorkerClient from the sapo consumer for HTTP transport.
"""

import dlt
import json
import hashlib
from typing import Iterator, Any
from datetime import datetime, timezone

from sapo.webhook_consumer import CloudflareWorkerClient


# Envelope column schema shared between hug_scan and hug_optin_event.
# Matches the sapo envelope shape so dbt staging can follow the same pattern.
_HUG_ENVELOPE_COLUMNS = {
    "entity_id": {"data_type": "text"},       # token value — unique per touchpoint
    "entity_type": {"data_type": "text"},
    "payload": {"data_type": "json"},
    "sync_metadata": {"data_type": "json"},
    "ingest_method": {"data_type": "text", "partition": True},
    "event_type": {"data_type": "text"},
    "event_timestamp": {"data_type": "timestamp"},
    "payload_hash": {"data_type": "text"},
    "year": {"data_type": "text", "partition": True},
    "month": {"data_type": "text", "partition": True},
}


@dlt.source
def hug_webhook_source(worker_url: str, poll_limit: int = 100):
    """
    DLT source for Hug scan and opt-in events from Cloudflare D1.

    Yields to two named tables: 'scan' and 'optin_event'.
    Both are token-keyed (entity_id = token).
    """
    return hug_event_dispatcher(worker_url, poll_limit)


@dlt.resource(
    primary_key="entity_id",
    write_disposition="append",
    table_format="delta",
    columns=_HUG_ENVELOPE_COLUMNS,
)
def hug_event_dispatcher(worker_url: str, poll_limit: int = 100) -> Iterator[Any]:
    """
    Polls D1 for source_system='hug' messages and dispatches to table-named records.

    Hug events carry 'token' as the business key — there is no 'id' field.
    entity_id is set to the token value. Events without a token are logged
    and skipped (they cannot be deduped or acked safely).

    ACK is sent only after all events in the batch have been yielded, so a
    pipeline crash before yield means events will be re-delivered on the next
    poll (at-least-once delivery).
    """
    client = CloudflareWorkerClient(worker_url)

    print("Polling D1 Hug events...")
    messages = client.poll_messages(source_system="hug", limit=poll_limit)

    if not messages:
        print("No Hug events queued.")
        return

    print(f"Received {len(messages)} Hug messages.")

    ids_to_ack = []

    for msg in messages:
        try:
            msg_id = msg.get("msg_id") or msg.get("id")
            entity_type = msg.get("entity_type", "unknown").lower()

            # Only handle known entity types; log and skip anything else.
            if entity_type not in ("scan", "optin"):
                print(
                    f"Unknown Hug entity_type='{entity_type}' for msg_id={msg_id}. Skipping."
                )
                continue

            # Parse the outer wrapper (JSON string → dict)
            raw_payload_str = msg.get("payload")
            wrapper: dict = {}
            if isinstance(raw_payload_str, str):
                try:
                    wrapper = json.loads(raw_payload_str)
                except json.JSONDecodeError:
                    print(
                        f"Failed to decode payload for msg_id={msg_id}. "
                        f"Raw: {str(raw_payload_str)[:120]}. Skipping."
                    )
                    continue
            elif isinstance(raw_payload_str, dict):
                wrapper = raw_payload_str
            else:
                print(
                    f"Unexpected payload type {type(raw_payload_str)} for msg_id={msg_id}. Skipping."
                )
                continue

            inner_payload = wrapper.get("payload")
            if not isinstance(inner_payload, dict):
                print(
                    f"No inner payload dict for msg_id={msg_id}. "
                    f"Wrapper keys: {list(wrapper.keys())}. Skipping."
                )
                continue

            # Hug events use 'token' as their business key (no 'id' field).
            token = inner_payload.get("token")
            if not token:
                print(
                    f"No 'token' in inner payload for msg_id={msg_id}. "
                    f"Payload keys: {list(inner_payload.keys())}. Skipping."
                )
                continue

            # Parse event timestamp from wrapper (set at edge receive time).
            received_at_str = wrapper.get("received_at")
            if received_at_str:
                try:
                    dt = datetime.fromisoformat(received_at_str.replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.now(timezone.utc)
            else:
                dt = datetime.now(timezone.utc)

            payload_str = json.dumps(inner_payload, sort_keys=True)
            payload_hash = hashlib.md5(payload_str.encode("utf-8")).hexdigest()

            # Map entity_type to the dlt table name.
            # 'optin' → table 'optin_event' to match the design name 'hug_optin_event'.
            table_name = "optin_event" if entity_type == "optin" else entity_type  # 'scan'

            envelope = {
                "entity_id": str(token),
                "entity_type": table_name,
                "ingest_method": "webhook",
                "event_type": wrapper.get("action", "unknown"),
                "event_timestamp": received_at_str or dt.isoformat(),
                "payload_hash": payload_hash,
                "year": str(dt.year),
                "month": str(dt.month),
                "payload": inner_payload,
                "sync_metadata": {
                    "source_system": "hug",
                    "event_timestamp": received_at_str or dt.isoformat(),
                    "processing_timestamp": datetime.now(timezone.utc).isoformat(),
                    "original_event_id": str(msg_id),
                },
            }

            if msg_id:
                ids_to_ack.append(msg_id)

            yield dlt.mark.with_table_name(envelope, table_name)

        except Exception as e:
            print(f"Error processing Hug message msg_id={msg.get('msg_id')}: {e}")
            # Continue: don't abort the whole batch for one bad message.

    # ACK only after all yields — if the pipeline crashes during load,
    # events remain in D1 and will be re-delivered on the next poll.
    if ids_to_ack:
        client.batch_ack(ids_to_ack)

"""Inbound adapter: parse FB Messenger webhook payloads → list[ParsedMessage].

Scope (v1): payload JSON → normalised messages.
Live FB Graph API fetch is out of scope (no token on this host).

TODO (live integration): wire a transport layer that either:
  a) Receives the FB webhook POST (verify token + X-Hub-Signature-256), or
  b) Polls GET /{page-id}/conversations?fields=messages{...}&access_token=TOKEN
Both paths produce the same JSON that parse_messenger_webhook already handles.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from domain.entities.conversation import ParsedMessage

log = logging.getLogger(__name__)


def parse_messenger_webhook(payload: dict) -> list[ParsedMessage]:
    """Extract messages from a Facebook Messenger webhook payload.

    Processes message events only; delivery/read receipts and other event
    types are silently skipped. Skips events with invalid timestamps rather
    than falling back to now() and producing incorrect data.

    Thread key is always the customer PSID:
    - Inbound (customer→page): sender.id is the customer PSID.
    - Echo/outbound (page→customer): sender.id is the page; recipient.id is the customer PSID.

    Returns a flat list of ParsedMessage, one per valid message event.
    """
    out: list[ParsedMessage] = []

    for entry in payload.get("entry", []):
        page_id: str = entry.get("id", "")
        for ev in entry.get("messaging", []):
            message = ev.get("message")
            if message is None:
                continue  # delivery/read receipt — skip

            mid: str = message.get("mid", "")
            if not mid:
                continue  # malformed — skip

            ts_ms: int = ev.get("timestamp", 0)
            sent_at = _ms_to_utc(ts_ms)
            if sent_at is None:
                log.warning("messenger parser: skipping mid=%s: invalid timestamp ms=%s", mid, ts_ms)
                continue

            sender_id: str = ev.get("sender", {}).get("id", "")
            recipient_id: str = ev.get("recipient", {}).get("id", "")

            # Echo when is_echo flag is set OR sender is the page itself.
            is_echo: bool = bool(message.get("is_echo")) or sender_id == page_id
            if is_echo:
                direction = "out"
                thread_psid = recipient_id   # customer psid
                sender_ref = sender_id       # page id (actual sender)
            else:
                direction = "in"
                thread_psid = sender_id      # customer psid
                sender_ref = sender_id

            # Serialise attachments as JSON string; empty string when none.
            raw_attachments = message.get("attachments") or []
            attachments = json.dumps(raw_attachments) if raw_attachments else ""

            out.append(ParsedMessage(
                channel="messenger",
                external_thread_id=thread_psid,
                page_id=page_id,
                external_message_id=mid,
                direction=direction,
                sender_ref=sender_ref,
                body=message.get("text", ""),
                attachments=attachments,
                sent_at=sent_at,
            ))

    return out


def _ms_to_utc(ms: int) -> str | None:
    """Convert Unix millisecond timestamp to UTC ISO-8601 string.

    Returns None for ms <= 0 so callers can skip malformed events instead
    of recording wrong timestamps.
    """
    if ms <= 0:
        return None
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"

"""CRM Conversation and Message domain entities — chat threads on external channels.

Pure dataclasses; no HTTP/DB adapter imports.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Channel constants
# ---------------------------------------------------------------------------
CHANNEL_MESSENGER = "messenger"
CHANNEL_SHOPEE = "shopee"
CHANNEL_ZALO = "zalo"
VALID_CHANNELS = [CHANNEL_MESSENGER, CHANNEL_SHOPEE, CHANNEL_ZALO]

# ---------------------------------------------------------------------------
# Conversation status constants
# ---------------------------------------------------------------------------
CONV_STATUS_OPEN = "open"
CONV_STATUS_PENDING = "pending"
CONV_STATUS_CLOSED = "closed"
VALID_CONVERSATION_STATUSES = [CONV_STATUS_OPEN, CONV_STATUS_PENDING, CONV_STATUS_CLOSED]

# ---------------------------------------------------------------------------
# Allowed conversation status transitions
# ---------------------------------------------------------------------------
CONV_ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    CONV_STATUS_OPEN: [CONV_STATUS_PENDING, CONV_STATUS_CLOSED],
    CONV_STATUS_PENDING: [CONV_STATUS_OPEN, CONV_STATUS_CLOSED],
    CONV_STATUS_CLOSED: [CONV_STATUS_OPEN],
}

# ---------------------------------------------------------------------------
# Message direction constants
# ---------------------------------------------------------------------------
DIRECTION_IN = "in"
DIRECTION_OUT = "out"


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

@dataclass
class Conversation:
    """Chat thread between a customer and the shop on an external channel.

    party_id is nullable until the external sender (psid) is resolved to a CRM party.
    """
    conversation_id: str        # UUID
    channel: str                # messenger|shopee|zalo
    external_thread_id: str     # psid (Messenger) / buyer id (Shopee) / user id (Zalo)
    status: str                 # open|pending|closed
    unread_count: int
    created_at: str             # UTC ISO-8601
    updated_at: str             # UTC ISO-8601
    party_id: Optional[str] = None          # FK → crm_party (nullable)
    page_id: Optional[str] = None           # FB page / Shopee shop / Zalo OA identifier
    assignee_user_id: Optional[str] = None  # FK → crm_app_user nullable
    last_message_at: Optional[str] = None   # UTC ISO-8601 nullable


@dataclass
class Message:
    """One inbound or outbound message within a conversation."""
    message_id: str             # UUID
    conversation_id: str        # FK → crm_conversation
    direction: str              # in|out
    sent_at: str                # UTC ISO-8601
    created_at: str             # UTC ISO-8601
    external_message_id: Optional[str] = None  # channel-native message id (idempotency key)
    sender_ref: Optional[str] = None           # psid, page_id, or staff identifier
    body: Optional[str] = None
    attachments: list = field(default_factory=list)  # parsed from JSON array column


@dataclass
class ParsedMessage:
    """Normalised inbound message produced by a chat-source adapter.

    Seam between inbound adapters and the application layer; passed to
    ConversationService.ingest_message before persistence.
    """
    channel: str                # messenger|shopee|zalo
    external_thread_id: str     # psid (sender id for Messenger)
    page_id: str                # FB page / shop / OA id
    external_message_id: str    # channel-native message id
    direction: str              # in|out
    sender_ref: str             # who sent (psid or page_id)
    sent_at: str                # UTC ISO-8601
    body: str = ""
    attachments: str = ""       # JSON array or empty string (raw column value)

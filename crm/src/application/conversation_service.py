"""Application service: chat ingest and inbox management.

Pure domain + ports only; no adapter imports.
"""
from __future__ import annotations

import logging
import uuid
from shared.timestamps import utc_now
from typing import Optional

from domain.entities.conversation import (
    Conversation,
    Message,
    ParsedMessage,
    CONV_ALLOWED_TRANSITIONS,
    VALID_CONVERSATION_STATUSES,
    DIRECTION_IN,
)
from domain.entities.party import Party
from domain.ports.conversation_repository import ConversationRepository
from domain.ports.party_repository import PartyRepository

log = logging.getLogger(__name__)


class ConversationService:
    """Handles chat ingest and inbox operations."""

    def __init__(
        self,
        conv_repo: ConversationRepository,
        party_repo: PartyRepository,
    ) -> None:
        self._conv_repo = conv_repo
        self._party_repo = party_repo

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def ingest_message(self, msg: ParsedMessage) -> None:
        """Process one parsed chat message.

        1. Upsert conversation by (channel, external_thread_id).
        2. Insert message (idempotent on external_message_id).
        3. Update last_message_at (take-max) and unread_count delta.
        4. Resolve psid → party and link if not yet linked.
        """
        if not msg.channel or not msg.external_thread_id:
            raise ValueError("channel and external_thread_id are required")
        if not msg.external_message_id:
            raise ValueError("external_message_id is required")
        if not msg.sent_at:
            raise ValueError("sent_at is required")

        now = utc_now()

        # Step 1: upsert conversation.
        conv = Conversation(
            conversation_id=str(uuid.uuid4()),
            channel=msg.channel,
            external_thread_id=msg.external_thread_id,
            page_id=msg.page_id,
            status="open",
            unread_count=0,
            created_at=now,
            updated_at=now,
        )
        conv_id = self._conv_repo.upsert_conversation(conv)

        # Step 2: insert message (idempotent).
        message = Message(
            message_id=str(uuid.uuid4()),
            conversation_id=conv_id,
            external_message_id=msg.external_message_id,
            direction=msg.direction,
            sender_ref=msg.sender_ref,
            body=msg.body,
            attachments=msg.attachments,
            sent_at=msg.sent_at,
            created_at=now,
        )
        _, inserted = self._conv_repo.insert_message(message)
        if not inserted:
            return  # duplicate — nothing more to do

        # Step 3: advance last_message_at and increment unread_count.
        # unread_delta=1 for inbound only; duplicates are already gated above.
        unread_delta = 1 if msg.direction == DIRECTION_IN else 0
        self._conv_repo.update_conversation_on_message(conv_id, msg.sent_at, unread_delta)

        # Step 4: resolve psid → party (Messenger-specific; harmless for others).
        existing = self._conv_repo.get_conversation_by_id(conv_id)
        if existing is None:
            raise RuntimeError(f"conversation {conv_id!r} not found after upsert")

        # For inbound: customer psid is sender_ref.
        # For echo/outbound: customer psid is external_thread_id (keyed on customer).
        psid_ref = msg.sender_ref if msg.direction == DIRECTION_IN else msg.external_thread_id

        if existing.party_id is None and psid_ref:
            try:
                party = self._party_repo.find_by_identity("psid", psid_ref)
            except Exception as exc:
                log.warning("psid lookup %s: %s", psid_ref, exc)
                party = None
            if party is not None:
                existing.party_id = party.party_id
                self._conv_repo.update_conversation(existing)

    # ------------------------------------------------------------------
    # Inbox
    # ------------------------------------------------------------------

    def list_inbox(
        self,
        assignee_user_id: str = "",
        status: str = "",
    ) -> list[Conversation]:
        """Return conversations filtered by optional assignee and/or status."""
        convs = self._conv_repo.list_conversations(assignee_user_id, status)
        return convs if convs is not None else []

    def list_messages(self, conversation_id: str, limit: int = 100) -> list[Message]:
        """Return messages for a conversation ordered by sent_at ASC."""
        msgs = self._conv_repo.list_messages(conversation_id)
        return (msgs if msgs is not None else [])[:limit]

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def assign_conversation(self, conversation_id: str, assignee_user_id: str) -> None:
        """Assign a conversation to a staff user."""
        conv = self._get_or_raise(conversation_id)
        conv.assignee_user_id = assignee_user_id
        self._conv_repo.update_conversation(conv)

    def set_status(self, conversation_id: str, new_status: str) -> None:
        """Transition a conversation status (open|pending|closed)."""
        if new_status not in VALID_CONVERSATION_STATUSES:
            raise ValueError(f"invalid conversation status {new_status!r}")
        conv = self._get_or_raise(conversation_id)
        allowed = CONV_ALLOWED_TRANSITIONS.get(conv.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"cannot transition conversation from {conv.status!r} to {new_status!r}"
            )
        conv.status = new_status
        self._conv_repo.update_conversation(conv)

    def link_party(self, conversation_id: str, party_id: str) -> None:
        """Directly link a conversation to a known party."""
        conv = self._get_or_raise(conversation_id)
        conv.party_id = party_id
        self._conv_repo.update_conversation(conv)

    def resolve_party_from_external_id(
        self, channel: str, sender_ref: str
    ) -> Optional[Party]:
        """Look up a party by channel identity (e.g. psid for Messenger)."""
        identity_type = "psid" if channel == "messenger" else channel
        try:
            return self._party_repo.find_by_identity(identity_type, sender_ref)
        except Exception as exc:
            log.warning("resolve_party_from_external_id %s/%s: %s", channel, sender_ref, exc)
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_or_raise(self, conversation_id: str) -> Conversation:
        conv = self._conv_repo.get_conversation_by_id(conversation_id)
        if conv is None:
            raise ValueError(f"conversation {conversation_id!r} not found")
        return conv

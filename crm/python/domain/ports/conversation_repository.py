from __future__ import annotations

from typing import Protocol

from domain.entities.conversation import Conversation, Message


class ConversationRepository(Protocol):
    """Outbound port for Conversation and Message persistence."""

    def upsert_conversation(self, conversation: Conversation) -> str:
        """Insert a new conversation or return the existing one matched by
        (channel, external_thread_id). Returns the conversation_id."""
        ...

    def get_conversation_by_id(self, conversation_id: str) -> Conversation | None:
        """Return a conversation by primary key, or None if not found."""
        ...

    def update_conversation(self, conversation: Conversation) -> None:
        """Persist mutable fields: party_id, status, assignee_user_id,
        last_message_at, unread_count, updated_at."""
        ...

    def insert_message(self, message: Message) -> tuple[str, bool]:
        """Insert a message row; idempotent via UNIQUE(conversation_id, external_message_id).
        Returns (message_id, inserted) — inserted=False means duplicate was skipped."""
        ...

    def list_conversations(
        self, assignee_user_id: str, status: str
    ) -> list[Conversation]:
        """Return conversations filtered by assignee and/or status.
        Empty string means 'any' for that filter. Ordered by last_message_at DESC."""
        ...

    def list_messages(self, conversation_id: str) -> list[Message]:
        """Return messages for a conversation ordered by sent_at ASC."""
        ...

    def update_conversation_on_message(
        self,
        conversation_id: str,
        sent_at: str,
        unread_delta: int,
    ) -> None:
        """Atomically advance last_message_at (take-max) and increment unread_count
        by delta. Call only when a new message was inserted.
        delta=1 for inbound, delta=0 for echo/outbound."""
        ...

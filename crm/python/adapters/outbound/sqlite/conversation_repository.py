"""SQLiteConversationRepository — Conversation + Message persistence (SQLite).

Ports exact SQL from conversation_queries.sql. Mirrors Go ConversationRepo logic:
- upsert uses INSERT … ON CONFLICT DO NOTHING RETURNING; on no-row conflict, falls
  back to a GET by (channel, external_thread_id).
- insert_message is idempotent via UNIQUE(conversation_id, external_message_id).
"""
from __future__ import annotations

import json
import sqlite3
from typing import Optional

from crm.python.adapters.outbound.sqlite.connection import CRMDatabase
from crm.python.domain.entities.conversation import Conversation, Message


# ── SQL statements (ported verbatim from conversation_queries.sql) ─────────────

_SQL_UPSERT_CONV = """
INSERT INTO crm_conversation (
  conversation_id, party_id, channel, external_thread_id, page_id,
  status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (channel, external_thread_id) DO NOTHING
RETURNING conversation_id
"""

_SQL_GET_CONV_BY_CHANNEL_THREAD = """
SELECT conversation_id, party_id, channel, external_thread_id, page_id,
       status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
WHERE channel = ? AND external_thread_id = ?
"""

_SQL_GET_CONV_BY_ID = """
SELECT conversation_id, party_id, channel, external_thread_id, page_id,
       status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
WHERE conversation_id = ?
"""

_SQL_UPDATE_CONV = """
UPDATE crm_conversation
SET party_id = ?, status = ?, assignee_user_id = ?,
    last_message_at = ?, unread_count = ?, updated_at = ?
WHERE conversation_id = ?
"""

_SQL_UPDATE_CONV_ON_MSG = """
UPDATE crm_conversation
SET last_message_at = CASE WHEN last_message_at IS NULL OR last_message_at < ? THEN ? ELSE last_message_at END,
    unread_count    = unread_count + ?
WHERE conversation_id = ?
"""

_SQL_LIST_BY_ASSIGNEE_STATUS = """
SELECT conversation_id, party_id, channel, external_thread_id, page_id,
       status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
WHERE assignee_user_id = ? AND status = ?
ORDER BY last_message_at DESC
"""

_SQL_LIST_BY_ASSIGNEE = """
SELECT conversation_id, party_id, channel, external_thread_id, page_id,
       status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
WHERE assignee_user_id = ?
ORDER BY last_message_at DESC
"""

_SQL_LIST_BY_STATUS = """
SELECT conversation_id, party_id, channel, external_thread_id, page_id,
       status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
WHERE status = ?
ORDER BY last_message_at DESC
"""

_SQL_LIST_ALL_CONVS = """
SELECT conversation_id, party_id, channel, external_thread_id, page_id,
       status, assignee_user_id, last_message_at, unread_count, created_at, updated_at
FROM crm_conversation
ORDER BY last_message_at DESC
"""

_SQL_INSERT_MSG = """
INSERT INTO crm_message (
  message_id, conversation_id, external_message_id, direction,
  sender_ref, body, attachments, sent_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (conversation_id, external_message_id) DO NOTHING
RETURNING message_id
"""

_SQL_LIST_MSGS = """
SELECT message_id, conversation_id, external_message_id, direction,
       sender_ref, body, attachments, sent_at
FROM crm_message
WHERE conversation_id = ?
ORDER BY sent_at ASC
"""


# ── Repository ─────────────────────────────────────────────────────────────────

class SQLiteConversationRepository:
    """SQLite adapter implementing the ConversationRepository port."""

    def __init__(self, db: CRMDatabase) -> None:
        self._conn: sqlite3.Connection = db.conn

    # ── Conversation CRUD ──────────────────────────────────────────────────────

    def upsert_conversation(self, conv: Conversation) -> str:
        """Insert new conversation or return existing id on (channel, external_thread_id) conflict."""
        attachments_json = _encode_attachments(getattr(conv, "attachments", None))
        params = (
            conv.conversation_id, conv.party_id, conv.channel, conv.external_thread_id,
            conv.page_id, conv.status, conv.assignee_user_id, conv.last_message_at,
            conv.unread_count, conv.created_at, conv.updated_at,
        )
        row = self._conn.execute(_SQL_UPSERT_CONV, params).fetchone()
        if row is not None:
            self._conn.commit()
            return row[0]
        # ON CONFLICT DO NOTHING → no RETURNING row; fall back to fetch existing.
        existing = self._conn.execute(
            _SQL_GET_CONV_BY_CHANNEL_THREAD, (conv.channel, conv.external_thread_id)
        ).fetchone()
        if existing is None:
            raise RuntimeError(
                f"upsert_conversation: conflict but no existing row found for "
                f"channel={conv.channel!r} thread={conv.external_thread_id!r}"
            )
        return existing["conversation_id"]

    def get_conversation_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Return Conversation by PK, or None if not found."""
        row = self._conn.execute(_SQL_GET_CONV_BY_ID, (conversation_id,)).fetchone()
        return _row_to_conv(row) if row else None

    def update_conversation(self, conversation: Conversation) -> None:
        """Persist mutable conversation fields."""
        c = conversation
        self._conn.execute(
            _SQL_UPDATE_CONV,
            (c.party_id, c.status, c.assignee_user_id, c.last_message_at,
             c.unread_count, c.updated_at, c.conversation_id),
        )
        self._conn.commit()

    def update_conversation_on_message(
        self, conversation_id: str, sent_at: str, unread_delta: int
    ) -> None:
        """Atomically advance last_message_at (take-max) and increment unread_count."""
        self._conn.execute(
            _SQL_UPDATE_CONV_ON_MSG,
            (sent_at, sent_at, unread_delta, conversation_id),
        )
        self._conn.commit()

    def list_conversations(
        self,
        assignee_user_id: str = "",
        status: str = "",
        limit: int = 50,
    ) -> list[Conversation]:
        """Return conversations filtered by assignee and/or status, newest first."""
        if assignee_user_id and status:
            rows = self._conn.execute(
                _SQL_LIST_BY_ASSIGNEE_STATUS, (assignee_user_id, status)
            ).fetchmany(limit)
        elif assignee_user_id:
            rows = self._conn.execute(
                _SQL_LIST_BY_ASSIGNEE, (assignee_user_id,)
            ).fetchmany(limit)
        elif status:
            rows = self._conn.execute(
                _SQL_LIST_BY_STATUS, (status,)
            ).fetchmany(limit)
        else:
            rows = self._conn.execute(_SQL_LIST_ALL_CONVS).fetchmany(limit)
        return [_row_to_conv(r) for r in rows]

    # ── Message CRUD ───────────────────────────────────────────────────────────

    def insert_message(self, msg: Message) -> tuple[str, bool]:
        """Insert message; idempotent via UNIQUE(conversation_id, external_message_id).

        Returns (message_id, inserted): inserted=False means duplicate was skipped.
        """
        attachments_raw = (
            json.dumps(msg.attachments) if isinstance(msg.attachments, list)
            else (msg.attachments or "")
        )
        params = (
            msg.message_id, msg.conversation_id, msg.external_message_id,
            msg.direction, msg.sender_ref, msg.body, attachments_raw, msg.sent_at,
        )
        row = self._conn.execute(_SQL_INSERT_MSG, params).fetchone()
        if row is not None:
            self._conn.commit()
            return row[0], True
        # Duplicate — ON CONFLICT DO NOTHING, idempotent skip.
        return "", False

    def list_messages(
        self, conversation_id: str, limit: int = 100
    ) -> list[Message]:
        """Return messages for a conversation ordered by sent_at ASC."""
        rows = self._conn.execute(_SQL_LIST_MSGS, (conversation_id,)).fetchmany(limit)
        return [_row_to_msg(r) for r in rows]


# ── Row mappers ────────────────────────────────────────────────────────────────

def _row_to_conv(row: sqlite3.Row) -> Conversation:
    return Conversation(
        conversation_id=row["conversation_id"],
        party_id=row["party_id"],
        channel=row["channel"],
        external_thread_id=row["external_thread_id"],
        page_id=row["page_id"],
        status=row["status"],
        assignee_user_id=row["assignee_user_id"],
        last_message_at=row["last_message_at"],
        unread_count=row["unread_count"] or 0,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_msg(row: sqlite3.Row) -> Message:
    raw = row["attachments"] or ""
    try:
        attachments = json.loads(raw) if raw else []
    except (json.JSONDecodeError, ValueError):
        attachments = []
    return Message(
        message_id=row["message_id"],
        conversation_id=row["conversation_id"],
        external_message_id=row["external_message_id"],
        direction=row["direction"],
        sender_ref=row["sender_ref"],
        body=row["body"],
        attachments=attachments,
        sent_at=row["sent_at"],
        created_at=row["sent_at"],  # crm_message has no created_at column; use sent_at
    )


def _encode_attachments(attachments: object) -> str:
    """Normalise attachments to a JSON string for storage."""
    if attachments is None:
        return ""
    if isinstance(attachments, list):
        return json.dumps(attachments)
    return str(attachments)

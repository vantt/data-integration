"""NoteService — business logic for party notes.

Depends only on domain entities and port protocols; no adapter imports.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from shared.timestamps import utc_now

if TYPE_CHECKING:
    from adapters.outbound.sqlite.connection import CRMDatabase

from domain.entities.profile import Note
from domain.ports.tag_repository import NoteRepository


class NoteService:
    """Manages note lifecycle for parties."""

    def __init__(
        self,
        note_repo: NoteRepository,
        db: Optional[CRMDatabase] = None,
    ) -> None:
        self._notes = note_repo
        self._db = db

    def add_note(
        self,
        party_id: str,
        body: str,
        author_user_id: Optional[str] = None,
        note_type: str = "general",
        pinned: bool = False,
        visibility: str = "team",
        source_activity_id: Optional[str] = None,
    ) -> Note:
        if not body.strip():
            raise ValueError("note service: note body must not be empty")
        note = Note(
            note_id=str(uuid.uuid4()),
            party_id=party_id,
            body=body,
            author_user_id=author_user_id,
            created_at=utc_now(),
            note_type=note_type,
            pinned=pinned,
            visibility=visibility,
            source_activity_id=source_activity_id,
        )
        self._notes.add_note(note)
        if self._db:
            self._db.commit()
        return note

    def list_notes(self, party_id: str) -> list[Note]:
        return self._notes.list_notes(party_id)

    def update_note(
        self,
        note_id: str,
        body: str,
        note_type: str = "general",
        pinned: bool = False,
        visibility: str = "team",
    ) -> None:
        if not body.strip():
            raise ValueError("note service: note body must not be empty")
        self._notes.update_note(note_id, body, note_type, pinned, visibility)
        if self._db:
            self._db.commit()

    def delete_note(self, note_id: str) -> None:
        self._notes.soft_delete_note(note_id)
        if self._db:
            self._db.commit()

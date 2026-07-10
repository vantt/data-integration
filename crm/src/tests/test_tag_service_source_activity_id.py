"""test_tag_service_source_activity_id.py — plan 260709-1638 phase-01.

crm_party_tag.source_activity_id (migration 0044): links a tag attach back to
the crm_activity_log row it was captured during. Covers:
- TagService.attach_tag(..., source_activity_id=...) passes it through to
  PartyTag and persists it.
- Backward compat: calling attach_tag() without the new kwarg still works and
  leaves source_activity_id NULL.
"""
from __future__ import annotations

import pathlib
import sys
import uuid

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from application.tag_service import TagService  # noqa: E402
from adapters.outbound.sqlite.tag_note_repository import SQLiteTagRepository  # noqa: E402


def _insert_party(db, party_id: str) -> None:
    db.conn.execute(
        "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
        (party_id, "Test Party"),
    )
    db.conn.commit()


def _insert_activity(db, activity_id: str, party_id: str) -> None:
    """source_activity_id has a REFERENCES crm_activity_log(activity_id) FK
    (migration 0044) — tests must insert a real row, not an arbitrary string."""
    db.conn.execute(
        """
        INSERT INTO crm_activity_log (activity_id, party_id, activity_type, occurred_at, created_at)
        VALUES (?, ?, 'call', '2026-07-01T00:00:00Z', '2026-07-01T00:00:00Z')
        """,
        (activity_id, party_id),
    )
    db.conn.commit()


class TestAttachTagSourceActivityId:
    def test_attach_tag_persists_source_activity_id(self, seeded_crm_db):
        repo = SQLiteTagRepository(seeded_crm_db)
        svc = TagService(repo, db=seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        _insert_activity(seeded_crm_db, "act-123", party_id)

        svc.attach_tag(party_id, "tag-health-0001", user_id=None, source="crm_user",
                        source_activity_id="act-123")

        row = seeded_crm_db.conn.execute(
            "SELECT source_activity_id FROM crm_party_tag WHERE party_id=? AND tag_id=?",
            (party_id, "tag-health-0001"),
        ).fetchone()
        assert row["source_activity_id"] == "act-123"

    def test_attach_tag_without_param_stays_backward_compatible(self, seeded_crm_db):
        """Existing call sites that don't pass source_activity_id keep working
        and the column stays NULL — matches every M03/inline call site that
        predates this migration."""
        repo = SQLiteTagRepository(seeded_crm_db)
        svc = TagService(repo, db=seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)

        svc.attach_tag(party_id, "tag-health-0002", user_id=None, source="crm_user")

        row = seeded_crm_db.conn.execute(
            "SELECT source_activity_id FROM crm_party_tag WHERE party_id=? AND tag_id=?",
            (party_id, "tag-health-0002"),
        ).fetchone()
        assert row["source_activity_id"] is None

    def test_reattach_without_activity_id_does_not_erase_existing_link(self, seeded_crm_db):
        """A later re-attach (e.g. sync reconcile passes no activity context)
        must not wipe a previously-recorded call link — COALESCE guard in
        SQLiteTagRepository._SQL_ATTACH."""
        repo = SQLiteTagRepository(seeded_crm_db)
        svc = TagService(repo, db=seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        _insert_activity(seeded_crm_db, "act-999", party_id)

        svc.attach_tag(party_id, "tag-health-0003", source="crm_user", source_activity_id="act-999")
        svc.attach_tag(party_id, "tag-health-0003", source="crm_user")  # no activity_id this time

        row = seeded_crm_db.conn.execute(
            "SELECT source_activity_id FROM crm_party_tag WHERE party_id=? AND tag_id=?",
            (party_id, "tag-health-0003"),
        ).fetchone()
        assert row["source_activity_id"] == "act-999"

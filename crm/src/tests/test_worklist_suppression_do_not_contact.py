"""test_worklist_suppression_do_not_contact.py — plan 260709-1638 phase-01.

Suppression: a party whose MOST RECENT activity has outcome_reason=
'do_not_contact' must disappear from the worklist action queue on next load —
without deleting any underlying data (crm_activity_log / crm_party untouched).
Runtime filter only, wired in WorklistQueryService.list_all_action_queue().

Compares the literal string 'do_not_contact' only — does NOT import
VALID_OUTCOME_REASONS from domain.entities.activity (out of scope for this
change; see plan phase-01 "Handoff wiring").
"""
from __future__ import annotations

import pathlib
import sys
import uuid
from unittest.mock import MagicMock

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from application.worklist_query_service import WorklistQueryService  # noqa: E402
from adapters.outbound.sqlite.activity_repository import SQLiteActivityRepository  # noqa: E402
from domain.entities.activity import Activity  # noqa: E402


def _make_action_item(party_id: str):
    item = MagicMock()
    item.party_id = party_id
    return item


class TestWorklistQueryServiceSuppression:
    """Unit-level: fake action_queue + fake suppression ports."""

    def test_suppressed_party_removed_from_action_queue(self):
        action_queue = MagicMock()
        action_queue.list_all_action_queue.return_value = [
            _make_action_item("party-A"),
            _make_action_item("party-B"),
        ]
        suppression = MagicMock()
        suppression.list_do_not_contact_party_ids.return_value = {"party-B"}

        svc = WorklistQueryService(action_queue=action_queue, suppression=suppression)
        result = svc.list_all_action_queue()

        assert [a.party_id for a in result] == ["party-A"]

    def test_no_suppression_port_returns_all(self):
        action_queue = MagicMock()
        action_queue.list_all_action_queue.return_value = [_make_action_item("party-A")]
        svc = WorklistQueryService(action_queue=action_queue)  # suppression=None default
        result = svc.list_all_action_queue()
        assert [a.party_id for a in result] == ["party-A"]

    def test_suppression_query_failure_degrades_to_unfiltered(self):
        """A suppression lookup error must not blank the whole worklist."""
        action_queue = MagicMock()
        action_queue.list_all_action_queue.return_value = [_make_action_item("party-A")]
        suppression = MagicMock()
        suppression.list_do_not_contact_party_ids.side_effect = RuntimeError("db down")

        svc = WorklistQueryService(action_queue=action_queue, suppression=suppression)
        result = svc.list_all_action_queue()
        assert [a.party_id for a in result] == ["party-A"]


class TestSuppressionEndToEnd:
    """Real DB: log a do_not_contact activity, then confirm the party
    disappears from the worklist on the next load."""

    def _insert_party(self, db, party_id: str) -> None:
        db.conn.execute(
            "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
            (party_id, "Test Party"),
        )
        db.conn.commit()

    def _insert_activity(self, db, party_id: str, occurred_at: str, outcome_reason) -> None:
        """Insert directly at repository level — bypasses ActivityService's
        VALID_OUTCOME_REASONS validation (owned by domain/entities/activity.py,
        a forbidden file for this change; 'do_not_contact' is added there by a
        different in-flight change). Repository writes accept any string."""
        activity_repo = SQLiteActivityRepository(db)
        activity_repo.insert(Activity(
            activity_id=str(uuid.uuid4()),
            party_id=party_id,
            activity_type="call",
            occurred_at=occurred_at,
            created_at=occurred_at,
            outcome_reason=outcome_reason,
        ))
        db.commit()

    def test_party_disappears_from_worklist_after_do_not_contact_activity(self, seeded_crm_db):
        party_suppressed = str(uuid.uuid4())
        party_visible = str(uuid.uuid4())
        self._insert_party(seeded_crm_db, party_suppressed)
        self._insert_party(seeded_crm_db, party_visible)

        # Two prior activities for party_suppressed — the LATEST one (by
        # occurred_at) carries do_not_contact; an earlier one does not, proving
        # the query keys off "most recent", not "any".
        self._insert_activity(seeded_crm_db, party_suppressed, "2026-07-01T00:00:00Z", "budget")
        self._insert_activity(seeded_crm_db, party_suppressed, "2026-07-05T00:00:00Z", "do_not_contact")
        self._insert_activity(seeded_crm_db, party_visible, "2026-07-05T00:00:00Z", "budget")

        activity_repo = SQLiteActivityRepository(seeded_crm_db)
        action_queue = MagicMock()
        action_queue.list_all_action_queue.return_value = [
            _make_action_item(party_suppressed),
            _make_action_item(party_visible),
        ]
        svc = WorklistQueryService(action_queue=action_queue, suppression=activity_repo)

        result = svc.list_all_action_queue()
        assert [a.party_id for a in result] == [party_visible]

        # Data is untouched — activities still exist for the suppressed party.
        remaining = seeded_crm_db.conn.execute(
            "SELECT COUNT(*) FROM crm_activity_log WHERE party_id = ?", (party_suppressed,)
        ).fetchone()[0]
        assert remaining == 2

    def test_earlier_do_not_contact_overridden_by_later_normal_activity(self, seeded_crm_db):
        """A party asked not to be contacted, then later re-engaged (e.g. staff
        follow-up outside the CRM) — the MOST RECENT activity wins, so the
        party becomes visible again once a newer non-suppressing activity lands."""
        party_id = str(uuid.uuid4())
        self._insert_party(seeded_crm_db, party_id)
        self._insert_activity(seeded_crm_db, party_id, "2026-07-01T00:00:00Z", "do_not_contact")
        self._insert_activity(seeded_crm_db, party_id, "2026-07-08T00:00:00Z", "budget")

        activity_repo = SQLiteActivityRepository(seeded_crm_db)
        action_queue = MagicMock()
        action_queue.list_all_action_queue.return_value = [_make_action_item(party_id)]
        svc = WorklistQueryService(action_queue=action_queue, suppression=activity_repo)

        result = svc.list_all_action_queue()
        assert [a.party_id for a in result] == [party_id]

"""test_task_claim_action_types_snapshot.py — plan 260709-1638 phase-01.

crm_task.claimed_action_types (migration 0043): snapshot the action_type list
of every action item covered by a customer claim, taken ONCE at claim time and
never re-synced afterwards. Covers:
- TaskService.claim_customer_actions() serializes the action_type list in the
  order given (already priority_rank-ascending upstream — cache_repository's
  list_all_action_queue() ORDER BY priority ASC, preserved by screen_worklist.py's
  party_id filter).
- A second claim() call on an existing customer claim never re-snapshots.
- Round-trip through SQLiteTaskRepository + migration 0043.
"""
from __future__ import annotations

import json
import pathlib
import sys
from unittest.mock import MagicMock

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from application.task_service import TaskService  # noqa: E402
from adapters.outbound.sqlite.task_repository import SQLiteTaskRepository  # noqa: E402


def _make_action(action_id, action_type, priority, **overrides):
    action = MagicMock()
    action.action_id = action_id
    action.action_type = action_type
    action.priority = priority
    action.rationale_vi = overrides.get("rationale_vi", "")
    action.customer_name = overrides.get("customer_name", "Test Customer")
    action.party_id = overrides.get("party_id", "party-1")
    action.value_at_stake_vnd = overrides.get("value_at_stake_vnd", 0)
    action.top_affinity_product = overrides.get("top_affinity_product", "")
    return action


class TestClaimCustomerActionsSnapshot:
    def test_two_actions_snapshot_in_priority_order(self):
        task_repo = MagicMock()
        task_repo.get_customer_claim.return_value = None
        task_repo.insert = MagicMock()
        cache_repo = MagicMock()
        svc = TaskService(task_repo, cache_repo, db=None)

        # Caller-supplied order is already priority_rank ascending (most urgent
        # first) — mirrors screen_worklist.py's filter over the warehouse query.
        actions = [
            _make_action("aq-1", "REORDER_OVERDUE", priority=1),
            _make_action("aq-2", "PROGRESS_CHECK", priority=5),
        ]
        task, is_new = svc.claim_customer_actions("party-1", actions, "user-1")

        assert is_new is True
        assert task.claimed_action_types == json.dumps(["REORDER_OVERDUE", "PROGRESS_CHECK"])
        assert json.loads(task.claimed_action_types) == ["REORDER_OVERDUE", "PROGRESS_CHECK"]

    def test_no_actions_snapshot_is_none(self):
        task_repo = MagicMock()
        task_repo.get_customer_claim.return_value = None
        cache_repo = MagicMock()
        svc = TaskService(task_repo, cache_repo, db=None)

        task, _ = svc.claim_customer_actions("party-1", [], "user-1")
        assert task.claimed_action_types is None

    def test_already_claimed_does_not_resnapshot(self):
        """Snapshot is written ONCE at claim — a second claim() call on an
        existing customer claim returns it unchanged (is_new=False, no insert)."""
        existing = MagicMock()
        existing.claimed_action_types = json.dumps(["OLD_TYPE"])
        task_repo = MagicMock()
        task_repo.get_customer_claim.return_value = existing
        cache_repo = MagicMock()
        svc = TaskService(task_repo, cache_repo, db=None)

        actions = [_make_action("aq-1", "NEW_TYPE", priority=1)]
        task, is_new = svc.claim_customer_actions("party-1", actions, "user-1")

        assert is_new is False
        assert task is existing
        assert task.claimed_action_types == json.dumps(["OLD_TYPE"])
        task_repo.insert.assert_not_called()


class TestClaimedActionTypesRoundTrip:
    """Migration 0043 + SQLiteTaskRepository — real DB round trip."""

    def _insert_party(self, db, party_id: str) -> None:
        db.conn.execute(
            "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
            (party_id, "Test Party"),
        )
        db.conn.commit()

    def _insert_app_user(self, db, user_id: str) -> None:
        db.conn.execute(
            "INSERT INTO crm_app_user (user_id, email, full_name) VALUES (?, ?, ?)",
            (user_id, f"{user_id}@test.vn", "Test User"),
        )
        db.conn.commit()

    def test_claim_persists_and_reads_back_json(self, seeded_crm_db):
        party_id = "party-rt-1"
        self._insert_party(seeded_crm_db, party_id)
        self._insert_app_user(seeded_crm_db, "user-1")
        task_repo = SQLiteTaskRepository(seeded_crm_db)
        svc = TaskService(task_repo, MagicMock(), db=seeded_crm_db)

        actions = [
            _make_action("aq-1", "REORDER_OVERDUE", priority=1, party_id=party_id),
            _make_action("aq-2", "PROGRESS_CHECK", priority=5, party_id=party_id),
        ]
        task, is_new = svc.claim_customer_actions(party_id, actions, "user-1")
        assert is_new is True

        reloaded = task_repo.get_by_id(task.task_id)
        assert reloaded is not None
        assert json.loads(reloaded.claimed_action_types) == ["REORDER_OVERDUE", "PROGRESS_CHECK"]

    def test_pre_migration_task_reads_as_none(self, seeded_crm_db):
        """A task row with claimed_action_types unset (column exists, value NULL)
        — the fix-forward contract: nothing before migration 0043 gets a value."""
        party_id = "party-rt-2"
        self._insert_party(seeded_crm_db, party_id)
        seeded_crm_db.conn.execute(
            """
            INSERT INTO crm_task (task_id, party_id, title, priority, status, source,
                                    created_at, updated_at)
            VALUES ('task-legacy', ?, 'Legacy task', 0, 'open', 'manual',
                    '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')
            """,
            (party_id,),
        )
        seeded_crm_db.conn.commit()

        task_repo = SQLiteTaskRepository(seeded_crm_db)
        reloaded = task_repo.get_by_id("task-legacy")
        assert reloaded.claimed_action_types is None

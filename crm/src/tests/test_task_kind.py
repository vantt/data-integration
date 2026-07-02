"""test_task_kind.py — unit tests for derive_task_kind truth table + task_service integration.

Coverage:
  1. derive_task_kind: all branches (truth table)
  2. task_service.create_task: derives kind when not supplied; honours explicit kind
  3. task_service.claim_customer_actions: always 'contact'
  4. M05 POST handler: derives when absent, honours explicit valid value
"""
from __future__ import annotations

import pathlib
import sys
import uuid
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from application.task_kind import derive_task_kind                         # noqa: E402
from domain.entities.task import (                                          # noqa: E402
    TASK_KIND_CONTACT, TASK_KIND_GENERIC, TASK_KIND_INTERNAL,
)
from domain.entities.cache_insight import (                                 # noqa: E402
    ACTION_COLLECT_FEEDBACK, ACTION_CALL_NOW, ACTION_REORDER_NUDGE,
    ACTION_WIN_BACK, ACTION_UPSELL, ACTION_CROSS_SELL,
)

_TS = "2026-07-02T00:00:00.000Z"


# ---------------------------------------------------------------------------
# 1. derive_task_kind truth table
# ---------------------------------------------------------------------------

class TestDeriveTaskKindTruthTable:
    """Cover every branch of derive_task_kind."""

    # Rule 1: no party → generic
    def test_no_party_id_is_generic(self):
        kind, confident = derive_task_kind("manual", None, None)
        assert kind == TASK_KIND_GENERIC
        assert confident is True

    def test_no_party_id_with_source_ref_is_generic(self):
        kind, confident = derive_task_kind("action_queue", "action-001", None)
        assert kind == TASK_KIND_GENERIC
        assert confident is True

    # Rule 2a: source == 'verify_account' → internal
    def test_verify_account_source_is_internal(self):
        kind, confident = derive_task_kind("verify_account", None, "party-001")
        assert kind == TASK_KIND_INTERNAL
        assert confident is True

    def test_verify_account_source_with_ref_is_internal(self):
        kind, confident = derive_task_kind("verify_account", "verify_account/abc", "party-002")
        assert kind == TASK_KIND_INTERNAL
        assert confident is True

    # Rule 2b: source_ref starts with 'verify_account'
    def test_verify_account_source_ref_prefix_is_internal(self):
        kind, confident = derive_task_kind("manual", "verify_account/abc123", "party-003")
        assert kind == TASK_KIND_INTERNAL
        assert confident is True

    def test_verify_account_source_ref_exact_prefix_is_internal(self):
        kind, confident = derive_task_kind("manual", "verify_account", "party-003")
        assert kind == TASK_KIND_INTERNAL
        assert confident is True

    # Rule 3: action_queue sources
    def test_action_queue_outreach_types_are_contact(self):
        outreach_types = [
            ACTION_CALL_NOW, ACTION_REORDER_NUDGE, ACTION_WIN_BACK,
            ACTION_UPSELL, ACTION_CROSS_SELL,
        ]
        for at in outreach_types:
            kind, confident = derive_task_kind("action_queue", "action-x", "party-001", action_type=at)
            assert kind == TASK_KIND_CONTACT, f"{at} should map to contact"
            assert confident is True

    def test_action_queue_collect_feedback_is_internal(self):
        kind, confident = derive_task_kind(
            "action_queue", "action-x", "party-001", action_type=ACTION_COLLECT_FEEDBACK
        )
        assert kind == TASK_KIND_INTERNAL
        assert confident is True

    def test_action_queue_claim_outreach_is_contact(self):
        kind, confident = derive_task_kind(
            "action_queue_claim", "party-001", "party-001", action_type=ACTION_CALL_NOW
        )
        assert kind == TASK_KIND_CONTACT
        assert confident is True

    def test_action_queue_claim_collect_feedback_is_internal(self):
        kind, confident = derive_task_kind(
            "action_queue_claim", "party-001", "party-001", action_type=ACTION_COLLECT_FEEDBACK
        )
        assert kind == TASK_KIND_INTERNAL
        assert confident is True

    def test_action_queue_no_action_type_defaults_contact(self):
        """action_queue with no action_type → contact (safe default)."""
        kind, confident = derive_task_kind("action_queue", "action-x", "party-001")
        assert kind == TASK_KIND_CONTACT
        assert confident is True

    # Rule 4: manual with party → contact, NOT confident
    def test_manual_with_party_is_contact_not_confident(self):
        kind, confident = derive_task_kind("manual", None, "party-001")
        assert kind == TASK_KIND_CONTACT
        assert confident is False

    def test_manual_with_party_and_ref_is_contact_not_confident(self):
        kind, confident = derive_task_kind("manual", "some-ref", "party-001")
        assert kind == TASK_KIND_CONTACT
        assert confident is False

    # Fallback: unknown source with party → contact, not confident
    def test_unknown_source_with_party_is_contact_not_confident(self):
        kind, confident = derive_task_kind("campaign", None, "party-001")
        assert kind == TASK_KIND_CONTACT
        assert confident is False

    def test_unknown_source_no_party_is_generic(self):
        kind, confident = derive_task_kind("campaign", None, None)
        assert kind == TASK_KIND_GENERIC
        assert confident is True

    # Edge: empty string party_id treated as falsy → generic
    def test_empty_string_party_id_is_generic(self):
        kind, confident = derive_task_kind("manual", None, "")
        assert kind == TASK_KIND_GENERIC
        assert confident is True


# ---------------------------------------------------------------------------
# 2. TaskService.create_task derives kind when not supplied
# ---------------------------------------------------------------------------

class TestTaskServiceCreateTaskKind:
    """Smoke-tests via mocked repo — no DB required."""

    def _make_service(self):
        from application.task_service import TaskService
        task_repo = MagicMock()
        task_repo.insert = MagicMock()
        cache_repo = MagicMock()
        svc = TaskService(task_repo, cache_repo, db=None)
        return svc, task_repo

    def test_action_queue_source_derives_contact(self):
        svc, repo = self._make_service()
        task = svc.create_task({
            "title": "Test action",
            "party_id": "party-001",
            "source": "action_queue",
            "source_ref": "action-001",
            "action_type": ACTION_CALL_NOW,
        })
        assert task.task_kind == TASK_KIND_CONTACT
        repo.insert.assert_called_once()

    def test_null_party_derives_generic(self):
        svc, repo = self._make_service()
        task = svc.create_task({
            "title": "Internal meeting",
            "party_id": None,
            "source": "manual",
        })
        assert task.task_kind == TASK_KIND_GENERIC

    def test_verify_account_source_derives_internal(self):
        svc, repo = self._make_service()
        task = svc.create_task({
            "title": "Verify account",
            "party_id": "party-001",
            "source": "verify_account",
        })
        assert task.task_kind == TASK_KIND_INTERNAL

    def test_manual_with_party_derives_contact(self):
        svc, repo = self._make_service()
        task = svc.create_task({
            "title": "Follow up call",
            "party_id": "party-001",
            "source": "manual",
        })
        assert task.task_kind == TASK_KIND_CONTACT

    def test_explicit_task_kind_is_honoured(self):
        """Explicit task_kind in task_data overrides derivation."""
        svc, repo = self._make_service()
        task = svc.create_task({
            "title": "Special internal",
            "party_id": "party-001",
            "source": "manual",
            "task_kind": "internal",
        })
        assert task.task_kind == TASK_KIND_INTERNAL

    def test_collect_feedback_action_derives_internal(self):
        svc, repo = self._make_service()
        task = svc.create_task({
            "title": "Feedback task",
            "party_id": "party-001",
            "source": "action_queue",
            "source_ref": "action-feedback-1",
            "action_type": ACTION_COLLECT_FEEDBACK,
        })
        assert task.task_kind == TASK_KIND_INTERNAL


# ---------------------------------------------------------------------------
# 3. TaskService.claim_customer_actions always sets contact
# ---------------------------------------------------------------------------

class TestTaskServiceClaimKind:
    def _make_service(self):
        from application.task_service import TaskService
        task_repo = MagicMock()
        task_repo.get_customer_claim = MagicMock(return_value=None)
        task_repo.insert = MagicMock()
        cache_repo = MagicMock()
        svc = TaskService(task_repo, cache_repo, db=None)
        return svc, task_repo

    def _make_action(self, action_type=ACTION_CALL_NOW):
        action = MagicMock()
        action.action_type = action_type
        action.rationale_vi = "Gọi ngay"
        action.priority = 1
        return action

    def test_claim_customer_actions_is_contact(self):
        svc, repo = self._make_service()
        actions = [self._make_action(ACTION_WIN_BACK)]
        task, is_new = svc.claim_customer_actions("party-001", actions, "user-001")
        assert task.task_kind == TASK_KIND_CONTACT
        assert is_new is True

    def test_claim_customer_actions_already_exists_returns_existing(self):
        svc, repo = self._make_service()
        existing = MagicMock()
        repo.get_customer_claim.return_value = existing
        task, is_new = svc.claim_customer_actions("party-001", [], "user-001")
        assert task is existing
        assert is_new is False


# ---------------------------------------------------------------------------
# 4. M05 POST decision logic — tested without importing FastAPI
#
#    The handler does exactly this resolution before calling create_task:
#
#      resolved_kind = task_kind.strip()
#      if not resolved_kind or resolved_kind not in VALID_TASK_KINDS:
#          resolved_kind, _ = derive_task_kind(source, source_ref, party_id)
#
#    We test that logic directly here so the suite does not require fastapi.
# ---------------------------------------------------------------------------

def _m05_resolve_kind(task_kind_form: str, source: str, source_ref: str, party_id: str) -> str:
    """Mirror the M05 POST resolution logic, usable without FastAPI."""
    from domain.entities.task import VALID_TASK_KINDS
    resolved = task_kind_form.strip()
    if not resolved or resolved not in VALID_TASK_KINDS:
        resolved, _ = derive_task_kind(
            source=source or "manual",
            source_ref=source_ref or None,
            party_id=party_id or None,
        )
    return resolved


class TestM05PostTaskKindLogic:
    """Test M05 POST task_kind resolution without importing FastAPI."""

    def test_empty_form_value_derives_contact_for_manual_with_party(self):
        kind = _m05_resolve_kind("", "manual", "", "party-001")
        assert kind == TASK_KIND_CONTACT

    def test_explicit_internal_is_honoured(self):
        kind = _m05_resolve_kind("internal", "manual", "", "party-001")
        assert kind == TASK_KIND_INTERNAL

    def test_explicit_generic_is_honoured(self):
        kind = _m05_resolve_kind("generic", "manual", "", "party-001")
        assert kind == TASK_KIND_GENERIC

    def test_invalid_value_falls_back_to_derived(self):
        """'bogus' not in VALID_TASK_KINDS → derive; manual+party → contact."""
        kind = _m05_resolve_kind("bogus", "manual", "", "party-001")
        assert kind == TASK_KIND_CONTACT

    def test_whitespace_only_value_derives(self):
        kind = _m05_resolve_kind("   ", "manual", "", "party-001")
        assert kind == TASK_KIND_CONTACT

    def test_no_party_derives_generic_regardless_of_source(self):
        kind = _m05_resolve_kind("", "manual", "", "")
        assert kind == TASK_KIND_GENERIC

    def test_verify_account_source_ref_derives_internal(self):
        kind = _m05_resolve_kind("", "manual", "verify_account/abc", "party-001")
        assert kind == TASK_KIND_INTERNAL

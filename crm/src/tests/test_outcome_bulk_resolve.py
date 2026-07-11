"""Pure-logic unit tests for Phase 04 outcome bulk-resolve helpers.

Tests cover:
- _parse_id_list: comma-separated parsing, empty/whitespace handling
- _bulk_resolve: action dismiss loop, task transition loop, skip_task_id guard,
  None-safe when action_state / task_svc are absent, per-item error isolation
- Phase-03 IDOR guard: mismatched action_id/task_id skipped, not mutated —
  isolation preserved for valid ids in the same batch, unresolvable ids fail
  closed.

No FastAPI / HTTP client — these tests import only the helper functions.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock, call

import pytest

# ── sys.path setup (mirrors conftest.py pattern) ──────────────────────────────
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # data-integration/
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1]) # crm/src/
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.adapters.inbound.web.screens.customer360.outcome_resolve_helpers import (
    parse_id_list as _parse_id_list,
    bulk_resolve as _bulk_resolve,
)
from crm.src.application.authorization_service import AuthorizationService


# ── shared test fixtures ──────────────────────────────────────────────────────
# Every `_bulk_resolve` call now requires `party_id`/`authz` (phase-03 IDOR
# fix). Tests not specifically exercising the IDOR guard use `_AUTHZ_OK` — a
# stand-in that always reports "same party" — so the pre-existing dismiss/
# snooze/transition_status assertions stay unaffected by the new guard. Tests
# that DO exercise the guard use a REAL AuthorizationService with the mocks'
# resolve_party_id()/get_task() configured to return a matching or mismatched
# party_id, exactly like the production path.

_PARTY = "party-test-1"


def _authz_ok() -> MagicMock:
    m = MagicMock(spec=AuthorizationService)
    m.is_same_party.return_value = True
    return m


# ── _parse_id_list ────────────────────────────────────────────────────────────

class TestParseIdList:
    def test_empty_string_returns_empty(self):
        assert _parse_id_list("") == []

    def test_whitespace_only_returns_empty(self):
        assert _parse_id_list("   ") == []

    def test_single_id(self):
        assert _parse_id_list("abc-123") == ["abc-123"]

    def test_multiple_ids_comma_separated(self):
        result = _parse_id_list("a1,b2,c3")
        assert result == ["a1", "b2", "c3"]

    def test_strips_whitespace_around_ids(self):
        result = _parse_id_list(" a1 , b2 , c3 ")
        assert result == ["a1", "b2", "c3"]

    def test_trailing_comma_ignored(self):
        result = _parse_id_list("a1,b2,")
        assert result == ["a1", "b2"]

    def test_consecutive_commas_produce_no_empty_entries(self):
        result = _parse_id_list("a1,,b2")
        assert result == ["a1", "b2"]

    def test_uuid_style_ids(self):
        ids = "550e8400-e29b-41d4-a716-446655440000,6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        result = _parse_id_list(ids)
        assert len(result) == 2
        assert result[0] == "550e8400-e29b-41d4-a716-446655440000"


# ── _bulk_resolve ─────────────────────────────────────────────────────────────

class TestBulkResolve:
    def _make_action_state(self):
        m = MagicMock()
        m.dismiss = MagicMock()
        return m

    def _make_task_svc(self):
        m = MagicMock()
        m.transition_status = MagicMock()
        return m

    # ── None-safe ────────────────────────────────────────────────────────────

    def test_none_action_state_does_not_raise(self):
        _bulk_resolve(["a1"], [], action_state=None, task_svc=None, party_id=_PARTY, authz=_authz_ok())

    def test_none_task_svc_does_not_raise(self):
        _bulk_resolve([], ["t1"], action_state=None, task_svc=None, party_id=_PARTY, authz=_authz_ok())

    def test_both_none_and_empty_lists_no_op(self):
        _bulk_resolve([], [], action_state=None, task_svc=None, party_id=_PARTY, authz=_authz_ok())

    # ── action_ids dispatched to dismiss ─────────────────────────────────────

    def test_single_action_dismissed(self):
        as_ = self._make_action_state()
        _bulk_resolve(["act-1"], [], action_state=as_, task_svc=None, party_id=_PARTY, authz=_authz_ok())
        as_.dismiss.assert_called_once_with("act-1", user_id=None)

    def test_multiple_actions_each_dismissed(self):
        as_ = self._make_action_state()
        _bulk_resolve(["a1", "a2", "a3"], [], action_state=as_, task_svc=None, party_id=_PARTY, authz=_authz_ok())
        assert as_.dismiss.call_count == 3
        as_.dismiss.assert_any_call("a1", user_id=None)
        as_.dismiss.assert_any_call("a2", user_id=None)
        as_.dismiss.assert_any_call("a3", user_id=None)

    def test_actor_id_passed_to_dismiss(self):
        as_ = self._make_action_state()
        _bulk_resolve(
            ["act-1"], [], action_state=as_, task_svc=None, actor_id="user-xyz",
            party_id=_PARTY, authz=_authz_ok(),
        )
        as_.dismiss.assert_called_once_with("act-1", user_id="user-xyz")

    def test_empty_actor_id_passes_none_to_dismiss(self):
        as_ = self._make_action_state()
        _bulk_resolve(
            ["act-1"], [], action_state=as_, task_svc=None, actor_id="",
            party_id=_PARTY, authz=_authz_ok(),
        )
        as_.dismiss.assert_called_once_with("act-1", user_id=None)

    # ── task_ids dispatched to transition_status ──────────────────────────────

    def test_single_task_transitioned_to_done(self):
        ts = self._make_task_svc()
        _bulk_resolve([], ["t-1"], action_state=None, task_svc=ts, party_id=_PARTY, authz=_authz_ok())
        ts.transition_status.assert_called_once_with("t-1", "done")

    def test_multiple_tasks_all_transitioned(self):
        ts = self._make_task_svc()
        _bulk_resolve([], ["t-1", "t-2"], action_state=None, task_svc=ts, party_id=_PARTY, authz=_authz_ok())
        assert ts.transition_status.call_count == 2
        ts.transition_status.assert_any_call("t-1", "done")
        ts.transition_status.assert_any_call("t-2", "done")

    # ── skip_task_id guard ────────────────────────────────────────────────────

    def test_skip_task_id_excluded_from_bulk(self):
        ts = self._make_task_svc()
        _bulk_resolve(
            [], ["t-1", "t-2"], action_state=None, task_svc=ts, skip_task_id="t-1",
            party_id=_PARTY, authz=_authz_ok(),
        )
        ts.transition_status.assert_called_once_with("t-2", "done")

    def test_skip_task_id_not_in_list_no_effect(self):
        ts = self._make_task_svc()
        _bulk_resolve(
            [], ["t-1", "t-2"], action_state=None, task_svc=ts, skip_task_id="t-99",
            party_id=_PARTY, authz=_authz_ok(),
        )
        assert ts.transition_status.call_count == 2

    def test_skip_task_id_empty_string_resolves_all(self):
        ts = self._make_task_svc()
        _bulk_resolve(
            [], ["t-1", "t-2"], action_state=None, task_svc=ts, skip_task_id="",
            party_id=_PARTY, authz=_authz_ok(),
        )
        assert ts.transition_status.call_count == 2

    # ── error isolation ───────────────────────────────────────────────────────

    def test_dismiss_error_on_first_does_not_stop_second(self):
        as_ = self._make_action_state()
        as_.dismiss.side_effect = [RuntimeError("db locked"), None]
        # Should not raise; second call must still run.
        _bulk_resolve(["a1", "a2"], [], action_state=as_, task_svc=None, party_id=_PARTY, authz=_authz_ok())
        assert as_.dismiss.call_count == 2

    def test_task_transition_error_on_first_does_not_stop_second(self):
        ts = self._make_task_svc()
        ts.transition_status.side_effect = [ValueError("bad transition"), None]
        _bulk_resolve([], ["t-1", "t-2"], action_state=None, task_svc=ts, party_id=_PARTY, authz=_authz_ok())
        assert ts.transition_status.call_count == 2

    # ── combined action + task ────────────────────────────────────────────────

    def test_combined_action_and_task(self):
        as_ = self._make_action_state()
        ts = self._make_task_svc()
        _bulk_resolve(
            ["a1"], ["t1"], action_state=as_, task_svc=ts, actor_id="u1",
            party_id=_PARTY, authz=_authz_ok(),
        )
        as_.dismiss.assert_called_once_with("a1", user_id="u1")
        ts.transition_status.assert_called_once_with("t1", "done")

    # ── contact_outcome gating (phase-02 Amendment) ───────────────────────────
    # /reason/resolve-async (the cockpit's "+Nhắn Zalo" follow-up button) must
    # apply the SAME no_answer/busy → snooze gate as execute_side_effects()
    # step 7, so that button can't silently undo a snooze that step 7 just made.

    def _make_action_state_with_snooze(self):
        m = MagicMock()
        m.dismiss = MagicMock()
        m.snooze = MagicMock()
        return m

    def test_no_answer_outcome_snoozes_instead_of_dismissing(self):
        as_ = self._make_action_state_with_snooze()
        ts = self._make_task_svc()
        _bulk_resolve(
            ["a1"], ["t1"], action_state=as_, task_svc=ts,
            actor_id="u1", contact_outcome="no_answer",
            party_id=_PARTY, authz=_authz_ok(),
        )
        as_.snooze.assert_called_once()
        assert as_.snooze.call_args.args[0] == "a1"
        as_.dismiss.assert_not_called()
        ts.transition_status.assert_not_called()

    def test_busy_outcome_snoozes_instead_of_dismissing(self):
        as_ = self._make_action_state_with_snooze()
        ts = self._make_task_svc()
        _bulk_resolve(
            ["a1"], ["t1"], action_state=as_, task_svc=ts,
            actor_id="u1", contact_outcome="busy",
            party_id=_PARTY, authz=_authz_ok(),
        )
        as_.snooze.assert_called_once()
        as_.dismiss.assert_not_called()
        ts.transition_status.assert_not_called()

    def test_answered_outcome_keeps_dismiss_and_done(self):
        as_ = self._make_action_state_with_snooze()
        ts = self._make_task_svc()
        _bulk_resolve(
            ["a1"], ["t1"], action_state=as_, task_svc=ts,
            actor_id="u1", contact_outcome="answered",
            party_id=_PARTY, authz=_authz_ok(),
        )
        as_.dismiss.assert_called_once_with("a1", user_id="u1")
        ts.transition_status.assert_called_once_with("t1", "done")
        as_.snooze.assert_not_called()

    def test_missing_contact_outcome_defaults_to_dismiss_and_done(self):
        """Callers that don't pass contact_outcome (pre-amendment behavior, e.g.
        default param) must be unaffected — backward compatible."""
        as_ = self._make_action_state_with_snooze()
        ts = self._make_task_svc()
        _bulk_resolve(
            ["a1"], ["t1"], action_state=as_, task_svc=ts, actor_id="u1",
            party_id=_PARTY, authz=_authz_ok(),
        )
        as_.dismiss.assert_called_once_with("a1", user_id="u1")
        ts.transition_status.assert_called_once_with("t1", "done")
        as_.snooze.assert_not_called()


# ---------------------------------------------------------------------------
# Phase-03 IDOR guard — mismatched action_id/task_id must be skipped, not
# mutated. Uses a REAL AuthorizationService (pure identity comparison) with
# action_state.resolve_party_id() / task_svc.get_task() configured per-id so
# the guard's actual resolve-then-compare logic is exercised, not bypassed.
# ---------------------------------------------------------------------------

class TestBulkResolveIdorGuard:
    def test_mismatched_action_id_skipped_valid_id_still_dismissed(self):
        """2-id batch: a1 belongs to the requesting party, a2 belongs to a
        different party — a2 must be skipped (not dismissed), a1 must still
        be processed (per-item isolation preserved)."""
        as_ = MagicMock()
        as_.resolve_party_id.side_effect = lambda aid: {
            "a1": _PARTY, "a2": "other-party",
        }[aid]
        _bulk_resolve(
            ["a1", "a2"], [], action_state=as_, task_svc=None,
            party_id=_PARTY, authz=AuthorizationService(),
        )
        as_.dismiss.assert_called_once_with("a1", user_id=None)

    def test_mismatched_task_id_skipped_valid_task_still_transitioned(self):
        ts = MagicMock()
        ts.get_task.side_effect = lambda tid: {
            "t1": MagicMock(party_id=_PARTY),
            "t2": MagicMock(party_id="other-party"),
        }[tid]
        _bulk_resolve(
            [], ["t1", "t2"], action_state=None, task_svc=ts,
            party_id=_PARTY, authz=AuthorizationService(),
        )
        ts.transition_status.assert_called_once_with("t1", "done")

    def test_unresolvable_action_id_fails_closed(self):
        """action_state.resolve_party_id returning None (not found in cache)
        must be treated as a mismatch, not implicitly valid."""
        as_ = MagicMock()
        as_.resolve_party_id.return_value = None
        _bulk_resolve(
            ["ghost-action"], [], action_state=as_, task_svc=None,
            party_id=_PARTY, authz=AuthorizationService(),
        )
        as_.dismiss.assert_not_called()

    def test_unresolvable_task_id_fails_closed(self):
        """task_svc.get_task returning None (task not found) must be treated
        as a mismatch, not implicitly valid."""
        ts = MagicMock()
        ts.get_task.return_value = None
        _bulk_resolve(
            [], ["ghost-task"], action_state=None, task_svc=ts,
            party_id=_PARTY, authz=AuthorizationService(),
        )
        ts.transition_status.assert_not_called()

    def test_mismatched_action_id_snooze_path_also_skipped(self):
        """no_contact outcomes route through snooze() instead of dismiss() —
        the guard must apply there too, not just the dismiss branch."""
        as_ = MagicMock()
        as_.resolve_party_id.return_value = "other-party"
        _bulk_resolve(
            ["a1"], [], action_state=as_, task_svc=None,
            contact_outcome="no_answer",
            party_id=_PARTY, authz=AuthorizationService(),
        )
        as_.snooze.assert_not_called()

"""Pure-logic unit tests for Phase 04 outcome bulk-resolve helpers.

Tests cover:
- _parse_id_list: comma-separated parsing, empty/whitespace handling
- _bulk_resolve: action dismiss loop, task transition loop, skip_task_id guard,
  None-safe when action_state / task_svc are absent, per-item error isolation

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
        _bulk_resolve(["a1"], [], action_state=None, task_svc=None)

    def test_none_task_svc_does_not_raise(self):
        _bulk_resolve([], ["t1"], action_state=None, task_svc=None)

    def test_both_none_and_empty_lists_no_op(self):
        _bulk_resolve([], [], action_state=None, task_svc=None)

    # ── action_ids dispatched to dismiss ─────────────────────────────────────

    def test_single_action_dismissed(self):
        as_ = self._make_action_state()
        _bulk_resolve(["act-1"], [], action_state=as_, task_svc=None)
        as_.dismiss.assert_called_once_with("act-1", user_id=None)

    def test_multiple_actions_each_dismissed(self):
        as_ = self._make_action_state()
        _bulk_resolve(["a1", "a2", "a3"], [], action_state=as_, task_svc=None)
        assert as_.dismiss.call_count == 3
        as_.dismiss.assert_any_call("a1", user_id=None)
        as_.dismiss.assert_any_call("a2", user_id=None)
        as_.dismiss.assert_any_call("a3", user_id=None)

    def test_actor_id_passed_to_dismiss(self):
        as_ = self._make_action_state()
        _bulk_resolve(["act-1"], [], action_state=as_, task_svc=None, actor_id="user-xyz")
        as_.dismiss.assert_called_once_with("act-1", user_id="user-xyz")

    def test_empty_actor_id_passes_none_to_dismiss(self):
        as_ = self._make_action_state()
        _bulk_resolve(["act-1"], [], action_state=as_, task_svc=None, actor_id="")
        as_.dismiss.assert_called_once_with("act-1", user_id=None)

    # ── task_ids dispatched to transition_status ──────────────────────────────

    def test_single_task_transitioned_to_done(self):
        ts = self._make_task_svc()
        _bulk_resolve([], ["t-1"], action_state=None, task_svc=ts)
        ts.transition_status.assert_called_once_with("t-1", "done")

    def test_multiple_tasks_all_transitioned(self):
        ts = self._make_task_svc()
        _bulk_resolve([], ["t-1", "t-2"], action_state=None, task_svc=ts)
        assert ts.transition_status.call_count == 2
        ts.transition_status.assert_any_call("t-1", "done")
        ts.transition_status.assert_any_call("t-2", "done")

    # ── skip_task_id guard ────────────────────────────────────────────────────

    def test_skip_task_id_excluded_from_bulk(self):
        ts = self._make_task_svc()
        _bulk_resolve([], ["t-1", "t-2"], action_state=None, task_svc=ts, skip_task_id="t-1")
        ts.transition_status.assert_called_once_with("t-2", "done")

    def test_skip_task_id_not_in_list_no_effect(self):
        ts = self._make_task_svc()
        _bulk_resolve([], ["t-1", "t-2"], action_state=None, task_svc=ts, skip_task_id="t-99")
        assert ts.transition_status.call_count == 2

    def test_skip_task_id_empty_string_resolves_all(self):
        ts = self._make_task_svc()
        _bulk_resolve([], ["t-1", "t-2"], action_state=None, task_svc=ts, skip_task_id="")
        assert ts.transition_status.call_count == 2

    # ── error isolation ───────────────────────────────────────────────────────

    def test_dismiss_error_on_first_does_not_stop_second(self):
        as_ = self._make_action_state()
        as_.dismiss.side_effect = [RuntimeError("db locked"), None]
        # Should not raise; second call must still run.
        _bulk_resolve(["a1", "a2"], [], action_state=as_, task_svc=None)
        assert as_.dismiss.call_count == 2

    def test_task_transition_error_on_first_does_not_stop_second(self):
        ts = self._make_task_svc()
        ts.transition_status.side_effect = [ValueError("bad transition"), None]
        _bulk_resolve([], ["t-1", "t-2"], action_state=None, task_svc=ts)
        assert ts.transition_status.call_count == 2

    # ── combined action + task ────────────────────────────────────────────────

    def test_combined_action_and_task(self):
        as_ = self._make_action_state()
        ts = self._make_task_svc()
        _bulk_resolve(["a1"], ["t1"], action_state=as_, task_svc=ts, actor_id="u1")
        as_.dismiss.assert_called_once_with("a1", user_id="u1")
        ts.transition_status.assert_called_once_with("t1", "done")

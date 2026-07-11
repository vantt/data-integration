"""test_customer_360_tasks_party_guard.py — Phase 03 (260711-1227) IDOR fix,
2nd site: PATCH /customers/{party_id}/tasks/{task_id}/{done,cancel,postpone}.

These 3 handlers took party_id as a URL path segment but mutated task_id
without ever checking the task's real party_id against it — task_id values
are visible across the app (worklist rows, task board), so exploiting this
required no more than viewing another customer's page first. Fixed by
resolving the task via task_svc.get_task(task_id) and rejecting (403) when
authz.is_same_party(task.party_id, party_id) is False, before any mutation.

Follows the mock-router-closure recovery pattern from
test_bulk_resolve_endpoint.py — no FastAPI TestClient; handlers recovered
from router.patch.call_args_list.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
from unittest.mock import MagicMock

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # data-integration/
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1]) # crm/src/
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from application.authorization_service import AuthorizationService  # noqa: E402
import adapters.inbound.web.screens.customer360.screen_customer_360_tasks as mod  # noqa: E402

_OWNER_PARTY = "party-owner"
_OTHER_PARTY = "party-other"


def _register(task_svc):
    router_mock = MagicMock()
    templates_mock = MagicMock()
    mod.register_task_routes(
        router_mock, templates_mock,
        party_tasks=MagicMock(),
        authz=AuthorizationService(),
        task_svc=task_svc,
        app_users=None,
    )
    patch_calls = router_mock.patch.return_value.call_args_list
    assert len(patch_calls) >= 3, "Expected 3 PATCH handlers (done, cancel, postpone)"
    return {
        "done": patch_calls[0].args[0],
        "cancel": patch_calls[1].args[0],
        "postpone": patch_calls[2].args[0],
    }


def _req():
    request_mock = MagicMock()
    request_mock.query_params.get.return_value = "open"
    return request_mock


class TestTaskDoneCrossPartyRejected:
    def test_cross_party_task_id_returns_403(self):
        task_svc = MagicMock()
        task_svc.get_task.return_value = MagicMock(party_id=_OTHER_PARTY)
        handlers = _register(task_svc)

        r = asyncio.run(handlers["done"](
            request=_req(), party_id=_OWNER_PARTY, task_id="foreign-task",
        ))
        assert r.status_code == 403
        task_svc.transition_status.assert_not_called()

    def test_own_task_id_still_completes(self):
        """Regression guard: the guard must not block the legitimate case."""
        task_svc = MagicMock()
        task_svc.get_task.return_value = MagicMock(party_id=_OWNER_PARTY)
        handlers = _register(task_svc)

        asyncio.run(handlers["done"](
            request=_req(), party_id=_OWNER_PARTY, task_id="own-task",
        ))
        task_svc.transition_status.assert_called_once_with("own-task", "done")


class TestTaskCancelCrossPartyRejected:
    def test_cross_party_task_id_returns_403(self):
        task_svc = MagicMock()
        task_svc.get_task.return_value = MagicMock(party_id=_OTHER_PARTY)
        handlers = _register(task_svc)

        r = asyncio.run(handlers["cancel"](
            request=_req(), party_id=_OWNER_PARTY, task_id="foreign-task",
        ))
        assert r.status_code == 403
        task_svc.transition_status.assert_not_called()

    def test_own_task_id_still_cancels(self):
        task_svc = MagicMock()
        task_svc.get_task.return_value = MagicMock(party_id=_OWNER_PARTY)
        handlers = _register(task_svc)

        asyncio.run(handlers["cancel"](
            request=_req(), party_id=_OWNER_PARTY, task_id="own-task",
        ))
        task_svc.transition_status.assert_called_once_with("own-task", "cancelled")


class TestTaskPostponeCrossPartyRejected:
    def test_cross_party_task_id_returns_403(self):
        task_svc = MagicMock()
        task_svc.get_task.return_value = MagicMock(party_id=_OTHER_PARTY, status="open")
        handlers = _register(task_svc)

        r = asyncio.run(handlers["postpone"](
            request=_req(), party_id=_OWNER_PARTY, task_id="foreign-task",
            due_date="2026-08-01", due_time="09:00",
        ))
        assert r.status_code == 403
        task_svc.update_task.assert_not_called()

    def test_own_task_id_still_postpones(self):
        task_svc = MagicMock()
        task_svc.get_task.return_value = MagicMock(party_id=_OWNER_PARTY, status="open")
        handlers = _register(task_svc)

        asyncio.run(handlers["postpone"](
            request=_req(), party_id=_OWNER_PARTY, task_id="own-task",
            due_date="2026-08-01", due_time="09:00",
        ))
        task_svc.update_task.assert_called_once()


class TestTaskUnresolvableIdFailsClosed:
    """A task_id the resolver can't find at all (get_task → None) must be
    treated as a mismatch, not implicitly allowed."""

    def test_done_ghost_task_id_returns_403(self):
        task_svc = MagicMock()
        task_svc.get_task.return_value = None
        handlers = _register(task_svc)

        r = asyncio.run(handlers["done"](
            request=_req(), party_id=_OWNER_PARTY, task_id="ghost-task",
        ))
        assert r.status_code == 403
        task_svc.transition_status.assert_not_called()

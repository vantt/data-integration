"""Endpoint-level tests for S07 Tasks Board's POST /tasks handler (no-party task creation fix):

- worklist header "+ Tao task" (no party_id) -> 200/204, not 404 (route-level fix; the real
  pre-fix 404 came from the M05 form posting to /customers//tasks, which does not
  route-match -- this suite exercises the corrected target, POST /tasks, directly)
- return_to="stay" -> no HX-Redirect header, HX-Trigger present (worklistRefresh + closeModal)
- return_to omitted/default -> unchanged HX-Redirect: /tasks behavior (regression-safe)
- priority/task_kind/source/source_ref forwarded into task_data when present

Follows the mock-closure pattern from test_modal_task_return_to.py -- no FastAPI TestClient;
handler is recovered from the router.post decorator call_args_list and invoked directly with
explicit keyword arguments.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock

import pytest

# ── sys.path setup (mirrors conftest.py / test_modal_task_return_to.py) ────────────
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # data-integration/
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # crm/src/
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _get_create_task_handler(task_creator_mock=None):
    """Register tasks board routes on a mock router and recover handle_create_task.

    make_tasks_board_router creates the router internally (`router = APIRouter()`), so —
    mirroring test_modal_task_return_to.py's `_get_task_modal_handlers` pattern — we patch
    APIRouter to intercept and capture the mock router it constructs.

    make_tasks_board_router registers, in order: GET /tasks, GET /tasks/dismissed,
    POST /tasks (handle_create_task), PATCH /tasks/{id}/status, POST /tasks/generate.
    handle_create_task is the FIRST @router.post call.

    Returns: (handle_create_task_handler, task_creator_mock)
    """
    from unittest.mock import patch

    router_mock = None
    if task_creator_mock is None:
        task_creator_mock = MagicMock()
        task_creator_mock.create_task.return_value = None

    def mock_api_router(*args, **kwargs):
        nonlocal router_mock
        router_mock = MagicMock()
        return router_mock

    with patch(
        'crm.src.adapters.inbound.web.screen_tasks_board.APIRouter',
        side_effect=mock_api_router,
    ):
        import crm.src.adapters.inbound.web.screen_tasks_board as mod

        templates_mock = MagicMock()
        task_querier_mock = MagicMock()
        task_writer_mock = MagicMock()

        mod.make_tasks_board_router(
            templates=templates_mock,
            task_querier=task_querier_mock,
            task_writer=task_writer_mock,
            task_creator=task_creator_mock,
        )

    post_decorator_calls = router_mock.post.return_value.call_args_list
    assert len(post_decorator_calls) >= 1, "Expected at least one POST handler"
    handle_create_task = post_decorator_calls[0].args[0]

    return handle_create_task, task_creator_mock


def _create_task_base_kwargs(**overrides) -> dict:
    """Base kwargs for handle_create_task handler invocation (no party_id -- worklist header case)."""
    kwargs = dict(
        request=MagicMock(state=MagicMock(current_user=None)),
        title="Follow-up call",
        description="",
        due_at="",
        party_id="",
        assignee_user_id="",
        priority="P3",
        task_kind="",
        source="manual",
        source_ref="",
        return_to="stay",
    )
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# No-party creation: no 404, task created successfully
# ---------------------------------------------------------------------------

def test_create_task_no_party_id_succeeds_no_404():
    """Worklist header '+ Tao task' (no party_id) posting to /tasks -> 200, not 404."""
    import asyncio

    handler, task_creator_mock = _get_create_task_handler()

    response = asyncio.run(handler(**_create_task_base_kwargs()))

    assert response.status_code in (200, 204), (
        f"Expected 200/204 for no-party task creation, got {response.status_code}"
    )
    task_creator_mock.create_task.assert_called_once()
    task_data = task_creator_mock.create_task.call_args.args[0]
    assert task_data["party_id"] is None
    assert task_data["title"] == "Follow-up call"


# ---------------------------------------------------------------------------
# return_to behavior
# ---------------------------------------------------------------------------

def test_create_task_return_to_stay_no_redirect():
    """return_to='stay' -> no HX-Redirect header, worklist stays in place."""
    import asyncio

    handler, _ = _get_create_task_handler()

    response = asyncio.run(handler(**_create_task_base_kwargs(return_to="stay")))

    assert "HX-Redirect" not in response.headers, (
        "return_to='stay' must NOT have HX-Redirect header"
    )
    assert "HX-Trigger" in response.headers
    assert response.headers["HX-Trigger"] == '{"worklistRefresh": true, "closeModal": true}', (
        f"Expected combined worklistRefresh+closeModal trigger, got: {response.headers.get('HX-Trigger')!r}"
    )


def test_create_task_return_to_redirect_has_redirect():
    """return_to='redirect' -> HX-Redirect: /tasks (explicit)."""
    import asyncio

    handler, _ = _get_create_task_handler()

    response = asyncio.run(handler(**_create_task_base_kwargs(return_to="redirect")))

    assert response.headers.get("HX-Redirect") == "/tasks"


def test_create_task_return_to_omitted_defaults_to_redirect():
    """return_to omitted -> unchanged HX-Redirect: /tasks behavior (regression-safe)."""
    import asyncio

    handler, _ = _get_create_task_handler()

    kwargs = _create_task_base_kwargs()
    kwargs.pop("return_to")  # rely on Form default="redirect"

    response = asyncio.run(handler(**kwargs))

    assert response.headers.get("HX-Redirect") == "/tasks", (
        "return_to omitted must default to redirect behavior"
    )
    assert response.headers.get("HX-Trigger") == '{"closeModal":true}'


# ---------------------------------------------------------------------------
# Field forwarding: priority / task_kind / source / source_ref
# ---------------------------------------------------------------------------

def test_create_task_forwards_priority_task_kind_source_source_ref():
    """M05-sent optional fields are forwarded into task_data for TaskService.create_task()."""
    import asyncio

    handler, task_creator_mock = _get_create_task_handler()

    asyncio.run(handler(**_create_task_base_kwargs(
        priority="P1",
        task_kind="internal",
        source="action_queue",
        source_ref="aq-123",
        return_to="stay",
    )))

    task_data = task_creator_mock.create_task.call_args.args[0]
    assert task_data["priority"] == 2  # P1 -> 2 per PRIO_STR_TO_INT
    assert task_data["task_kind"] == "internal"
    assert task_data["source"] == "action_queue"
    assert task_data["source_ref"] == "aq-123"


def test_create_task_default_priority_matches_prior_hardcoded_behavior():
    """A caller sending the Form default priority ("P3", matching Form(default="P3"))
    still resolves to the same int 0 the handler hardcoded before this change.

    (The mock-closure pattern invokes the handler directly, bypassing FastAPI's DI, so
    omitting a Form(...) kwarg entirely yields the raw Form() marker object rather than
    its resolved default -- this test instead pins the resolved value a real request
    would produce for a caller that doesn't send `priority`.)
    """
    import asyncio

    handler, task_creator_mock = _get_create_task_handler()

    asyncio.run(handler(**_create_task_base_kwargs(priority="P3")))

    task_data = task_creator_mock.create_task.call_args.args[0]
    assert task_data["priority"] == 0


def test_create_task_missing_title_returns_400():
    """Blank title still rejected with 400 (unchanged validation)."""
    import asyncio

    handler, _ = _get_create_task_handler()

    response = asyncio.run(handler(**_create_task_base_kwargs(title="   ")))

    assert response.status_code == 400

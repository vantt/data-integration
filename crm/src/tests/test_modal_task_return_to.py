"""Endpoint-level tests for M05 task modal handlers (return_to behavior):

- return_to="stay" → no HX-Redirect header, HX-Trigger present instead
- return_to="redirect" (or omitted/default) → HX-Redirect present, no HX-Trigger

Follows the mock-closure pattern from test_quick_outcome_cockpit_post.py — no FastAPI
TestClient; handlers are recovered from the router.post/patch decorator call_args_list
and invoked directly with explicit keyword arguments.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock

import pytest

# ── sys.path setup (mirrors conftest.py / test_quick_outcome_cockpit_post.py) ──────
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # data-integration/
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1]) # crm/src/
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _get_task_modal_handlers():
    """Register task modal routes on a mock router and recover post_task and patch_task_edit.

    make_task_modal_router creates the router internally, so we mock APIRouter to intercept
    and provide a mock router. The handlers are closures capturing the mocked dependencies.

    Returns: (post_task_handler, patch_task_edit_handler, task_svc_mock)
    """
    from unittest.mock import patch

    # We'll capture the router_mock created inside make_task_modal_router
    router_mock = None
    task_svc_mock = MagicMock()

    def mock_api_router(*args, **kwargs):
        nonlocal router_mock
        router_mock = MagicMock()
        return router_mock

    with patch('crm.src.adapters.inbound.web.screens.modals.screen_modal_task.APIRouter', side_effect=mock_api_router):
        import crm.src.adapters.inbound.web.screens.modals.screen_modal_task as mod

        templates_mock = MagicMock()
        profile_mock = MagicMock()
        app_users_mock = MagicMock()

        mod.make_task_modal_router(
            templates=templates_mock,
            profile=profile_mock,
            task_svc=task_svc_mock,
            app_users=app_users_mock,
        )

    # Recover post_task handler (decorated with @router.post)
    post_decorator_calls = router_mock.post.return_value.call_args_list
    assert len(post_decorator_calls) >= 1, "Expected at least one POST handler"
    post_task_handler = post_decorator_calls[0].args[0]

    # Recover patch_task_edit handler (decorated with @router.patch)
    patch_decorator_calls = router_mock.patch.return_value.call_args_list
    assert len(patch_decorator_calls) >= 1, "Expected at least one PATCH handler"
    patch_task_edit_handler = patch_decorator_calls[0].args[0]

    return post_task_handler, patch_task_edit_handler, task_svc_mock


def _post_task_base_kwargs(**overrides) -> dict:
    """Base kwargs for post_task handler invocation."""
    kwargs = dict(
        request=MagicMock(state=MagicMock(current_user=None)),
        party_id="party-m05-1",
        title="Test Task",
        description="",
        due_at="",
        assignee_user_id="",
        priority="P3",
        source="manual",
        source_ref="",
        task_kind="",
        return_to="redirect",
    )
    kwargs.update(overrides)
    return kwargs


def _patch_task_edit_base_kwargs(**overrides) -> dict:
    """Base kwargs for patch_task_edit handler invocation."""
    kwargs = dict(
        request=MagicMock(state=MagicMock(current_user=None)),
        task_id="task-m05-1",
        title="Updated Task",
        description="",
        due_at="",
        priority="P3",
        assignee_user_id="",
        party_id="party-m05-1",
        return_to="redirect",
    )
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# post_task tests
# ---------------------------------------------------------------------------

def test_post_task_return_to_stay_no_redirect():
    """post_task with return_to='stay' → no HX-Redirect, has HX-Trigger."""
    import asyncio

    post_task_handler, _, task_svc_mock = _get_task_modal_handlers()
    task_svc_mock.create_task.return_value = None

    response = asyncio.run(post_task_handler(**_post_task_base_kwargs(
        return_to="stay",
    )))

    assert "HX-Redirect" not in response.headers, (
        "post_task with return_to='stay' must NOT have HX-Redirect header"
    )
    assert "HX-Trigger" in response.headers, (
        "post_task with return_to='stay' must have HX-Trigger header"
    )
    assert response.headers["HX-Trigger"] == '{"worklistRefresh": true}', (
        f"Expected HX-Trigger with worklistRefresh, got: {response.headers.get('HX-Trigger')!r}"
    )


def test_post_task_return_to_redirect_has_redirect():
    """post_task with return_to='redirect' (or omitted) → HX-Redirect present."""
    import asyncio

    post_task_handler, _, task_svc_mock = _get_task_modal_handlers()
    task_svc_mock.create_task.return_value = None

    response = asyncio.run(post_task_handler(**_post_task_base_kwargs(
        return_to="redirect",
        party_id="party-m05-2",
    )))

    assert "HX-Redirect" in response.headers, (
        "post_task with return_to='redirect' must have HX-Redirect header"
    )
    redirect_val = response.headers["HX-Redirect"]
    # post_task uses redirect_to_customer which redirects to /customers/{party_id} without ?tab=tasks
    assert redirect_val == "/customers/party-m05-2", (
        f"Expected HX-Redirect to /customers/party-m05-2, got: {redirect_val!r}"
    )


def test_post_task_return_to_omitted_defaults_to_redirect():
    """post_task with return_to omitted → defaults to redirect behavior."""
    import asyncio

    post_task_handler, _, task_svc_mock = _get_task_modal_handlers()
    task_svc_mock.create_task.return_value = None

    # Invoke without explicitly setting return_to (relies on Form default="redirect")
    kwargs = _post_task_base_kwargs()
    kwargs.pop("return_to")  # Remove to test default

    response = asyncio.run(post_task_handler(**kwargs))

    assert "HX-Redirect" in response.headers, (
        "post_task with return_to omitted must default to redirect behavior"
    )


def test_post_task_no_party_id_redirect_to_customers_empty():
    """post_task with no party_id redirects to /customers/ (redirect_to_customer uses party_id as-is)."""
    import asyncio

    post_task_handler, _, task_svc_mock = _get_task_modal_handlers()
    task_svc_mock.create_task.return_value = None

    response = asyncio.run(post_task_handler(**_post_task_base_kwargs(
        return_to="redirect",
        party_id="",
    )))

    assert "HX-Redirect" in response.headers
    redirect_val = response.headers["HX-Redirect"]
    # post_task uses redirect_to_customer which uses party_id as-is, resulting in /customers/
    assert redirect_val == "/customers/", (
        f"Expected HX-Redirect to /customers/ when party_id empty, got: {redirect_val!r}"
    )


# ---------------------------------------------------------------------------
# patch_task_edit tests
# ---------------------------------------------------------------------------

def test_patch_task_edit_return_to_stay_no_redirect():
    """patch_task_edit with return_to='stay' → no HX-Redirect, has HX-Trigger."""
    import asyncio

    _, patch_task_edit_handler, task_svc_mock = _get_task_modal_handlers()
    task_svc_mock.update_task.return_value = None

    response = asyncio.run(patch_task_edit_handler(**_patch_task_edit_base_kwargs(
        return_to="stay",
    )))

    assert "HX-Redirect" not in response.headers, (
        "patch_task_edit with return_to='stay' must NOT have HX-Redirect header"
    )
    assert "HX-Trigger" in response.headers, (
        "patch_task_edit with return_to='stay' must have HX-Trigger header"
    )
    assert response.headers["HX-Trigger"] == '{"worklistRefresh": true}', (
        f"Expected HX-Trigger with worklistRefresh, got: {response.headers.get('HX-Trigger')!r}"
    )


def test_patch_task_edit_return_to_redirect_has_redirect():
    """patch_task_edit with return_to='redirect' (or omitted) → HX-Redirect present."""
    import asyncio

    _, patch_task_edit_handler, task_svc_mock = _get_task_modal_handlers()
    task_svc_mock.update_task.return_value = None

    response = asyncio.run(patch_task_edit_handler(**_patch_task_edit_base_kwargs(
        return_to="redirect",
        party_id="party-m05-3",
    )))

    assert "HX-Redirect" in response.headers, (
        "patch_task_edit with return_to='redirect' must have HX-Redirect header"
    )
    redirect_val = response.headers["HX-Redirect"]
    assert redirect_val == "/customers/party-m05-3?tab=tasks", (
        f"Expected HX-Redirect to /customers/party-m05-3?tab=tasks, got: {redirect_val!r}"
    )


def test_patch_task_edit_return_to_omitted_defaults_to_redirect():
    """patch_task_edit with return_to omitted → defaults to redirect behavior."""
    import asyncio

    _, patch_task_edit_handler, task_svc_mock = _get_task_modal_handlers()
    task_svc_mock.update_task.return_value = None

    # Invoke without explicitly setting return_to (relies on Form default="redirect")
    kwargs = _patch_task_edit_base_kwargs()
    kwargs.pop("return_to")  # Remove to test default

    response = asyncio.run(patch_task_edit_handler(**kwargs))

    assert "HX-Redirect" in response.headers, (
        "patch_task_edit with return_to omitted must default to redirect behavior"
    )


def test_patch_task_edit_no_party_id_redirect_to_tasks():
    """patch_task_edit with no party_id redirects to /tasks instead of /customers/...."""
    import asyncio

    _, patch_task_edit_handler, task_svc_mock = _get_task_modal_handlers()
    task_svc_mock.update_task.return_value = None

    response = asyncio.run(patch_task_edit_handler(**_patch_task_edit_base_kwargs(
        return_to="redirect",
        party_id="",
    )))

    assert "HX-Redirect" in response.headers
    redirect_val = response.headers["HX-Redirect"]
    assert redirect_val == "/tasks", (
        f"Expected HX-Redirect to /tasks when party_id empty, got: {redirect_val!r}"
    )

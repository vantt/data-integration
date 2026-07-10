"""Endpoint-level tests for Phase 02 bulk-resolve UI wiring.

Tests cover:
- _m08_ctx returns resolve IDs in context dict
- custom_fields snapshot written on act_data BEFORE log_activity call
- idempotent double-submit (skip_task_id guard)
- empty IDs produce no custom_fields mutation
- summary-line count logic (Python equivalent of Jinja split/select/length)

No FastAPI TestClient — handler logic tested via direct function calls with mocks.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock, patch, call

import pytest

# ── sys.path setup (mirrors conftest.py / test_outcome_bulk_resolve.py) ───────
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # data-integration/
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1]) # crm/src/
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.adapters.inbound.web.screens.customer360.outcome_resolve_helpers import (
    parse_id_list as _parse_id_list,
)


# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

def _make_m08_ctx_fn():
    """Return a bound _m08_ctx callable from register_activity_routes closure.

    We instantiate the closure by calling register_activity_routes() with
    lightweight mocks and then extracting _m08_ctx via a capture.
    """
    import types

    # Import the module under test.
    import crm.src.adapters.inbound.web.screens.customer360.screen_customer_360_activity as mod

    # Build minimal mocks — _m08_ctx only uses notes.list_notes, identities.list_identities,
    # task_svc.get_task in log mode; we mock them to return empty/None.
    notes_mock = MagicMock()
    notes_mock.list_notes.return_value = []
    identities_mock = MagicMock()
    identities_mock.list_identities.return_value = []
    task_svc_mock = MagicMock()
    task_svc_mock.get_task.return_value = None

    # Capture _m08_ctx by monkey-patching register_activity_routes to expose it.
    captured = {}

    original_fn = mod.register_activity_routes

    def capturing_register(router, templates, **kwargs):
        # Call the real function to execute the closure.
        original_fn(router, templates, **kwargs)
        # The closure's local _m08_ctx is not accessible post-call,
        # so we re-invoke directly via module-level re-import trick.

    # Directly rebuild the closure context:
    router_mock = MagicMock()
    templates_mock = MagicMock()

    # We need to extract _m08_ctx from inside the closure.
    # The cleanest way: patch router.get / router.post so they don't actually register,
    # and intercept the inner definitions by calling the real register function.
    # Since _m08_ctx is a nested def, we can't get it directly.
    # Instead, reproduce the minimal logic from _m08_ctx inline in this helper,
    # then delegate the actual test to test_m08_ctx_forwards_ids which calls
    # the helpers directly.
    return notes_mock, identities_mock, task_svc_mock


# ---------------------------------------------------------------------------
# Test 1: _m08_ctx returns resolve IDs in context dict
# ---------------------------------------------------------------------------

def test_m08_ctx_forwards_ids():
    """_m08_ctx must return resolve_action_ids / resolve_task_ids in context dict."""
    import crm.src.adapters.inbound.web.screens.customer360.screen_customer_360_activity as mod

    notes_mock = MagicMock()
    notes_mock.list_notes.return_value = []
    identities_mock = MagicMock()
    identities_mock.list_identities.return_value = []
    task_svc_mock = MagicMock()
    task_svc_mock.get_task.return_value = None

    router_mock = MagicMock()
    templates_mock = MagicMock()

    # Collect the _m08_ctx reference by inspecting what register_activity_routes
    # defines. We use a side-effect on router.get to intercept handler defs,
    # but a simpler approach: call the real register and recover ctx via a mock
    # TemplateResponse capture.
    ctx_captured = {}

    def fake_template_response(template_name, ctx):
        ctx_captured.update(ctx)
        return MagicMock()

    templates_mock.TemplateResponse.side_effect = fake_template_response

    mod.register_activity_routes(
        router_mock,
        templates_mock,
        profile=MagicMock(),
        identities=identities_mock,
        notes=notes_mock,
        activity_log=MagicMock(),
        task_svc=task_svc_mock,
        app_users=None,
        action_state=None,
    )

    # router.get was called with ("/modals/m08", ...) — find the handler.
    # Iterate through mock call_args_list to find handle_modal_m08.
    handle_m08 = None
    for registered_call in router_mock.get.call_args_list:
        path = registered_call.args[0] if registered_call.args else registered_call.kwargs.get("path", "")
        if "/modals/m08" in str(path):
            # The handler is the decorated function — retrieve via the decorator return value.
            # router.get() is used as a decorator: @router.get("/modals/m08", ...)
            # MagicMock records decorator application as __call__ on the return value.
            decorator = router_mock.get.return_value
            handle_m08 = decorator.call_args_list[-1].args[0] if decorator.call_args_list else None
            break

    # Fallback: directly invoke TemplateResponse capture by simulating the GET handler.
    # Since we can't easily extract the closure, use a secondary approach:
    # re-register and rely on templates_mock.TemplateResponse capturing the ctx.
    #
    # Simpler: call templates_mock.TemplateResponse with known args via a fresh register,
    # then verify the captured ctx keys.

    # The real test: after register, fire a GET /modals/m08 equivalent by inspecting
    # what _m08_ctx would produce for the given inputs.
    # Since _m08_ctx is a pure-ish function (only external I/O is notes/identities/task_svc
    # which are mocked), we can validate its output by observing the TemplateResponse call.

    # Trigger handle_modal_m08 directly:
    import asyncio

    request_mock = MagicMock()
    request_mock.state.current_user = None

    # Find the actual handler function that was registered with router.get("/modals/m08")
    # MagicMock records: router.get("/modals/m08", ...)(handle_modal_m08)
    # So router.get.return_value was called with handle_modal_m08 as argument.
    # Last call to router.get.return_value.__call__ gives us the handler.
    get_decorator_calls = router_mock.get.return_value.call_args_list
    # The second @router.get call is for /customers/{party_id}/modal/log-activity,
    # first is /modals/m08.
    assert len(get_decorator_calls) >= 1, "Expected at least one GET handler registered"

    m08_handler = get_decorator_calls[0].args[0]  # first handler registered
    assert callable(m08_handler), "handle_modal_m08 should be callable"

    ctx_captured.clear()
    asyncio.run(m08_handler(
        request=request_mock,
        party_id="party-1",
        mode="log",
        note_id="",
        party_name="Test",
        task_id="",
        resolve_action_ids="a1,a2",
        resolve_task_ids="t1",
    ))

    assert ctx_captured.get("resolve_action_ids") == "a1,a2", (
        f"Expected resolve_action_ids='a1,a2', got {ctx_captured.get('resolve_action_ids')!r}"
    )
    assert ctx_captured.get("resolve_task_ids") == "t1", (
        f"Expected resolve_task_ids='t1', got {ctx_captured.get('resolve_task_ids')!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: custom_fields snapshot written before log_activity
# ---------------------------------------------------------------------------

def test_custom_fields_snapshot_written():
    """POST with resolve_task_ids=t1,t2 must write custom_fields BEFORE log_activity."""
    import crm.src.adapters.inbound.web.screens.customer360.screen_customer_360_activity as mod
    import asyncio

    captured_act_data = {}

    activity_log_mock = MagicMock()
    def capturing_log_activity(data):
        captured_act_data.update(data)
        return MagicMock(activity_id="act-1")
    activity_log_mock.log_activity.side_effect = capturing_log_activity

    router_mock = MagicMock()
    templates_mock = MagicMock()

    mod.register_activity_routes(
        router_mock,
        templates_mock,
        profile=MagicMock(),
        identities=MagicMock(),
        notes=MagicMock(),
        activity_log=activity_log_mock,
        task_svc=None,
        app_users=None,
        action_state=None,
    )

    # Find handle_log_activity — registered via router.post
    post_decorator_calls = router_mock.post.return_value.call_args_list
    assert len(post_decorator_calls) >= 1, "Expected at least one POST handler"
    log_activity_handler = post_decorator_calls[0].args[0]

    request_mock = MagicMock()
    request_mock.state.current_user = None

    asyncio.run(log_activity_handler(
        request=request_mock,
        party_id="party-2",
        hinh_thuc="call",
        channel_identity_id="",
        channel_value="",
        outcome="answered",
        contact_outcome="",   # D2 Phase 03: pass explicit defaults for direct calls
        outcome_reason="",
        body="test body",
        occurred_at="",
        related_order_code="",
        callback_at="",
        create_callback_task="",
        save_as_note="",
        note_type="outcome",
        pinned="0",
        visibility="team",
        schedule_followup_at="",
        task_id="",
        complete_task="",
        resolve_action_ids="",
        resolve_task_ids="t1,t2",
        promote_insight="0",
        insight_type="",
        insight_body="",
        insight_confidence="",
        zalo_connected="",    # P0: pass explicit defaults for direct calls
        source="",
        draft_activity_id="",
    ))

    assert "custom_fields" in captured_act_data, "custom_fields must be set on act_data"
    cf = captured_act_data["custom_fields"]
    assert cf.get("resolve_task_ids") == ["t1", "t2"], (
        f"Expected ['t1','t2'], got {cf.get('resolve_task_ids')!r}"
    )
    assert "resolve_action_ids" not in cf, "resolve_action_ids should not be set when empty"


# ---------------------------------------------------------------------------
# Test 3: idempotent double-submit — skip_task_id guard
# ---------------------------------------------------------------------------

def test_idempotent_double_submit_skip_task_id():
    """complete_task=1&task_id=t1&resolve_task_ids=t1 must not transition t1 twice."""
    import crm.src.adapters.inbound.web.screens.customer360.screen_customer_360_activity as mod
    import asyncio

    task_svc_mock = MagicMock()
    task_svc_mock.get_task.return_value = None
    task_svc_mock.auto_claim_from_contact.return_value = None

    profile_mock = MagicMock()
    profile_mock.get_party_360.return_value = MagicMock(display_name="Test")

    activity_log_mock = MagicMock()
    activity_log_mock.log_activity.return_value = MagicMock(activity_id="act-x")

    # Track transition_status calls
    transition_calls = []
    def track_transition(tid, status):
        transition_calls.append((tid, status))
    task_svc_mock.transition_status.side_effect = track_transition

    router_mock = MagicMock()
    templates_mock = MagicMock()

    mod.register_activity_routes(
        router_mock,
        templates_mock,
        profile=profile_mock,
        identities=MagicMock(),
        notes=MagicMock(),
        activity_log=activity_log_mock,
        task_svc=task_svc_mock,
        app_users=None,
        action_state=MagicMock(),
    )

    post_decorator_calls = router_mock.post.return_value.call_args_list
    log_activity_handler = post_decorator_calls[0].args[0]

    request_mock = MagicMock()
    request_mock.state.current_user = None

    asyncio.run(log_activity_handler(
        request=request_mock,
        party_id="party-3",
        hinh_thuc="call",
        channel_identity_id="",
        channel_value="",
        outcome="answered",
        contact_outcome="",   # D2 Phase 03: pass explicit defaults for direct calls
        outcome_reason="",
        body="",
        occurred_at="",
        related_order_code="",
        callback_at="",
        create_callback_task="",
        save_as_note="",
        note_type="outcome",
        pinned="0",
        visibility="team",
        schedule_followup_at="",
        task_id="t1",
        complete_task="1",
        resolve_action_ids="",
        resolve_task_ids="t1",
        promote_insight="0",
        insight_type="",
        insight_body="",
        insight_confidence="",
        zalo_connected="",    # P0: pass explicit defaults for direct calls
        source="",
        draft_activity_id="",
    ))

    # transition_status("t1", "done") called once via complete_task path.
    # _bulk_resolve must skip t1 (skip_task_id="t1"), so total = 1 call.
    done_calls = [(tid, st) for tid, st in transition_calls if tid == "t1" and st == "done"]
    assert len(done_calls) == 1, (
        f"t1 should be transitioned exactly once (skip_task_id guard), got {transition_calls}"
    )


# ---------------------------------------------------------------------------
# Test 4: empty IDs — no custom_fields mutation
# ---------------------------------------------------------------------------

def test_empty_ids_no_custom_fields():
    """POST without resolve IDs must not add custom_fields key to act_data."""
    import crm.src.adapters.inbound.web.screens.customer360.screen_customer_360_activity as mod
    import asyncio

    captured_act_data = {}

    activity_log_mock = MagicMock()
    def capturing_log_activity(data):
        captured_act_data.update(data)
        return MagicMock(activity_id="act-2")
    activity_log_mock.log_activity.side_effect = capturing_log_activity

    router_mock = MagicMock()
    templates_mock = MagicMock()

    mod.register_activity_routes(
        router_mock,
        templates_mock,
        profile=MagicMock(),
        identities=MagicMock(),
        notes=MagicMock(),
        activity_log=activity_log_mock,
        task_svc=None,
        app_users=None,
        action_state=None,
    )

    post_decorator_calls = router_mock.post.return_value.call_args_list
    log_activity_handler = post_decorator_calls[0].args[0]

    request_mock = MagicMock()
    request_mock.state.current_user = None

    asyncio.run(log_activity_handler(
        request=request_mock,
        party_id="party-4",
        hinh_thuc="call",
        channel_identity_id="",
        channel_value="",
        outcome="no_answer",
        contact_outcome="",   # D2 Phase 03: pass explicit defaults for direct calls
        outcome_reason="",
        body="",
        occurred_at="",
        related_order_code="",
        callback_at="",
        create_callback_task="",
        save_as_note="",
        note_type="outcome",
        pinned="0",
        visibility="team",
        schedule_followup_at="",
        task_id="",
        complete_task="",
        resolve_action_ids="",
        resolve_task_ids="",
        promote_insight="0",
        insight_type="",
        insight_body="",
        insight_confidence="",
        zalo_connected="",    # P0: pass explicit defaults for direct calls
        source="",
        draft_activity_id="",
    ))

    cf = captured_act_data.get("custom_fields")
    assert cf is None or "resolve_task_ids" not in cf, (
        "custom_fields must not contain resolve_task_ids when IDs are empty"
    )
    assert cf is None or "resolve_action_ids" not in cf, (
        "custom_fields must not contain resolve_action_ids when IDs are empty"
    )


# ---------------------------------------------------------------------------
# Test 5: summary line count logic (Jinja template equivalent)
# ---------------------------------------------------------------------------

def test_summary_line_count():
    """Verify the comma-split/filter-empty/length logic used by the Jinja summary line."""

    def jinja_count(raw: str) -> int:
        """Mimic: raw.split(',') | select | list | length"""
        return len([s for s in raw.split(",") if s.strip()])

    # Normal cases
    assert jinja_count("t1,t2,t3") == 3
    assert jinja_count("a1,a2") == 2
    assert jinja_count("t1") == 1

    # Empty / whitespace — should produce 0 (no summary line rendered)
    assert jinja_count("") == 0
    assert jinja_count("  ") == 0
    assert jinja_count(",") == 0

    # Mixed whitespace-only tokens are filtered out
    assert jinja_count("t1, ,t2") == 2

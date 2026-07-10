"""Endpoint-level tests for phase-01 (activity-log disposition API, P0):

- source=call_cockpit → small confirmation fragment, NO HX-Redirect header
- source absent (M08 / timeline) → HX-Redirect kept (regression guard)
- zalo_connected=1 → custom_fields.zalo_connected=True written before log_activity
- zalo_connected absent → custom_fields untouched (no accidental key)

Follows the mock-closure pattern from test_bulk_resolve_endpoint.py — no FastAPI
TestClient; handle_log_activity is recovered from the router.post() decorator
call_args_list and invoked directly with explicit keyword arguments.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock

import pytest

# ── sys.path setup (mirrors conftest.py / test_bulk_resolve_endpoint.py) ──────
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # data-integration/
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1]) # crm/src/
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _get_log_activity_handler(activity_log_mock, task_svc=None, profile=None):
    """Register the routes on a mock router and recover handle_log_activity."""
    import crm.src.adapters.inbound.web.screens.customer360.screen_customer_360_activity as mod

    router_mock = MagicMock()
    templates_mock = MagicMock()

    mod.register_activity_routes(
        router_mock,
        templates_mock,
        profile=profile or MagicMock(),
        identities=MagicMock(),
        notes=MagicMock(),
        activity_log=activity_log_mock,
        task_svc=task_svc,
        app_users=None,
        action_state=None,
    )

    post_decorator_calls = router_mock.post.return_value.call_args_list
    assert len(post_decorator_calls) >= 1, "Expected at least one POST handler"
    return post_decorator_calls[0].args[0]


def _base_kwargs(**overrides) -> dict:
    kwargs = dict(
        request=MagicMock(state=MagicMock(current_user=None)),
        party_id="party-cockpit-1",
        hinh_thuc="call",
        channel_identity_id="",
        channel_value="",
        outcome="",
        contact_outcome="no_answer",
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
        zalo_connected="",
        source="",
        draft_activity_id="",
    )
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# source=call_cockpit → confirmation fragment, no HX-Redirect
# ---------------------------------------------------------------------------

def test_call_cockpit_source_returns_fragment_no_redirect():
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.log_activity.return_value = MagicMock(activity_id="act-cockpit-1")

    handler = _get_log_activity_handler(activity_log_mock)

    response = asyncio.run(handler(**_base_kwargs(
        contact_outcome="no_answer",
        source="call_cockpit",
    )))

    assert "HX-Redirect" not in response.headers, (
        "call_cockpit source must NOT redirect — outcome bar swaps a small fragment"
    )
    body = response.body.decode("utf-8")
    assert "Không bắt" in body, f"Expected Vietnamese outcome label in fragment, got: {body!r}"
    assert "s14-outcome__done" in body
    assert "Hoàn tác" in body


def test_call_cockpit_source_busy_label():
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.log_activity.return_value = MagicMock(activity_id="act-cockpit-2")

    handler = _get_log_activity_handler(activity_log_mock)

    response = asyncio.run(handler(**_base_kwargs(
        contact_outcome="busy",
        source="call_cockpit",
    )))

    body = response.body.decode("utf-8")
    assert "Bận" in body
    assert "HX-Redirect" not in response.headers


# ---------------------------------------------------------------------------
# source absent (M08 / timeline) → HX-Redirect kept (regression guard)
# ---------------------------------------------------------------------------

def test_no_source_keeps_hx_redirect():
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.log_activity.return_value = MagicMock(activity_id="act-m08-1")

    handler = _get_log_activity_handler(activity_log_mock)

    response = asyncio.run(handler(**_base_kwargs(
        contact_outcome="answered",
        source="",
    )))

    assert response.headers.get("HX-Redirect") == "/customers/party-cockpit-1?tab=timeline"


def test_unknown_source_keeps_hx_redirect():
    """Only the exact 'call_cockpit' marker skips the redirect."""
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.log_activity.return_value = MagicMock(activity_id="act-m08-2")

    handler = _get_log_activity_handler(activity_log_mock)

    response = asyncio.run(handler(**_base_kwargs(
        contact_outcome="answered",
        source="timeline",
    )))

    assert response.headers.get("HX-Redirect") == "/customers/party-cockpit-1?tab=timeline"


# ---------------------------------------------------------------------------
# zalo_connected → custom_fields.zalo_connected=True
# ---------------------------------------------------------------------------

def test_zalo_connected_written_to_custom_fields():
    import asyncio

    captured_act_data = {}

    activity_log_mock = MagicMock()

    def capturing_log_activity(data):
        captured_act_data.update(data)
        return MagicMock(activity_id="act-zalo-1")

    activity_log_mock.log_activity.side_effect = capturing_log_activity

    handler = _get_log_activity_handler(activity_log_mock)

    asyncio.run(handler(**_base_kwargs(
        contact_outcome="answered",
        zalo_connected="1",
    )))

    cf = captured_act_data.get("custom_fields")
    assert cf is not None, "custom_fields must be set when zalo_connected=1"
    assert cf.get("zalo_connected") is True


def test_zalo_connected_absent_no_custom_fields_key():
    import asyncio

    captured_act_data = {}

    activity_log_mock = MagicMock()

    def capturing_log_activity(data):
        captured_act_data.update(data)
        return MagicMock(activity_id="act-zalo-2")

    activity_log_mock.log_activity.side_effect = capturing_log_activity

    handler = _get_log_activity_handler(activity_log_mock)

    asyncio.run(handler(**_base_kwargs(
        contact_outcome="answered",
        zalo_connected="",
    )))

    cf = captured_act_data.get("custom_fields")
    assert cf is None or "zalo_connected" not in cf


def test_quick_outcome_body_is_persisted():
    """s14QuickOutcomeVals() sends body=<quick-note value> — confirm it reaches
    ActivityService.log_activity unchanged (fix 260710-1447: quick-note capture)."""
    import asyncio

    captured_act_data = {}

    activity_log_mock = MagicMock()

    def capturing_log_activity(data):
        captured_act_data.update(data)
        return MagicMock(activity_id="act-quicknote-1")

    activity_log_mock.log_activity.side_effect = capturing_log_activity

    handler = _get_log_activity_handler(activity_log_mock)

    asyncio.run(handler(**_base_kwargs(
        contact_outcome="no_answer",
        source="call_cockpit",
        body="Khách hẹn gọi lại chiều mai",
    )))

    assert captured_act_data.get("body") == "Khách hẹn gọi lại chiều mai"


def test_zalo_connected_and_resolve_ids_merge_into_same_custom_fields():
    """zalo_connected must coexist with the existing bulk-resolve custom_fields write."""
    import asyncio

    captured_act_data = {}

    activity_log_mock = MagicMock()

    def capturing_log_activity(data):
        captured_act_data.update(data)
        return MagicMock(activity_id="act-zalo-3")

    activity_log_mock.log_activity.side_effect = capturing_log_activity

    handler = _get_log_activity_handler(activity_log_mock)

    asyncio.run(handler(**_base_kwargs(
        contact_outcome="answered",
        zalo_connected="1",
        resolve_task_ids="t1",
    )))

    cf = captured_act_data.get("custom_fields")
    assert cf.get("zalo_connected") is True
    assert cf.get("resolve_task_ids") == ["t1"]

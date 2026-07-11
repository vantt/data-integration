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


def _authz_ok() -> MagicMock:
    """Phase-03 IDOR guard stand-in — always reports "same party" so these
    pre-existing tests (not about the IDOR guard itself) are unaffected."""
    from application.authorization_service import AuthorizationService
    m = MagicMock(spec=AuthorizationService)
    m.is_same_party.return_value = True
    return m


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
        authz=_authz_ok(),
        task_svc=task_svc,
        app_users=None,
        action_state=None,
    )

    post_decorator_calls = router_mock.post.return_value.call_args_list
    assert len(post_decorator_calls) >= 1, "Expected at least one POST handler"
    return post_decorator_calls[0].args[0]


def _get_patch_activity_handler(activity_log_mock, task_svc=None, profile=None):
    """Register the routes on a mock router and recover handle_patch_activity.

    register_activity_routes registers exactly one @router.patch route
    (`/api/activities/{activity_id}`), so index 0 is unambiguous.
    """
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
        authz=_authz_ok(),
        task_svc=task_svc,
        app_users=None,
        action_state=None,
    )

    patch_decorator_calls = router_mock.patch.return_value.call_args_list
    assert len(patch_decorator_calls) >= 1, "Expected at least one PATCH handler"
    return patch_decorator_calls[0].args[0]


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
        return_to="redirect",
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


# ---------------------------------------------------------------------------
# return_to=stay (phase-01 P0): modal returns to invoker instead of redirect
# ---------------------------------------------------------------------------

def test_return_to_stay_no_hx_redirect_has_worklist_trigger():
    """handle_log_activity(return_to='stay') → 200, no HX-Redirect, carries
    HX-Trigger: worklistRefresh so the worklist container auto-refreshes."""
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.log_activity.return_value = MagicMock(activity_id="act-stay-1")

    handler = _get_log_activity_handler(activity_log_mock)

    response = asyncio.run(handler(**_base_kwargs(
        contact_outcome="answered",
        source="",
        return_to="stay",
    )))

    assert response.status_code == 200
    assert "HX-Redirect" not in response.headers
    assert response.headers.get("HX-Trigger") == '{"worklistRefresh": true}'


def test_return_to_redirect_default_unaffected_by_new_param():
    """Default return_to='redirect' (or omitted) must not change pre-existing
    HX-Redirect behaviour — regression guard for the new param's default."""
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.log_activity.return_value = MagicMock(activity_id="act-stay-2")

    handler = _get_log_activity_handler(activity_log_mock)

    response = asyncio.run(handler(**_base_kwargs(
        contact_outcome="answered",
        source="",
    )))

    assert response.headers.get("HX-Redirect") == "/customers/party-cockpit-1?tab=timeline"
    assert "HX-Trigger" not in response.headers


def test_call_cockpit_source_takes_precedence_over_return_to_stay():
    """source='call_cockpit' branch (small confirmation fragment) is checked
    BEFORE return_to — the two P0 flows never collide since call_cockpit
    callers never send return_to=stay, but confirm the resolution order."""
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.log_activity.return_value = MagicMock(activity_id="act-stay-3")

    handler = _get_log_activity_handler(activity_log_mock)

    response = asyncio.run(handler(**_base_kwargs(
        contact_outcome="no_answer",
        source="call_cockpit",
        return_to="stay",
    )))

    body = response.body.decode("utf-8")
    assert "s14-outcome__done" in body
    assert "HX-Redirect" not in response.headers
    assert "HX-Trigger" not in response.headers


# ---------------------------------------------------------------------------
# Amendment (2026-07-11) — handle_patch_activity(edit_mode='1', return_to='stay')
# fixes the s14StripOpenDetail() no-op gap: PATCH /api/activities/{id} must
# honour return_to too, not just POST /customers/{id}/log-activity.
# ---------------------------------------------------------------------------

def test_patch_activity_edit_mode_return_to_stay_no_redirect():
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.patch_activity.return_value = MagicMock(
        activity_id="act-edit-1", party_id="party-cockpit-1",
    )

    handler = _get_patch_activity_handler(activity_log_mock)

    response = asyncio.run(handler(
        request=MagicMock(state=MagicMock(current_user=None)),
        activity_id="act-edit-1",
        contact_outcome="answered",
        outcome_reason=None,
        body=None,
        callback_at=None,
        related_order_code=None,
        occurred_at=None,
        channel_identity_id=None,
        zalo_connected=None,
        edit_mode="1",
        return_to="stay",
    ))

    assert response.status_code == 200
    assert "HX-Redirect" not in response.headers
    assert response.headers.get("HX-Trigger") == '{"activitySaved": true}'


def test_patch_activity_edit_mode_default_return_to_still_redirects():
    """Regression guard: edit_mode='1' with the default return_to='redirect'
    (every pre-existing caller) must keep the original HX-Redirect behaviour."""
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.patch_activity.return_value = MagicMock(
        activity_id="act-edit-2", party_id="party-cockpit-1",
    )

    handler = _get_patch_activity_handler(activity_log_mock)

    response = asyncio.run(handler(
        request=MagicMock(state=MagicMock(current_user=None)),
        activity_id="act-edit-2",
        contact_outcome="answered",
        outcome_reason=None,
        body=None,
        callback_at=None,
        related_order_code=None,
        occurred_at=None,
        channel_identity_id=None,
        zalo_connected=None,
        edit_mode="1",
        return_to="redirect",
    ))

    assert response.headers.get("HX-Redirect") == "/customers/party-cockpit-1?tab=timeline"
    assert "HX-Trigger" not in response.headers


def test_patch_activity_non_edit_mode_return_to_stay_still_204():
    """Draft autosave (edit_mode not '1') ignores return_to entirely — always
    204, regardless of what return_to carries."""
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.patch_activity.return_value = MagicMock(
        activity_id="act-draft-1", party_id="party-cockpit-1",
    )

    handler = _get_patch_activity_handler(activity_log_mock)

    response = asyncio.run(handler(
        request=MagicMock(state=MagicMock(current_user=None)),
        activity_id="act-draft-1",
        contact_outcome="answered",
        outcome_reason=None,
        body=None,
        callback_at=None,
        related_order_code=None,
        occurred_at=None,
        channel_identity_id=None,
        zalo_connected=None,
        edit_mode="",
        return_to="stay",
    ))

    assert response.status_code == 204

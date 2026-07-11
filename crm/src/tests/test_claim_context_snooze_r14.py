"""test_claim_context_snooze_r14.py — Phase 08 AI-7: fill test gaps for phases 04/05.

Covers behaviors that shipped without tests:
  (a) TaskService.claim_customer_actions denormalizes value_at_stake_vnd (SUM)
      and top_affinity_product (from the highest-value action).
  (b) PATCH /tasks/{id}/snooze — clamp days to [1, 30], doing→open transition.
  (c) GET /customers/{party_id}/call — queue_pos auto-correction to the
      party's real index in queue_ids.
  (d) POST /customers/{party_id}/r14-ack — writes script_id into custom_fields
      (AI-3), and the R14 banner template only unlocks on a successful POST
      (AI-4 — string-contains assertion; JS execution isn't unit-testable here).

All target modules (task_service.py, screen_worklist.py, screen_call_cockpit.py)
are read-only from this file's perspective — tests exercise current behavior,
they do not drive new code.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# ── sys.path setup (mirrors conftest.py / sibling test files) ────────────────
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # data-integration/
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # crm/src/
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI                                                  # noqa: E402
from fastapi.testclient import TestClient                                    # noqa: E402
from fastapi.templating import Jinja2Templates                               # noqa: E402

from application.task_service import TaskService                            # noqa: E402
from application.authorization_service import AuthorizationService          # noqa: E402
from domain.entities.cache_insight import ActionQueueItem                   # noqa: E402
from domain.entities.task import (                                          # noqa: E402
    Task, TASK_STATUS_OPEN, TASK_STATUS_DOING,
)

_TS = "2026-07-02T00:00:00.000Z"


# =============================================================================
# (a) claim_customer_actions — denormalize value_at_stake_vnd / top_affinity_product
# =============================================================================

def _action(action_id: str, value_at_stake_vnd: int, top_affinity_product: str,
            priority: int = 1) -> ActionQueueItem:
    return ActionQueueItem(
        action_id=action_id,
        customer_key="ckey-001",
        action_type="CALL_NOW",
        rationale_vi="test rationale",
        value_at_stake_vnd=value_at_stake_vnd,
        priority=priority,
        pending_since="2026-07-01",
        generated_date="2026-07-01",
        refreshed_at=_TS,
        top_affinity_product=top_affinity_product,
    )


class TestClaimCustomerActionsDenormalization:
    def _make_service(self):
        task_repo = MagicMock()
        task_repo.get_customer_claim.return_value = None
        cache_repo = MagicMock()
        svc = TaskService(
            task_repo, cache_repo,
            authz=AuthorizationService(), notes=MagicMock(),
            db=None,
        )
        return svc, task_repo

    def test_value_at_stake_is_sum_across_actions(self):
        svc, repo = self._make_service()
        actions = [
            _action("a1", 100_000, "Kem A"),
            _action("a2", 500_000, "Serum B"),
            _action("a3", 50_000, "Toner C"),
        ]
        task, is_new = svc.claim_customer_actions("party-1", actions, "user-1")
        assert is_new is True
        assert task.value_at_stake_vnd == 650_000
        repo.insert.assert_called_once()

    def test_top_affinity_product_from_highest_value_action(self):
        svc, _ = self._make_service()
        actions = [
            _action("a1", 100_000, "Kem A"),
            _action("a2", 500_000, "Serum B"),  # highest value_at_stake_vnd
            _action("a3", 50_000, "Toner C"),
        ]
        task, _ = svc.claim_customer_actions("party-1", actions, "user-1")
        assert task.top_affinity_product == "Serum B"

    def test_zero_sum_stores_none_not_zero(self):
        svc, _ = self._make_service()
        actions = [_action("a1", 0, "")]
        task, _ = svc.claim_customer_actions("party-1", actions, "user-1")
        assert task.value_at_stake_vnd is None

    def test_already_claimed_returns_existing_not_new(self):
        svc, repo = self._make_service()
        existing_task = Task(
            task_id="t-existing", party_id="party-1", title="x", priority=0,
            status=TASK_STATUS_OPEN, source="action_queue_claim",
            created_at=_TS, updated_at=_TS,
        )
        repo.get_customer_claim.return_value = existing_task
        task, is_new = svc.claim_customer_actions(
            "party-1", [_action("a1", 100_000, "Kem A")], "user-1",
        )
        assert is_new is False
        assert task is existing_task
        repo.insert.assert_not_called()


# =============================================================================
# (b) PATCH /tasks/{id}/snooze — clamp [1, 30], doing→open transition
# =============================================================================

def _make_task(task_id: str = "t-1", status: str = TASK_STATUS_OPEN) -> Task:
    return Task(
        task_id=task_id, party_id="party-1", title="Follow up", priority=0,
        status=status, source="manual", created_at=_TS, updated_at=_TS,
    )


def _build_worklist_app(task):
    from adapters.inbound.web.screen_worklist import make_worklist_router

    templates_mock = MagicMock(spec=Jinja2Templates)
    worklist_svc_mock = MagicMock()
    tasks_mock = MagicMock()
    tasks_mock.get_task.return_value = task
    task_writer_mock = MagicMock()

    app = FastAPI()
    app.include_router(
        make_worklist_router(templates_mock, worklist_svc_mock, tasks_mock, task_writer_mock)
    )
    client = TestClient(app, raise_server_exceptions=False)
    return client, task_writer_mock


class TestSnoozeEndpoint:
    def test_clamps_days_above_30(self):
        task = _make_task(status=TASK_STATUS_OPEN)
        client, writer = _build_worklist_app(task)
        r_high = client.patch(f"/tasks/{task.task_id}/snooze?days=999")
        assert r_high.status_code == 204
        due_high = writer.update_task.call_args[0][1]["due_at"]

        writer.reset_mock()
        r_30 = client.patch(f"/tasks/{task.task_id}/snooze?days=30")
        assert r_30.status_code == 204
        due_30 = writer.update_task.call_args[0][1]["due_at"]

        assert due_high == due_30, "days=999 must clamp to the same due_at as days=30"

    def test_clamps_days_below_1(self):
        task = _make_task(status=TASK_STATUS_OPEN)
        client, writer = _build_worklist_app(task)
        r_zero = client.patch(f"/tasks/{task.task_id}/snooze?days=0")
        assert r_zero.status_code == 204
        due_zero = writer.update_task.call_args[0][1]["due_at"]

        writer.reset_mock()
        r_neg = client.patch(f"/tasks/{task.task_id}/snooze?days=-5")
        assert r_neg.status_code == 204
        due_neg = writer.update_task.call_args[0][1]["due_at"]

        writer.reset_mock()
        r_one = client.patch(f"/tasks/{task.task_id}/snooze?days=1")
        assert r_one.status_code == 204
        due_one = writer.update_task.call_args[0][1]["due_at"]

        assert due_zero == due_one, "days=0 must clamp to the same due_at as days=1"
        assert due_neg == due_one, "days=-5 must clamp to the same due_at as days=1"

    def test_doing_task_transitions_to_open(self):
        task = _make_task(status=TASK_STATUS_DOING)
        client, writer = _build_worklist_app(task)
        r = client.patch(f"/tasks/{task.task_id}/snooze?days=3")
        assert r.status_code == 204
        writer.transition_status.assert_called_once_with(task.task_id, "open")

    def test_open_task_does_not_transition(self):
        task = _make_task(status=TASK_STATUS_OPEN)
        client, writer = _build_worklist_app(task)
        r = client.patch(f"/tasks/{task.task_id}/snooze?days=3")
        assert r.status_code == 204
        writer.transition_status.assert_not_called()


# =============================================================================
# (c) GET /customers/{party_id}/call — queue_pos auto-correction
# =============================================================================

_PARTY_ID = "party-queue-1"
_TEMPLATES_DIR = str(
    pathlib.Path(__file__).parents[1] / "adapters" / "inbound" / "web" / "templates"
)


def _make_templates() -> Jinja2Templates:
    import jinja2
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
        autoescape=True,
        auto_reload=False,
    )
    env.filters["fmt_vnd"] = lambda v: f"{v:,}₫" if v else "0₫"
    env.filters["truncate_str"] = lambda s, n=80: (s or "")[:n]
    env.filters["format_datetime_ict"] = lambda v: v or ""
    env.globals["today"] = lambda: "2026-07-02"
    return Jinja2Templates(env=env)


def _build_cockpit_app() -> TestClient:
    from fastapi import APIRouter
    from adapters.inbound.web.screens.customer360.screen_call_cockpit import (
        register_call_cockpit_route,
    )

    templates = _make_templates()
    app = FastAPI()
    router = APIRouter()

    party_mock = MagicMock()
    party_mock.display_name = "Nguyen Van A"
    party_mock.province = "Hồ Chí Minh"

    def _load_base(party_id):
        return party_mock, []

    def _load_insight(ids):
        return None

    def _sapo_customer_id(ids):
        return 1001

    notes_mock = MagicMock()
    notes_mock.list_notes.return_value = []
    party_tasks_mock = MagicMock()
    party_tasks_mock.list_by_party.return_value = []

    register_call_cockpit_route(
        router, templates,
        _load_base=_load_base, _load_insight=_load_insight,
        _sapo_customer_id=_sapo_customer_id,
        notes=notes_mock, party_tasks=party_tasks_mock,
        approach_repo=None, action_task_resolver=None,
    )
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestQueuePosAutoCorrection:
    def test_wrong_queue_pos_is_corrected_to_real_index(self):
        client = _build_cockpit_app()
        # party is at index 1 of the queue, but caller passes queue_pos=0
        r = client.get(
            f"/customers/{_PARTY_ID}/call"
            f"?queue_ids=p0,{_PARTY_ID},p2&queue_pos=0"
        )
        assert r.status_code == 200
        # Auto-corrected position → displayed as #2/3 (0-indexed 1 + 1)
        assert "#2/3" in r.text
        # Next-link must point at the item AFTER the corrected position (p2),
        # not after the caller-supplied (wrong) queue_pos=0.
        assert f"/customers/p2/call?queue_ids=p0,{_PARTY_ID},p2&queue_pos=2" in r.text

    def test_party_not_in_queue_keeps_caller_supplied_pos(self):
        client = _build_cockpit_app()
        r = client.get(
            f"/customers/{_PARTY_ID}/call?queue_ids=p0,p1,p2&queue_pos=1"
        )
        assert r.status_code == 200
        assert "#2/3" in r.text  # queue_pos untouched since party_id absent from list

    def test_no_queue_context_hides_counter(self):
        client = _build_cockpit_app()
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert "s14-queue-count" not in r.text


# =============================================================================
# (d) POST /customers/{party_id}/r14-ack — script_id written; template guard
# =============================================================================

def _register_activity_routes(activity_log_mock, task_svc=None, action_state=None):
    import adapters.inbound.web.screens.customer360.screen_customer_360_activity as mod

    authz_mock = MagicMock(spec=AuthorizationService)
    authz_mock.is_same_party.return_value = True
    router_mock = MagicMock()
    templates_mock = MagicMock()
    mod.register_activity_routes(
        router_mock, templates_mock,
        profile=MagicMock(), identities=MagicMock(), notes=MagicMock(),
        activity_log=activity_log_mock, authz=authz_mock, task_svc=task_svc,
        app_users=None, action_state=action_state,
    )
    post_calls = router_mock.post.return_value.call_args_list
    # Registration order: log-activity, reason/resolve-async, r14-ack.
    assert len(post_calls) >= 3, "Expected 3 POST handlers registered"
    return post_calls[2].args[0]


class TestR14AckScriptId:
    def test_script_id_written_to_custom_fields(self):
        captured: dict = {}

        activity_log_mock = MagicMock()

        def capture(data):
            captured.update(data)
            return MagicMock(activity_id="act-r14")

        activity_log_mock.log_activity.side_effect = capture
        handler = _register_activity_routes(activity_log_mock)

        request_mock = MagicMock()
        request_mock.state.current_user = None
        request_mock.form = AsyncMock(return_value={
            "reason_shown": "margin âm bất thường",
            "script_id": "2026-07-01T00:00:00Z",
        })

        asyncio.run(handler(request=request_mock, party_id="party-r14"))

        cf = captured.get("custom_fields")
        assert cf is not None
        assert cf.get("r14_ack") is True
        assert cf.get("script_id") == "2026-07-01T00:00:00Z"
        assert cf.get("reason_shown") == "margin âm bất thường"

    def test_missing_script_id_writes_empty_string_not_error(self):
        captured: dict = {}
        activity_log_mock = MagicMock()

        def capture(data):
            captured.update(data)
            return MagicMock(activity_id="act-r14b")

        activity_log_mock.log_activity.side_effect = capture
        handler = _register_activity_routes(activity_log_mock)

        request_mock = MagicMock()
        request_mock.state.current_user = None
        request_mock.form = AsyncMock(return_value={"reason_shown": "x"})

        asyncio.run(handler(request=request_mock, party_id="party-r14"))

        cf = captured.get("custom_fields")
        assert cf.get("script_id") == ""


class TestR14UnlockGuardedOnSuccess:
    """AI-4: JS execution can't run in pytest — assert the fixed guard string
    is present in the template source instead of executing the browser JS."""

    def test_template_only_unlocks_on_successful_request(self):
        tpl_path = (
            pathlib.Path(__file__).parents[1] / "adapters" / "inbound" / "web"
            / "templates" / "fragments" / "c360_call_cockpit_panel.html"
        )
        html = tpl_path.read_text(encoding="utf-8")
        assert "event.detail.successful" in html
        assert "s14UnlockR14()" in html
        assert "s14R14AckError" in html

    def test_script_id_hidden_input_forwarded_via_hx_include(self):
        tpl_path = (
            pathlib.Path(__file__).parents[1] / "adapters" / "inbound" / "web"
            / "templates" / "fragments" / "c360_call_cockpit_panel.html"
        )
        html = tpl_path.read_text(encoding="utf-8")
        assert 'name="script_id"' in html
        assert "s14-r14-script-id-val" in html
        assert "#s14-r14-script-id-val" in html

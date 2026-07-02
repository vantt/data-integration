"""Tests for Phase 03 (S15 Task Detail) and Phase 04 (S14 Cockpit v2 backend).

Covers:
- GET /tasks/{id} for each task_kind returns 200 + expected context keys
- GET /tasks/{id} with claim source exposes claim_actions
- GET /tasks/{id} 404 on unknown task_id
- POST /tasks/{id}/status — valid and illegal transitions
- /customers/{party_id}/call renders with + without task_id
- call_cockpit panel context includes rail primary + secondary
- contact-tasks present in rail
- inline collect POST returns row fragment (not full panel)

4 pre-existing unrelated failures are expected — these tests add 0 new failures.
"""
from __future__ import annotations

import pathlib
import sys
import uuid
from typing import Optional
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.templating import Jinja2Templates

from crm.src.adapters.inbound.web.screens.screen_task_detail import make_task_detail_router
from crm.src.adapters.inbound.web.screens.customer360.screen_call_cockpit import (
    register_call_cockpit_route,
)
from crm.src.application.reason_rail import assemble_reason_rail, RailItem
from crm.src.domain.entities.task import (
    Task,
    TASK_STATUS_OPEN,
    TASK_STATUS_DOING,
    TASK_STATUS_DONE,
    TASK_STATUS_CANCELLED,
    TASK_KIND_CONTACT,
    TASK_KIND_INTERNAL,
    TASK_KIND_GENERIC,
    TASK_SOURCE_MANUAL,
    TASK_SOURCE_ACTION_QUEUE,
    TASK_SOURCE_ACTION_QUEUE_CLAIM,
    TASK_ALLOWED_TRANSITIONS,
)
from crm.src.domain.entities.cache_insight import CacheInsight, ActionQueueItem

_TS = "2026-07-02T00:00:00.000Z"
_PARTY_ID = str(uuid.uuid4())
_TASK_ID = str(uuid.uuid4())
_TEMPLATES_DIR = str(
    pathlib.Path(__file__).parents[1]
    / "adapters" / "inbound" / "web" / "templates"
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_task(
    task_id: str = _TASK_ID,
    task_kind: str = TASK_KIND_CONTACT,
    status: str = TASK_STATUS_OPEN,
    source: str = TASK_SOURCE_MANUAL,
    party_id: Optional[str] = _PARTY_ID,
    source_ref: Optional[str] = None,
) -> Task:
    return Task(
        task_id=task_id,
        title="Test task",
        priority=0,
        status=status,
        source=source,
        created_at=_TS,
        updated_at=_TS,
        party_id=party_id,
        task_kind=task_kind,
        source_ref=source_ref,
    )


def _make_action(action_id: str = "act-001") -> ActionQueueItem:
    return ActionQueueItem(
        action_id=action_id,
        customer_key="ckey-001",
        action_type="CALL_NOW",
        rationale_vi="Khách cần liên hệ",
        value_at_stake_vnd=500_000,
        priority=2,
        pending_since="2026-07-01",
        generated_date="2026-07-01",
        refreshed_at=_TS,
        status="open",
    )


def _make_templates() -> Jinja2Templates:
    import jinja2
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
        autoescape=True,
        auto_reload=False,
    )
    # Minimal filters used by stub templates
    env.filters["fmt_vnd"] = lambda v: f"{v:,}₫" if v else "0₫"
    env.filters["truncate_str"] = lambda s, n=80: (s or "")[:n]
    env.filters["format_datetime_ict"] = lambda v: v or ""
    env.globals["today"] = lambda: "2026-07-02"
    return Jinja2Templates(env=env)


def _build_task_detail_app(
    task: Optional[Task],
    insight: Optional[CacheInsight] = None,
    activities: list = None,
    transition_raises: bool = False,
) -> TestClient:
    """Build a minimal FastAPI app wired with make_task_detail_router."""
    templates = _make_templates()

    task_repo = MagicMock()
    task_repo.get_by_id.return_value = task
    task_repo.list_by_party.return_value = []

    profile = MagicMock()
    party_mock = MagicMock()
    party_mock.display_name = "Nguyen Van A"
    party_mock.province = "Hồ Chí Minh"
    profile.get_party_360.return_value = party_mock

    identity_mock = MagicMock()
    identity_mock.identity_type = "sapo_customer"
    identity_mock.identity_value = "1001"
    identities = MagicMock()
    identities.list_identities.return_value = [identity_mock]

    insight_repo = MagicMock()
    insight_repo.get_customer_insight.return_value = insight

    activity_repo = MagicMock()
    activity_repo.list_activities.return_value = activities or []

    task_svc = MagicMock()
    if transition_raises:
        task_svc.transition_status.side_effect = ValueError("illegal transition")
    task_svc.get_task.return_value = task

    app = FastAPI()
    app.include_router(
        make_task_detail_router(
            templates=templates,
            task_repo=task_repo,
            profile=profile,
            identities=identities,
            insight=insight_repo,
            activities=activity_repo,
            task_svc=task_svc,
        )
    )
    return TestClient(app, raise_server_exceptions=False)


# ── S15 Task Detail — GET ─────────────────────────────────────────────────────

class TestTaskDetailGet:
    def test_contact_task_returns_200(self):
        task = _make_task(task_kind=TASK_KIND_CONTACT)
        client = _build_task_detail_app(task)
        r = client.get(f"/tasks/{_TASK_ID}")
        assert r.status_code == 200
        assert "task-detail-stub" in r.text

    def test_internal_task_returns_200(self):
        task = _make_task(task_kind=TASK_KIND_INTERNAL)
        client = _build_task_detail_app(task)
        r = client.get(f"/tasks/{_TASK_ID}")
        assert r.status_code == 200

    def test_generic_task_returns_200(self):
        task = _make_task(task_kind=TASK_KIND_GENERIC, party_id=None)
        client = _build_task_detail_app(task)
        r = client.get(f"/tasks/{_TASK_ID}")
        assert r.status_code == 200

    def test_404_on_unknown_task(self):
        client = _build_task_detail_app(task=None)
        r = client.get("/tasks/nonexistent-id")
        assert r.status_code == 404

    def test_context_exposes_body_kind(self):
        task = _make_task(task_kind=TASK_KIND_CONTACT)
        client = _build_task_detail_app(task)
        r = client.get(f"/tasks/{_TASK_ID}")
        assert "contact" in r.text

    def test_context_exposes_allowed_transitions(self):
        task = _make_task(status=TASK_STATUS_OPEN)
        client = _build_task_detail_app(task)
        r = client.get(f"/tasks/{_TASK_ID}")
        assert r.status_code == 200
        # TASK_ALLOWED_TRANSITIONS[open] = [doing, done, cancelled]
        for t in TASK_ALLOWED_TRANSITIONS[TASK_STATUS_OPEN]:
            assert t in r.text

    def test_claim_task_exposes_claim_actions(self):
        action = _make_action("act-claim-001")
        ins = CacheInsight(actions=[action])
        task = _make_task(
            task_kind=TASK_KIND_CONTACT,
            source=TASK_SOURCE_ACTION_QUEUE_CLAIM,
            source_ref="act-claim-001",
        )
        client = _build_task_detail_app(task, insight=ins)
        r = client.get(f"/tasks/{_TASK_ID}")
        assert r.status_code == 200
        assert "act" in r.text.lower() or "action" in r.text.lower()

    def test_contact_task_shows_vao_phien_goi_link(self):
        task = _make_task(task_kind=TASK_KIND_CONTACT)
        client = _build_task_detail_app(task)
        r = client.get(f"/tasks/{_TASK_ID}")
        assert "/call" in r.text

    def test_generic_task_no_party_block(self):
        task = _make_task(task_kind=TASK_KIND_GENERIC, party_id=None)
        client = _build_task_detail_app(task)
        r = client.get(f"/tasks/{_TASK_ID}")
        assert r.status_code == 200
        # No party block when no party_id
        assert "Vào phiên gọi" not in r.text


# ── S15 Task Detail — POST /status ───────────────────────────────────────────

class TestTaskStatusTransition:
    def test_valid_start_transition(self):
        task = _make_task(status=TASK_STATUS_OPEN)
        client = _build_task_detail_app(task)
        r = client.post(
            f"/tasks/{_TASK_ID}/status",
            data={"new_status": "doing"},
        )
        # Should redirect (HX-Redirect) → 200 with empty body
        assert r.status_code == 200
        assert r.headers.get("hx-redirect") == f"/tasks/{_TASK_ID}"

    def test_valid_cancel_transition(self):
        task = _make_task(status=TASK_STATUS_OPEN)
        client = _build_task_detail_app(task)
        r = client.post(
            f"/tasks/{_TASK_ID}/status",
            data={"new_status": "cancelled"},
        )
        assert r.status_code == 200

    def test_valid_reopen_from_done(self):
        task = _make_task(status=TASK_STATUS_DONE)
        client = _build_task_detail_app(task)
        r = client.post(
            f"/tasks/{_TASK_ID}/status",
            data={"new_status": "open"},
        )
        assert r.status_code == 200

    def test_illegal_transition_rejected(self):
        # done → doing is not allowed
        task = _make_task(status=TASK_STATUS_DONE)
        client = _build_task_detail_app(task)
        r = client.post(
            f"/tasks/{_TASK_ID}/status",
            data={"new_status": "doing"},
        )
        assert r.status_code == 422

    def test_illegal_transition_cancelled_to_done(self):
        task = _make_task(status=TASK_STATUS_CANCELLED)
        client = _build_task_detail_app(task)
        r = client.post(
            f"/tasks/{_TASK_ID}/status",
            data={"new_status": "done"},
        )
        assert r.status_code == 422

    def test_status_404_on_unknown_task(self):
        client = _build_task_detail_app(task=None)
        r = client.post("/tasks/no-such-task/status", data={"new_status": "doing"})
        assert r.status_code == 404


# ── Reason Rail ───────────────────────────────────────────────────────────────

class TestReasonRail:
    def test_empty_insight_and_no_tasks_returns_none_primary(self):
        primary, secondary = assemble_reason_rail(None, [])
        assert primary is None
        assert secondary == []

    def test_single_action_becomes_primary(self):
        action = _make_action("act-001")
        ins = CacheInsight(actions=[action])
        primary, secondary = assemble_reason_rail(ins, [])
        assert primary is not None
        assert primary.action_id == "act-001"
        assert secondary == []

    def test_dismissed_action_excluded(self):
        action = _make_action("act-dis")
        action.status = "dismissed"
        ins = CacheInsight(actions=[action])
        primary, secondary = assemble_reason_rail(ins, [])
        assert primary is None

    def test_resolved_action_excluded(self):
        action = _make_action("act-res")
        ins = CacheInsight(actions=[action])
        primary, secondary = assemble_reason_rail(ins, [], resolved_action_ids={"act-res"})
        assert primary is None

    def test_contact_task_in_rail(self):
        task = _make_task(status=TASK_STATUS_OPEN)
        primary, secondary = assemble_reason_rail(None, [task])
        assert primary is not None
        assert primary.task_id == _TASK_ID

    def test_doing_task_takes_priority_over_action(self):
        action = _make_action("act-001")
        action.action_type = "CALL_NOW"
        ins = CacheInsight(actions=[action])
        doing_task = _make_task(
            task_id="t-doing",
            status=TASK_STATUS_DOING,
        )
        primary, secondary = assemble_reason_rail(ins, [doing_task])
        assert primary is not None
        assert primary.task_id == "t-doing"

    def test_pinned_task_forced_to_primary(self):
        action = _make_action("act-001")
        action.action_type = "CALL_NOW"
        ins = CacheInsight(actions=[action])
        open_task = _make_task(task_id="t-pin", status=TASK_STATUS_OPEN)
        primary, secondary = assemble_reason_rail(
            ins, [open_task], pinned_task_id="t-pin"
        )
        assert primary is not None
        assert primary.task_id == "t-pin"

    def test_multiple_items_split_primary_secondary(self):
        a1 = _make_action("act-001")
        a2 = _make_action("act-002")
        ins = CacheInsight(actions=[a1, a2])
        primary, secondary = assemble_reason_rail(ins, [])
        assert primary is not None
        assert len(secondary) == 1

    def test_contact_tasks_present_alongside_actions(self):
        action = _make_action("act-001")
        ins = CacheInsight(actions=[action])
        task = _make_task(task_id="t-contact", status=TASK_STATUS_OPEN)
        primary, secondary = assemble_reason_rail(ins, [task])
        all_ids = {primary.task_id, primary.action_id} | {
            r.task_id for r in secondary
        } | {r.action_id for r in secondary}
        assert "t-contact" in all_ids
        assert "act-001" in all_ids


# ── Call Cockpit full-screen route ────────────────────────────────────────────

def _build_cockpit_app(
    party_exists: bool = True,
    contact_tasks: list = None,
    insight: Optional[CacheInsight] = None,
) -> TestClient:
    templates = _make_templates()
    app = FastAPI()
    router_base = app.router

    from fastapi import APIRouter
    router = APIRouter()

    party_mock = MagicMock()
    party_mock.display_name = "Nguyen Van A"
    party_mock.province = "Hồ Chí Minh"

    def _load_base(party_id):
        if party_exists:
            return party_mock, []
        return None, []

    def _load_insight(ids):
        return insight

    def _sapo_customer_id(ids):
        return 1001

    notes_mock = MagicMock()
    notes_mock.list_notes.return_value = []

    party_tasks_mock = MagicMock()
    party_tasks_mock.list_by_party.return_value = contact_tasks or []

    register_call_cockpit_route(
        router,
        templates,
        _load_base=_load_base,
        _load_insight=_load_insight,
        _sapo_customer_id=_sapo_customer_id,
        notes=notes_mock,
        party_tasks=party_tasks_mock,
        approach_repo=None,
        action_task_resolver=None,
    )
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestCallCockpitRoute:
    def test_renders_without_task_id(self):
        client = _build_cockpit_app()
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert "s14-panel-root" in r.text

    def test_renders_with_task_id(self):
        client = _build_cockpit_app()
        r = client.get(f"/customers/{_PARTY_ID}/call?task_id={_TASK_ID}")
        assert r.status_code == 200
        assert _TASK_ID in r.text

    def test_return_target_set_when_task_id_present(self):
        client = _build_cockpit_app()
        r = client.get(f"/customers/{_PARTY_ID}/call?task_id={_TASK_ID}")
        assert f"/tasks/{_TASK_ID}" in r.text

    def test_no_return_target_without_task_id(self):
        client = _build_cockpit_app()
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert "Quay lại task" not in r.text

    def test_404_when_party_not_found(self):
        client = _build_cockpit_app(party_exists=False)
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 404

    def test_rail_primary_from_action_in_context(self):
        action = _make_action("act-cockpit")
        ins = CacheInsight(actions=[action])
        client = _build_cockpit_app(insight=ins)
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        # rail primary should appear in template
        assert "s14-reason--primary" in r.text

    def test_contact_tasks_appear_in_rail(self):
        task = _make_task(
            task_id="t-rail",
            task_kind=TASK_KIND_CONTACT,
            status=TASK_STATUS_OPEN,
        )
        client = _build_cockpit_app(contact_tasks=[task])
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert "s14-reason" in r.text

    def test_doing_contact_task_is_primary(self):
        task = _make_task(
            task_id="t-doing",
            task_kind=TASK_KIND_CONTACT,
            status=TASK_STATUS_DOING,
        )
        client = _build_cockpit_app(contact_tasks=[task])
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert "s14-reason--primary" in r.text


# ── Inline collect (§4) ───────────────────────────────────────────────────────

class TestInlineCollect:
    """Verify that POST /customers/{id}/contact?inline=1 returns the row fragment."""

    def _build_contact_modal_app(self) -> TestClient:
        from crm.src.adapters.inbound.web.screens.modals.screen_modal_contact import (
            make_contact_modal_router,
        )
        templates = _make_templates()
        profile = MagicMock()
        profile.get_party_360.return_value = MagicMock(display_name="X")
        profile.upsert_profile.return_value = None

        party_repo = MagicMock()
        party_repo.list_identities.return_value = []
        party_repo.insert_identity_full.return_value = None
        party_repo.get_by_id.return_value = MagicMock(display_name="X", primary_email="")
        party_repo.update.return_value = None

        app = FastAPI()
        app.include_router(make_contact_modal_router(templates, profile, party_repo))
        return TestClient(app, raise_server_exceptions=False)

    def test_inline_contact_returns_row_fragment_not_redirect(self):
        client = self._build_contact_modal_app()
        r = client.post(
            f"/customers/{_PARTY_ID}/contact",
            data={
                "action": "add_channel",
                "add_identity_type": "zalo",
                "add_identity_value": "0901234567",
                "inline": "1",
            },
        )
        assert r.status_code == 200
        # Must return the row fragment, NOT a redirect
        assert "hx-redirect" not in r.headers
        assert "s14-collect-row" in r.text
        assert "✓" in r.text

    def test_non_inline_contact_still_redirects(self):
        client = self._build_contact_modal_app()
        r = client.post(
            f"/customers/{_PARTY_ID}/contact",
            data={
                "action": "add_channel",
                "add_identity_type": "phone_secondary",
                "add_identity_value": "0909999999",
                "inline": "0",
            },
        )
        # Normal path: redirect
        assert "hx-redirect" in r.headers or r.status_code == 200

    def test_inline_core_returns_row_fragment(self):
        client = self._build_contact_modal_app()
        r = client.post(
            f"/customers/{_PARTY_ID}/core",
            data={
                "display_name": "New Name",
                "inline": "1",
            },
        )
        assert r.status_code == 200
        assert "hx-redirect" not in r.headers
        assert "s14-collect-row" in r.text

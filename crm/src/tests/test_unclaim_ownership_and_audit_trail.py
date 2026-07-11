"""test_unclaim_ownership_and_audit_trail.py — plan 260711-1227 phase-02.

Covers TaskService.unclaim_customer_actions' ownership guard + audit-note
write, and both route handlers (worklist S01 + C360) that wrap it:

  (a) Non-assignee unclaim -> "forbidden" / 403, claim state unchanged.
  (b) Unauthenticated unclaim (actor_id/uid empty) -> "forbidden" / 401 —
      dedicated test, NOT folded into (a): this is the specific case the
      original design's fail-open guard (`if actor_id and not is_owner(...)`)
      missed. The guard must be `if not actor_id or not is_owner(...)`.
  (c) Valid unclaim -> "ok", crm_note row actually persisted (queried via the
      DB connection, not just an HTTP-status assertion) with correct
      party_id/author_user_id/note_type.
  (d) Missing/invalid reason -> 422 at the route layer (service layer itself
      still unclaims on an invalid reason, it just skips the audit note —
      the 422 rejection is a route-layer input-validation concern).
  (e) Both route handlers share the same TaskService logic — no duplicated
      authorization code.
"""
from __future__ import annotations

import pathlib
import sys

import pytest
from starlette.middleware.base import BaseHTTPMiddleware

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from unittest.mock import MagicMock  # noqa: E402

from fastapi import APIRouter, FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from fastapi.templating import Jinja2Templates  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from application.authorization_service import AuthorizationService  # noqa: E402
from application.note_service import NoteService  # noqa: E402
from application.task_service import TaskService  # noqa: E402
from adapters.outbound.sqlite.task_repository import SQLiteTaskRepository  # noqa: E402
from adapters.outbound.sqlite.tag_note_repository import SQLiteNoteRepository  # noqa: E402
from domain.entities.task import TASK_STATUS_CANCELLED, TASK_STATUS_OPEN  # noqa: E402


# ── Shared DB seeding helpers ─────────────────────────────────────────────────

def _insert_party(db, party_id: str) -> None:
    db.conn.execute(
        "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
        (party_id, "Test Party"),
    )
    db.conn.commit()


def _insert_app_user(db, user_id: str) -> None:
    db.conn.execute(
        "INSERT INTO crm_app_user (user_id, email, full_name) VALUES (?, ?, ?)",
        (user_id, f"{user_id}@test.vn", "Test User"),
    )
    db.conn.commit()


def _make_real_service(db) -> tuple[TaskService, SQLiteTaskRepository]:
    """A real TaskService (SQLite-backed) — needed because this phase's bugs
    (fail-open guard, wrong-port note write) only surface with real repos."""
    task_repo = SQLiteTaskRepository(db)
    note_svc = NoteService(SQLiteNoteRepository(db), db)
    svc = TaskService(
        task_repo, MagicMock(),
        authz=AuthorizationService(), notes=note_svc,
        db=db,
    )
    return svc, task_repo


def _seed_claim(svc: TaskService, db, party_id: str, assignee_id: str):
    """Insert party + assignee, then claim via the service (mirrors real usage)."""
    _insert_party(db, party_id)
    _insert_app_user(db, assignee_id)
    action = MagicMock()
    action.action_type = "call_now"
    action.rationale_vi = "Gọi ngay"
    action.priority = 1
    action.customer_name = "Test Party"
    action.party_id = party_id
    action.value_at_stake_vnd = 0
    action.top_affinity_product = ""
    task, is_new = svc.claim_customer_actions(party_id, [action], assignee_id)
    assert is_new is True
    return task


def _note_rows(db, party_id: str) -> list[dict]:
    cur = db.conn.execute(
        "SELECT party_id, author_user_id, note_type, body, visibility "
        "FROM crm_note WHERE party_id = ? AND deleted_at IS NULL",
        (party_id,),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


# =============================================================================
# TaskService.unclaim_customer_actions — direct unit coverage
# =============================================================================

class TestUnclaimOwnershipGuard:
    def test_not_found_when_no_claim_exists(self, seeded_crm_db):
        svc, _ = _make_real_service(seeded_crm_db)
        result = svc.unclaim_customer_actions("no-such-party", actor_id="user-1", reason="other")
        assert result == "not_found"

    def test_forbidden_when_actor_is_not_the_assignee(self, seeded_crm_db):
        """(a) Two different non-empty actor_ids — the rightful assignee vs.
        a different staff member — must reject the mismatched one."""
        svc, task_repo = _make_real_service(seeded_crm_db)
        party_id = "party-forbidden-1"
        task = _seed_claim(svc, seeded_crm_db, party_id, assignee_id="user-owner")
        _insert_app_user(seeded_crm_db, "user-other")

        result = svc.unclaim_customer_actions(party_id, actor_id="user-other", reason="other")

        assert result == "forbidden"
        reloaded = task_repo.get_by_id(task.task_id)
        assert reloaded.status == TASK_STATUS_OPEN, "claim state must be unchanged on 403"
        assert _note_rows(seeded_crm_db, party_id) == [], "no audit note on a rejected unclaim"

    def test_forbidden_when_actor_id_is_empty(self, seeded_crm_db):
        """(b) THE fail-open regression case: an unauthenticated caller (empty
        actor_id) must hit the SAME "forbidden" branch as a genuine ownership
        mismatch — there is no separate "skip the check" path. This is
        deliberately a distinct test from the non-assignee case above (that
        one uses two non-empty actor_ids; this one is empty/None)."""
        svc, task_repo = _make_real_service(seeded_crm_db)
        party_id = "party-forbidden-2"
        task = _seed_claim(svc, seeded_crm_db, party_id, assignee_id="user-owner")

        result_empty = svc.unclaim_customer_actions(party_id, actor_id="", reason="other")
        result_none = svc.unclaim_customer_actions(party_id, actor_id=None, reason="other")

        assert result_empty == "forbidden"
        assert result_none == "forbidden"
        reloaded = task_repo.get_by_id(task.task_id)
        assert reloaded.status == TASK_STATUS_OPEN
        assert _note_rows(seeded_crm_db, party_id) == []

    def test_ok_persists_audit_note_with_correct_fields(self, seeded_crm_db):
        """(c) query crm_note directly — this is exactly the case where the
        original design's raw-NoteRepository call would have raised TypeError
        (silently swallowed), leaving no note despite a 200/"ok" response."""
        svc, task_repo = _make_real_service(seeded_crm_db)
        party_id = "party-ok-1"
        task = _seed_claim(svc, seeded_crm_db, party_id, assignee_id="user-owner")

        result = svc.unclaim_customer_actions(party_id, actor_id="user-owner", reason="wrong_region")

        assert result == "ok"
        reloaded = task_repo.get_by_id(task.task_id)
        assert reloaded.status == TASK_STATUS_CANCELLED

        notes = _note_rows(seeded_crm_db, party_id)
        assert len(notes) == 1
        assert notes[0]["party_id"] == party_id
        assert notes[0]["author_user_id"] == "user-owner"
        assert notes[0]["note_type"] == "unclaim_reason"
        assert notes[0]["visibility"] == "team"
        assert "Sai khu vực" in notes[0]["body"]

    def test_ok_with_invalid_reason_still_unclaims_but_writes_no_note(self, seeded_crm_db):
        """Service layer does not reject an unrecognized reason outright (the
        422 rejection lives at the route layer) — it just skips the note."""
        svc, task_repo = _make_real_service(seeded_crm_db)
        party_id = "party-ok-2"
        task = _seed_claim(svc, seeded_crm_db, party_id, assignee_id="user-owner")

        result = svc.unclaim_customer_actions(party_id, actor_id="user-owner", reason="not-a-real-reason")

        assert result == "ok"
        reloaded = task_repo.get_by_id(task.task_id)
        assert reloaded.status == TASK_STATUS_CANCELLED
        assert _note_rows(seeded_crm_db, party_id) == []


# =============================================================================
# Route layer — worklist (S01) PATCH /worklist/customers/{party_id}/unclaim
# =============================================================================

class _FakeUser:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id


class _InjectUserMiddleware(BaseHTTPMiddleware):
    """Test-only stand-in for CFAccessMiddleware: sets request.state.current_user
    from an X-Test-User header so route handlers' _current_user_id(request) /
    getattr(request.state, "current_user", None) patterns behave realistically."""

    async def dispatch(self, request, call_next):
        uid = request.headers.get("X-Test-User")
        request.state.current_user = _FakeUser(uid) if uid else None
        return await call_next(request)


def _build_worklist_app(task_claim):
    from adapters.inbound.web.screen_worklist import make_worklist_router

    templates_mock = MagicMock(spec=Jinja2Templates)
    templates_mock.TemplateResponse.return_value = HTMLResponse("rendered")
    worklist_svc_mock = MagicMock()
    worklist_svc_mock.list_all_action_queue.return_value = []
    tasks_mock = MagicMock()
    tasks_mock.list_tasks.return_value = []
    tasks_mock.list_unassigned.return_value = []
    task_writer_mock = MagicMock()

    app = FastAPI()
    app.add_middleware(_InjectUserMiddleware)
    app.include_router(make_worklist_router(
        templates_mock, worklist_svc_mock, tasks_mock, task_writer_mock,
        task_claim=task_claim,
    ))
    return TestClient(app, raise_server_exceptions=False)


class TestWorklistUnclaimRoute:
    def test_unauthenticated_returns_401(self):
        task_claim = MagicMock()
        client = _build_worklist_app(task_claim)

        r = client.patch(
            "/worklist/customers/party-1/unclaim", data={"reason": "wrong_region"}
        )

        assert r.status_code == 401
        task_claim.unclaim_customer_actions.assert_not_called()

    def test_missing_reason_returns_422(self):
        task_claim = MagicMock()
        client = _build_worklist_app(task_claim)

        r = client.patch(
            "/worklist/customers/party-1/unclaim",
            headers={"X-Test-User": "user-1"},
        )

        assert r.status_code == 422
        task_claim.unclaim_customer_actions.assert_not_called()

    def test_invalid_reason_returns_422(self):
        task_claim = MagicMock()
        client = _build_worklist_app(task_claim)

        r = client.patch(
            "/worklist/customers/party-1/unclaim",
            data={"reason": "not-a-real-reason"},
            headers={"X-Test-User": "user-1"},
        )

        assert r.status_code == 422
        task_claim.unclaim_customer_actions.assert_not_called()

    def test_forbidden_result_returns_403(self):
        task_claim = MagicMock()
        task_claim.unclaim_customer_actions.return_value = "forbidden"
        client = _build_worklist_app(task_claim)

        r = client.patch(
            "/worklist/customers/party-1/unclaim",
            data={"reason": "wrong_region"},
            headers={"X-Test-User": "user-other"},
        )

        assert r.status_code == 403
        task_claim.unclaim_customer_actions.assert_called_once_with(
            "party-1", actor_id="user-other", reason="wrong_region",
        )

    def test_ok_result_renders_fragment_and_invalidates_cache(self):
        task_claim = MagicMock()
        task_claim.unclaim_customer_actions.return_value = "ok"
        client = _build_worklist_app(task_claim)

        r = client.patch(
            "/worklist/customers/party-1/unclaim",
            data={"reason": "wrong_region"},
            headers={"X-Test-User": "user-owner"},
        )

        assert r.status_code == 200
        task_claim.unclaim_customer_actions.assert_called_once_with(
            "party-1", actor_id="user-owner", reason="wrong_region",
        )


# =============================================================================
# Route layer — C360 PATCH /customers/{party_id}/unclaim
# =============================================================================

def _build_c360_unclaim_app(task_svc):
    from adapters.inbound.web.screens.customer360.screen_customer_360_panels import (
        register_panel_routes,
    )

    templates_mock = MagicMock(spec=Jinja2Templates)
    templates_mock.TemplateResponse.return_value = HTMLResponse("rendered")

    router = APIRouter()
    register_panel_routes(
        router, templates_mock,
        activities=MagicMock(), notes=MagicMock(), party_tasks=MagicMock(),
        task_svc=task_svc,
        _load_base=lambda party_id: (MagicMock(), MagicMock()),
        _load_insight=lambda ids: None,
        _sapo_customer_id=lambda ids: None,
    )
    app = FastAPI()
    app.add_middleware(_InjectUserMiddleware)
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestC360UnclaimRoute:
    """Same ownership/reason rules as the worklist route — logic lives once
    in TaskService, this route only maps its result to HTTP status."""

    def test_unauthenticated_returns_401(self):
        task_svc = MagicMock()
        client = _build_c360_unclaim_app(task_svc)

        r = client.patch("/customers/party-1/unclaim", data={"reason": "wrong_region"})

        assert r.status_code == 401
        task_svc.unclaim_customer_actions.assert_not_called()

    def test_invalid_reason_returns_422(self):
        task_svc = MagicMock()
        client = _build_c360_unclaim_app(task_svc)

        r = client.patch(
            "/customers/party-1/unclaim",
            data={"reason": "bogus"},
            headers={"X-Test-User": "user-1"},
        )

        assert r.status_code == 422
        task_svc.unclaim_customer_actions.assert_not_called()

    def test_forbidden_result_returns_403(self):
        task_svc = MagicMock()
        task_svc.unclaim_customer_actions.return_value = "forbidden"
        client = _build_c360_unclaim_app(task_svc)

        r = client.patch(
            "/customers/party-1/unclaim",
            data={"reason": "wrong_region"},
            headers={"X-Test-User": "user-other"},
        )

        assert r.status_code == 403

    def test_ok_result_renders_panel(self):
        task_svc = MagicMock()
        task_svc.unclaim_customer_actions.return_value = "ok"
        client = _build_c360_unclaim_app(task_svc)

        r = client.patch(
            "/customers/party-1/unclaim",
            data={"reason": "wrong_region"},
            headers={"X-Test-User": "user-owner"},
        )

        assert r.status_code == 200
        task_svc.unclaim_customer_actions.assert_called_once_with(
            "party-1", actor_id="user-owner", reason="wrong_region",
        )

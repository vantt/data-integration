"""test_disposition_strip_v2.py — phase-03 (activity-log disposition API, P2):
Disposition Strip v2 (outcome_bar -> disposition_strip, T0-T3 state machine).

Covers what is feasible as Python/pytest route + contract tests (this repo has
no JS unit-test harness — confirmed by inspection of crm/src/tests/):
  - ActivityService.find_open_draft() thin wrapper (new in this phase).
  - build_draft_activity_ctx() shaping (screen_call_cockpit.py, new in this
    phase) — None when no activity_log/current_user/open draft; correct dict
    shape when an open draft exists.
  - Full-screen /customers/{id}/call renders the new disposition strip
    (#s14-strip) with the right initial `data-phase` for T0 (no draft),
    T1 (draft, no contact_outcome) and T2 (draft, contact_outcome set) —
    i.e. mid-call reload recovery never forces T0 again.
  - Old outcome_bar markup/JS (s14-outcome, s14-oc, s14OpenOutcome,
    s14QuickOutcomeVals, s14StartCallSession) is fully gone from the template;
    new disposition-strip identifiers are present — a lightweight automated
    stand-in for "spec/template parity" review.

Anything requiring live browser interaction (keyboard shortcuts firing,
sheet-up visual sizing, timer ticking, PATCH/finalize fetch() round-trips) is
NOT claimed here — see the manual test script in the phase-03 implementation
report instead.
"""
from __future__ import annotations

import pathlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from fastapi.templating import Jinja2Templates  # noqa: E402

from application.activity_service import ActivityService  # noqa: E402
from adapters.outbound.sqlite.activity_repository import SQLiteActivityRepository  # noqa: E402
from adapters.inbound.web.screens.customer360.screen_call_cockpit import (  # noqa: E402
    register_call_cockpit_route,
    build_draft_activity_ctx,
)

_TEMPLATES_DIR = str(
    pathlib.Path(__file__).parents[1] / "adapters" / "inbound" / "web" / "templates"
)
_TEMPLATE_FRAGMENT_PATH = (
    pathlib.Path(__file__).parents[1] / "adapters" / "inbound" / "web"
    / "templates" / "fragments" / "c360_call_cockpit_panel.html"
)


def _insert_party(db, party_id: str) -> None:
    db.conn.execute(
        "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
        (party_id, "Test Party"),
    )
    db.conn.commit()


def _insert_staff(db, user_id: str) -> None:
    """crm_activity_log.staff_user_id REFERENCES crm_app_user(user_id)."""
    db.conn.execute(
        "INSERT OR IGNORE INTO crm_app_user (user_id, email, full_name) VALUES (?, ?, ?)",
        (user_id, f"{user_id}@test.vn", user_id),
    )
    db.conn.commit()


# ---------------------------------------------------------------------------
# ActivityService.find_open_draft — thin wrapper (new in this phase)
# ---------------------------------------------------------------------------

class TestFindOpenDraft:
    def test_returns_none_without_open_draft(self, seeded_crm_db):
        svc = ActivityService(SQLiteActivityRepository(seeded_crm_db), db=seeded_crm_db)
        party_id = "party-fod-1"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")

        assert svc.find_open_draft("staff-1", party_id) is None

    def test_returns_the_open_draft(self, seeded_crm_db):
        svc = ActivityService(SQLiteActivityRepository(seeded_crm_db), db=seeded_crm_db)
        party_id = "party-fod-2"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")
        draft = svc.create_draft(party_id, "staff-1")

        found = svc.find_open_draft("staff-1", party_id)
        assert found is not None
        assert found.activity_id == draft.activity_id

    def test_empty_ids_return_none_without_raising(self, seeded_crm_db):
        svc = ActivityService(SQLiteActivityRepository(seeded_crm_db), db=seeded_crm_db)
        assert svc.find_open_draft("", "party-x") is None
        assert svc.find_open_draft("staff-x", "") is None


# ---------------------------------------------------------------------------
# build_draft_activity_ctx — shaping for the strip's mid-call reload recovery
# ---------------------------------------------------------------------------

class TestBuildDraftActivityCtx:
    def test_none_when_activity_log_none(self):
        user = SimpleNamespace(user_id="staff-1")
        assert build_draft_activity_ctx(None, user, "party-1") is None

    def test_none_when_current_user_none(self):
        assert build_draft_activity_ctx(MagicMock(), None, "party-1") is None

    def test_none_when_no_open_draft(self):
        activity_log = MagicMock()
        activity_log.find_open_draft.return_value = None
        user = SimpleNamespace(user_id="staff-1")
        assert build_draft_activity_ctx(activity_log, user, "party-1") is None

    def test_shapes_dict_from_draft(self, seeded_crm_db):
        svc = ActivityService(SQLiteActivityRepository(seeded_crm_db), db=seeded_crm_db)
        party_id = "party-ctx-1"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"body": "hello", "custom_fields_patch": {"zalo_connected": True}}, "staff-1")

        user = SimpleNamespace(user_id="staff-1")
        ctx = build_draft_activity_ctx(svc, user, party_id)

        assert ctx is not None
        assert ctx["activity_id"] == draft.activity_id
        assert ctx["started_at"] == draft.started_at
        assert ctx["contact_outcome"] is None
        assert ctx["body"] == "hello"
        assert ctx["zalo_connected"] is True

    def test_returns_none_on_lookup_exception(self):
        activity_log = MagicMock()
        activity_log.find_open_draft.side_effect = RuntimeError("boom")
        user = SimpleNamespace(user_id="staff-1")
        assert build_draft_activity_ctx(activity_log, user, "party-1") is None


# ---------------------------------------------------------------------------
# Full-screen /customers/{id}/call — disposition strip initial phase
# ---------------------------------------------------------------------------

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
    env.globals["today"] = lambda: "2026-07-10"
    return Jinja2Templates(env=env)


def _build_cockpit_app(activity_log=None, inject_user_id: str = None) -> TestClient:
    """Minimal FastAPI app wired with register_call_cockpit_route, optionally
    injecting request.state.current_user (no real auth middleware exists in
    this harness — build_draft_activity_ctx() needs it to look up a draft)."""
    templates = _make_templates()
    app = FastAPI()

    if inject_user_id:
        @app.middleware("http")
        async def _inject_user(request, call_next):  # noqa: ANN001
            # layout.html (extended by call_cockpit.html) reads full_name/email/
            # role off request.state.current_user for the topbar avatar — a bare
            # user_id-only stub throws UndefinedError deep in an unrelated part
            # of the page, so give it the full shape here.
            request.state.current_user = SimpleNamespace(
                user_id=inject_user_id, full_name=inject_user_id,
                email=f"{inject_user_id}@test.vn", role="rep",
            )
            return await call_next(request)

    from fastapi import APIRouter
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
        router,
        templates,
        _load_base=_load_base,
        _load_insight=_load_insight,
        _sapo_customer_id=_sapo_customer_id,
        notes=notes_mock,
        party_tasks=party_tasks_mock,
        approach_repo=None,
        action_task_resolver=None,
        activity_log=activity_log,
    )
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


_PARTY_ID = "22222222-2222-2222-2222-222222222222"


class TestDispositionStripInitialPhase:
    def test_no_activity_log_renders_t0(self):
        client = _build_cockpit_app(activity_log=None)
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert 'data-phase="t0"' in r.text

    def test_no_open_draft_renders_t0(self, seeded_crm_db):
        svc = ActivityService(SQLiteActivityRepository(seeded_crm_db), db=seeded_crm_db)
        _insert_party(seeded_crm_db, _PARTY_ID)
        _insert_staff(seeded_crm_db, "staff-1")

        client = _build_cockpit_app(activity_log=svc, inject_user_id="staff-1")
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert 'data-phase="t0"' in r.text

    def test_open_draft_without_outcome_renders_t1(self, seeded_crm_db):
        svc = ActivityService(SQLiteActivityRepository(seeded_crm_db), db=seeded_crm_db)
        _insert_party(seeded_crm_db, _PARTY_ID)
        _insert_staff(seeded_crm_db, "staff-1")
        svc.create_draft(_PARTY_ID, "staff-1")

        client = _build_cockpit_app(activity_log=svc, inject_user_id="staff-1")
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert 'data-phase="t1"' in r.text, (
            "mid-call reload with an open draft (no outcome yet) must resume T1, not T0"
        )

    def test_open_draft_with_outcome_renders_t2(self, seeded_crm_db):
        svc = ActivityService(SQLiteActivityRepository(seeded_crm_db), db=seeded_crm_db)
        _insert_party(seeded_crm_db, _PARTY_ID)
        _insert_staff(seeded_crm_db, "staff-1")
        draft = svc.create_draft(_PARTY_ID, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "answered"}, "staff-1")

        client = _build_cockpit_app(activity_log=svc, inject_user_id="staff-1")
        r = client.get(f"/customers/{_PARTY_ID}/call")
        assert r.status_code == 200
        assert 'data-phase="t2"' in r.text, (
            "a draft with contact_outcome already chosen before the reload must resume T2"
        )

    def test_never_creates_a_second_draft_on_reload(self, seeded_crm_db):
        """Reload recovery must be read-only — GET /call must not call create_draft."""
        svc = ActivityService(SQLiteActivityRepository(seeded_crm_db), db=seeded_crm_db)
        _insert_party(seeded_crm_db, _PARTY_ID)
        _insert_staff(seeded_crm_db, "staff-1")
        svc.create_draft(_PARTY_ID, "staff-1")

        client = _build_cockpit_app(activity_log=svc, inject_user_id="staff-1")
        r1 = client.get(f"/customers/{_PARTY_ID}/call")
        r2 = client.get(f"/customers/{_PARTY_ID}/call")
        assert r1.status_code == 200
        assert r2.status_code == 200

        rows = seeded_crm_db.conn.execute(
            "SELECT COUNT(*) AS n FROM crm_activity_log WHERE party_id=? AND status='draft'",
            (_PARTY_ID,),
        ).fetchone()
        assert rows["n"] == 1


# ---------------------------------------------------------------------------
# Old outcome_bar removed / new disposition strip present — a lightweight
# automated stand-in for "S14 spec and template không lệch nhau" review.
# ---------------------------------------------------------------------------

class TestOldOutcomeBarFullyRemoved:
    def test_old_identifiers_gone_from_template(self):
        html = _TEMPLATE_FRAGMENT_PATH.read_text(encoding="utf-8")
        # Function-call/definition syntax ("(" immediately after the name) — not
        # a bare substring check, since the removal itself is legitimately noted
        # in a code comment ("...outcome_bar + s14OpenOutcome (M08-per-click)
        # ENTIRELY...") which would otherwise false-positive this check.
        for stale in (
            "s14OpenOutcome(", "s14QuickOutcomeVals(", "s14ClearQuickNote(",
            "s14QuickOutcomeError(", "s14AutoGrowNote(", "s14StartCallSession(",
            "class=\"s14-outcome\"", "s14-oc s14-oc--",
        ):
            assert stale not in html, f"stale outcome_bar identifier still present: {stale!r}"

    def test_new_strip_identifiers_present(self):
        html = _TEMPLATE_FRAGMENT_PATH.read_text(encoding="utf-8")
        for expected in (
            "id=\"s14-strip\"", "s14StripStartCall", "s14StripPickOutcome",
            "s14StripSave", "s14StripZaloFollowup", "data-phase",
        ):
            assert expected in html, f"expected disposition-strip identifier missing: {expected!r}"

    def test_spec_doc_has_no_outcome_bar_region(self):
        # crm/docs/ is NOT bind-mounted into the crm container (only src/
        # migrations/ops/sync/userscripts are — confirmed via `docker compose
        # exec crm ls /app/crm`), and CRM tests only ever run inside that
        # container, so this check cannot execute here. Spec/template naming
        # parity is instead verified via the ui-spec skill's own tools, run
        # on the host in this phase's implementation: `validate.mjs --root
        # ./crm/docs/ui-spec` (0 warnings) and `build.mjs` (ASCII regenerated
        # clean) — see the phase-03 implementation report.
        spec_path = (
            pathlib.Path(__file__).parents[3] / "crm" / "docs" / "ui-spec"
            / "screens" / "S14-call-mode-cockpit.md"
        )
        if not spec_path.exists():
            import pytest
            pytest.skip("crm/docs not mounted in the crm container — see docstring")
        text = spec_path.read_text(encoding="utf-8")
        assert "outcome_bar" not in text
        assert "disposition_strip" in text

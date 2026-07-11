"""test_activity_disposition_api_routes.py — phase-02 (activity-log disposition
API, P1): route-level coverage for the 3 new endpoints plus the legacy
draft-adopt hand-off, against a REAL ActivityService + seeded_crm_db (not a
mock) so 409/422 status mapping and idempotent side-effect skipping are
verified end-to-end, not just asserted against a mocked service.

Follows the mock-router-closure recovery pattern from test_bulk_resolve_endpoint.py
(no FastAPI TestClient — handlers recovered from router.post/patch.call_args_list).
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
from unittest.mock import MagicMock

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from application.activity_service import ActivityService  # noqa: E402
from application.activity_side_effects import execute_side_effects  # noqa: E402
from adapters.outbound.sqlite.activity_repository import SQLiteActivityRepository  # noqa: E402
import adapters.inbound.web.screens.customer360.screen_customer_360_activity as mod  # noqa: E402


def _insert_party(db, party_id: str) -> None:
    db.conn.execute(
        "INSERT INTO crm_party (party_id, display_name) VALUES (?, ?)",
        (party_id, "Test Party"),
    )
    db.conn.commit()


def _insert_staff(db, user_id: str) -> None:
    """crm_activity_log.staff_user_id REFERENCES crm_app_user(user_id) — tests
    must insert a real row, not an arbitrary string (migration 0004 FK)."""
    db.conn.execute(
        "INSERT OR IGNORE INTO crm_app_user (user_id, email, full_name) VALUES (?, ?, ?)",
        (user_id, f"{user_id}@test.vn", user_id),
    )
    db.conn.commit()


def _register(db, **overrides):
    """Register routes with a REAL ActivityService (backed by seeded_crm_db) and
    return (router_mock, activity_svc, notes_mock, task_svc_mock)."""
    activity_svc = ActivityService(SQLiteActivityRepository(db), last_contact_repo=None, db=db)
    router_mock = MagicMock()
    templates_mock = MagicMock()
    notes_mock = overrides.pop("notes", MagicMock())
    task_svc_mock = overrides.pop("task_svc", MagicMock())
    identities_mock = overrides.pop("identities", MagicMock())
    identities_mock.list_identities.return_value = []
    kwargs = dict(
        profile=MagicMock(),
        identities=identities_mock,
        notes=notes_mock,
        activity_log=activity_svc,
        task_svc=task_svc_mock,
        app_users=None,
        action_state=MagicMock(),
        party_insights=MagicMock(),
    )
    kwargs.update(overrides)
    mod.register_activity_routes(router_mock, templates_mock, **kwargs)
    return router_mock, activity_svc, notes_mock, task_svc_mock


def _post_handler(router_mock, index: int):
    return router_mock.post.return_value.call_args_list[index].args[0]


def _patch_handler(router_mock, index: int = 0):
    return router_mock.patch.return_value.call_args_list[index].args[0]


def _get_handler(router_mock, index: int):
    return router_mock.get.return_value.call_args_list[index].args[0]


def _req(user_id="staff-1"):
    request_mock = MagicMock()
    current_user = MagicMock(user_id=user_id) if user_id else None
    request_mock.state.current_user = current_user
    return request_mock


# ---------------------------------------------------------------------------
# POST /api/parties/{party_id}/call-sessions
# ---------------------------------------------------------------------------

class TestCreateCallSession:
    def test_idempotent_same_staff_party(self, seeded_crm_db):
        router_mock, svc, _, _ = _register(seeded_crm_db)
        handler = _post_handler(router_mock, 3)
        party_id = "party-cs-1"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")

        r1 = asyncio.run(handler(request=_req(), party_id=party_id, channel_identity_id="idn-1", task_id=""))
        r2 = asyncio.run(handler(request=_req(), party_id=party_id, channel_identity_id="idn-1", task_id=""))

        import json
        id1 = json.loads(r1.body)["activity_id"]
        id2 = json.loads(r2.body)["activity_id"]
        assert id1 == id2

    def test_unauthenticated_returns_401(self, seeded_crm_db):
        router_mock, svc, _, _ = _register(seeded_crm_db)
        handler = _post_handler(router_mock, 3)
        party_id = "party-cs-2"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")

        r = asyncio.run(handler(request=_req(user_id=None), party_id=party_id, channel_identity_id="", task_id=""))
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /api/activities/{activity_id}
# ---------------------------------------------------------------------------

class TestPatchActivityRoute:
    def test_invalid_enum_returns_422(self, seeded_crm_db):
        router_mock, svc, _, _ = _register(seeded_crm_db)
        party_id = "party-patch-1"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")
        draft = svc.create_draft(party_id, "staff-1")

        handler = _patch_handler(router_mock)
        r = asyncio.run(handler(
            request=_req(), activity_id=draft.activity_id,
            contact_outcome="replied",  # messaging outcome, invalid for channel_type='call'
            outcome_reason=None, body=None, callback_at=None, related_order_code=None,
            occurred_at=None, channel_identity_id=None, zalo_connected=None, edit_mode="",
        ))
        assert r.status_code == 422

    def test_unknown_activity_returns_404(self, seeded_crm_db):
        router_mock, svc, _, _ = _register(seeded_crm_db)
        handler = _patch_handler(router_mock)
        r = asyncio.run(handler(
            request=_req(), activity_id="nope",
            contact_outcome=None, outcome_reason=None, body="hi", callback_at=None,
            related_order_code=None, occurred_at=None, channel_identity_id=None,
            zalo_connected=None, edit_mode="",
        ))
        assert r.status_code == 404

    def test_no_side_effects_204_by_default(self, seeded_crm_db):
        router_mock, svc, notes_mock, task_svc_mock = _register(seeded_crm_db)
        party_id = "party-patch-2"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")
        draft = svc.create_draft(party_id, "staff-1")

        handler = _patch_handler(router_mock)
        r = asyncio.run(handler(
            request=_req(), activity_id=draft.activity_id,
            contact_outcome="answered", outcome_reason=None, body="hello",
            callback_at=None, related_order_code=None, occurred_at=None,
            channel_identity_id=None, zalo_connected=None, edit_mode="",
        ))
        assert r.status_code == 204
        notes_mock.add_note.assert_not_called()
        task_svc_mock.auto_claim_from_contact.assert_not_called()


# ---------------------------------------------------------------------------
# POST /api/activities/{activity_id}/finalize
# ---------------------------------------------------------------------------

class TestFinalizeActivityRoute:
    def test_409_without_contact_outcome(self, seeded_crm_db):
        router_mock, svc, _, _ = _register(seeded_crm_db)
        party_id = "party-fin-1"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")
        draft = svc.create_draft(party_id, "staff-1")

        handler = _post_handler(router_mock, 4)
        r = asyncio.run(handler(
            request=_req(), activity_id=draft.activity_id,
            complete_task_ids="", resolve_action_ids="", resolve_task_ids="",
            create_callback_task="", schedule_followup_at="", save_as_note="",
            note_type="outcome", pinned="0", visibility="team",
            promote_insight="0", insight_type="", insight_body="", insight_confidence="",
            contact_duration_s="",
        ))
        assert r.status_code == 409

    def test_idempotent_second_call_does_not_duplicate_side_effects(self, seeded_crm_db):
        router_mock, svc, notes_mock, task_svc_mock = _register(seeded_crm_db)
        party_id = "party-fin-2"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "answered", "body": "call notes"}, "staff-1")

        handler = _post_handler(router_mock, 4)
        kwargs = dict(
            request=_req(), activity_id=draft.activity_id,
            complete_task_ids="", resolve_action_ids="", resolve_task_ids="",
            create_callback_task="", schedule_followup_at="",
            save_as_note="1", note_type="outcome", pinned="0", visibility="team",
            promote_insight="0", insight_type="", insight_body="", insight_confidence="",
            contact_duration_s="",
        )
        r1 = asyncio.run(handler(**kwargs))
        r2 = asyncio.run(handler(**kwargs))

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert notes_mock.add_note.call_count == 1, "finalize must not double-write the note on a repeat call"

    def test_finalize_runs_auto_claim(self, seeded_crm_db):
        router_mock, svc, _, task_svc_mock = _register(seeded_crm_db)
        party_id = "party-fin-3"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "answered"}, "staff-1")

        handler = _post_handler(router_mock, 4)
        asyncio.run(handler(
            request=_req(), activity_id=draft.activity_id,
            complete_task_ids="", resolve_action_ids="", resolve_task_ids="",
            create_callback_task="", schedule_followup_at="", save_as_note="",
            note_type="outcome", pinned="0", visibility="team",
            promote_insight="0", insight_type="", insight_body="", insight_confidence="",
            contact_duration_s="",
        ))
        task_svc_mock.auto_claim_from_contact.assert_called_once()


# ---------------------------------------------------------------------------
# Legacy POST /customers/{party_id}/log-activity — draft-adopt hand-off
# ---------------------------------------------------------------------------

def _log_activity_kwargs(**overrides) -> dict:
    kwargs = dict(
        request=_req(), party_id="party-legacy-draft",
        hinh_thuc="call", channel_identity_id="", channel_value="",
        outcome="", contact_outcome="answered", outcome_reason="",
        body="ghi chú", occurred_at="", related_order_code="",
        callback_at="", create_callback_task="", save_as_note="",
        note_type="outcome", pinned="0", visibility="team",
        schedule_followup_at="", task_id="", complete_task="",
        resolve_action_ids="", resolve_task_ids="",
        promote_insight="0", insight_type="", insight_body="", insight_confidence="",
        zalo_connected="", source="", draft_activity_id="",
    )
    kwargs.update(overrides)
    return kwargs


class TestLegacyLogActivityDraftAdopt:
    def test_draft_activity_id_finalizes_same_row_with_duration(self, seeded_crm_db):
        router_mock, svc, _, _ = _register(seeded_crm_db)
        party_id = "party-legacy-draft"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")
        draft = svc.create_draft(party_id, "staff-1")

        handler = _post_handler(router_mock, 0)
        asyncio.run(handler(**_log_activity_kwargs(
            party_id=party_id, draft_activity_id=draft.activity_id, source="call_cockpit",
        )))

        row = seeded_crm_db.conn.execute(
            "SELECT status, contact_duration_s, body FROM crm_activity_log WHERE activity_id=?",
            (draft.activity_id,),
        ).fetchone()
        assert row["status"] == "final"
        assert row["contact_duration_s"] is not None
        assert row["body"] == "ghi chú"

        # No second row was inserted for this submit.
        count = seeded_crm_db.conn.execute(
            "SELECT COUNT(*) AS n FROM crm_activity_log WHERE party_id=?", (party_id,),
        ).fetchone()["n"]
        assert count == 1

    def test_without_draft_activity_id_inserts_fresh_row(self, seeded_crm_db):
        """Regression guard: absent draft_activity_id (every pre-P1 caller)
        keeps inserting a brand-new row exactly like before."""
        router_mock, svc, _, _ = _register(seeded_crm_db)
        party_id = "party-legacy-fresh"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")

        handler = _post_handler(router_mock, 0)
        asyncio.run(handler(**_log_activity_kwargs(party_id=party_id, draft_activity_id="")))

        rows = seeded_crm_db.conn.execute(
            "SELECT status, started_at, contact_duration_s FROM crm_activity_log WHERE party_id=?",
            (party_id,),
        ).fetchall()
        assert len(rows) == 1
        # Fresh-insert path never sets status/started_at — NULL reads as "final".
        assert rows[0]["status"] is None
        assert rows[0]["contact_duration_s"] is None


# ---------------------------------------------------------------------------
# execute_side_effects — callback/follow-up task assignee (phase-03 P0 #3)
# ---------------------------------------------------------------------------

class TestSideEffectsTaskAssignee:
    """Callback (step 4) and follow-up (step 5) tasks must be assigned to the
    actor who logged the call, not left unassigned in Hàng Đợi Chung."""

    def test_callback_task_assigned_to_actor(self):
        task_svc = MagicMock()
        execute_side_effects(
            MagicMock(activity_id="act-cb-1"), "staff-1",
            party_id="party-cb-1", task_svc=task_svc,
            create_callback_task=True, callback_at="2026-07-13T10:00:00Z",
        )
        task_data = task_svc.create_task.call_args.args[0]
        assert task_data["assignee_user_id"] == "staff-1"
        assert task_data["created_by"] == "staff-1"
        assert task_data["source"] == "manual"

    def test_followup_task_assigned_to_actor(self):
        task_svc = MagicMock()
        execute_side_effects(
            MagicMock(activity_id="act-fu-1"), "staff-2",
            party_id="party-fu-1", task_svc=task_svc,
            schedule_followup_at="2026-07-14T09:00:00Z",
        )
        task_data = task_svc.create_task.call_args.args[0]
        assert task_data["assignee_user_id"] == "staff-2"
        assert task_data["created_by"] == "staff-2"
        assert task_data["source"] == "manual"

    def test_actor_id_none_leaves_assignee_none(self):
        """Regression guard: activities without a resolvable actor (e.g. system
        import) must still create the task, just unassigned — no exception."""
        task_svc = MagicMock()
        execute_side_effects(
            MagicMock(activity_id="act-cb-2"), None,
            party_id="party-cb-2", task_svc=task_svc,
            create_callback_task=True, callback_at="2026-07-13T10:00:00Z",
        )
        task_data = task_svc.create_task.call_args.args[0]
        assert task_data["assignee_user_id"] is None
        assert task_data["created_by"] is None


# ---------------------------------------------------------------------------
# execute_side_effects — step 7 bulk-resolve outcome-aware snooze (phase-02 ①)
# ---------------------------------------------------------------------------

class TestSideEffectsBulkResolveOutcomeAware:
    """no_answer/busy → snooze (not dismiss), claimed task stays open.
    Every other outcome → prior dismiss+done behavior, unchanged."""

    def test_no_answer_snoozes_action_and_leaves_task_open(self):
        action_state = MagicMock()
        task_svc = MagicMock()
        execute_side_effects(
            MagicMock(activity_id="act-na-1", contact_outcome="no_answer"), "staff-1",
            party_id="party-na-1", action_state=action_state, task_svc=task_svc,
            resolve_action_ids=["a1"], resolve_task_ids=["t1"],
        )
        action_state.snooze.assert_called_once()
        aid, until_date = action_state.snooze.call_args.args
        assert aid == "a1"
        # until_date is "YYYY-MM-DD", ~2 days out — just check format + not today.
        assert len(until_date) == 10 and until_date.count("-") == 2
        action_state.dismiss.assert_not_called()
        task_svc.transition_status.assert_not_called()

    def test_busy_snoozes_action_and_leaves_task_open(self):
        action_state = MagicMock()
        task_svc = MagicMock()
        execute_side_effects(
            MagicMock(activity_id="act-busy-1", contact_outcome="busy"), "staff-1",
            party_id="party-busy-1", action_state=action_state, task_svc=task_svc,
            resolve_action_ids=["a2"], resolve_task_ids=["t2"],
        )
        action_state.snooze.assert_called_once_with(
            "a2", action_state.snooze.call_args.args[1], user_id="staff-1",
        )
        action_state.dismiss.assert_not_called()
        task_svc.transition_status.assert_not_called()

    def test_answered_still_dismisses_and_completes(self):
        """Control case: unaffected outcomes keep the prior dismiss+done behavior."""
        action_state = MagicMock()
        task_svc = MagicMock()
        execute_side_effects(
            MagicMock(activity_id="act-ans-1", contact_outcome="answered"), "staff-1",
            party_id="party-ans-1", action_state=action_state, task_svc=task_svc,
            resolve_action_ids=["a3"], resolve_task_ids=["t3"],
        )
        action_state.dismiss.assert_called_once_with("a3", user_id="staff-1")
        task_svc.transition_status.assert_called_once_with("t3", "done")
        action_state.snooze.assert_not_called()

    def test_no_contact_outcome_on_activity_falls_back_to_dismiss(self):
        """No contact_outcome at all (e.g. MagicMock w/o it set, or None) must not
        be misread as a no-contact outcome — prior behavior preserved."""
        action_state = MagicMock()
        task_svc = MagicMock()
        execute_side_effects(
            MagicMock(activity_id="act-none-1", contact_outcome=None), "staff-1",
            party_id="party-none-1", action_state=action_state, task_svc=task_svc,
            resolve_action_ids=["a4"], resolve_task_ids=["t4"],
        )
        action_state.dismiss.assert_called_once_with("a4", user_id="staff-1")
        task_svc.transition_status.assert_called_once_with("t4", "done")
        action_state.snooze.assert_not_called()


# ---------------------------------------------------------------------------
# POST /customers/{party_id}/reason/resolve-async — outcome gate (phase-02
# Amendment): the cockpit's "+Nhắn Zalo" follow-up button used to dismiss/
# complete unconditionally, undoing the snooze execute_side_effects step 7 had
# just applied for no_answer/busy. Route-level (real ActivityService + DB)
# coverage that contact_outcome now threads through to the same gate.
# ---------------------------------------------------------------------------

class TestResolveAsyncOutcomeGate:
    def test_no_answer_outcome_snoozes_not_dismisses(self, seeded_crm_db):
        action_state = MagicMock()
        router_mock, svc, _, task_svc_mock = _register(seeded_crm_db, action_state=action_state)
        handler = _post_handler(router_mock, 1)
        party_id = "party-ra-1"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")

        asyncio.run(handler(
            request=_req("staff-1"), party_id=party_id,
            channel="zalo", action_id="a1", task_id="", note="",
            contact_outcome="no_answer",
        ))

        action_state.snooze.assert_called_once()
        assert action_state.snooze.call_args.args[0] == "a1"
        action_state.dismiss.assert_not_called()

    def test_busy_outcome_snoozes_not_dismisses(self, seeded_crm_db):
        action_state = MagicMock()
        router_mock, svc, _, task_svc_mock = _register(seeded_crm_db, action_state=action_state)
        handler = _post_handler(router_mock, 1)
        party_id = "party-ra-2"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")

        asyncio.run(handler(
            request=_req("staff-1"), party_id=party_id,
            channel="zalo", action_id="a2", task_id="", note="",
            contact_outcome="busy",
        ))

        action_state.snooze.assert_called_once()
        action_state.dismiss.assert_not_called()

    def test_answered_outcome_still_dismisses(self, seeded_crm_db):
        """Control case: unaffected outcomes keep the prior dismiss behavior."""
        action_state = MagicMock()
        router_mock, svc, _, task_svc_mock = _register(seeded_crm_db, action_state=action_state)
        handler = _post_handler(router_mock, 1)
        party_id = "party-ra-3"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")

        asyncio.run(handler(
            request=_req("staff-1"), party_id=party_id,
            channel="zalo", action_id="a3", task_id="", note="",
            contact_outcome="answered",
        ))

        action_state.dismiss.assert_called_once_with("a3", user_id="staff-1")
        action_state.snooze.assert_not_called()

    def test_missing_contact_outcome_defaults_to_dismiss(self, seeded_crm_db):
        """Old client not yet sending contact_outcome must be unaffected —
        backward compatible with the pre-amendment endpoint signature."""
        action_state = MagicMock()
        router_mock, svc, _, task_svc_mock = _register(seeded_crm_db, action_state=action_state)
        handler = _post_handler(router_mock, 1)
        party_id = "party-ra-4"
        _insert_party(seeded_crm_db, party_id)
        _insert_staff(seeded_crm_db, "staff-1")

        asyncio.run(handler(
            request=_req("staff-1"), party_id=party_id,
            channel="zalo", action_id="a4", task_id="", note="",
            contact_outcome="",
        ))

        action_state.dismiss.assert_called_once_with("a4", user_id="staff-1")
        action_state.snooze.assert_not_called()

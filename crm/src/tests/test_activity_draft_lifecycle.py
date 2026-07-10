"""test_activity_draft_lifecycle.py — phase-02 (activity-log disposition API, P1).

Covers ActivityService.create_draft / patch_activity / finalize_activity against
a real SQLite DB with migrations applied (crm_activity_log.status/started_at/
finalize_at/contact_duration_s from migration 0045):

- create_draft is idempotent per (staff, party) — repeat calls adopt the same row.
- patch_activity rejects a contact_outcome invalid for the activity's channel_type.
- finalize_activity raises ActivityFinalizeConflictError (-> 409 at the route)
  when contact_outcome is still empty.
- finalize_activity is idempotent — second call reports already_finalized=True
  and does not re-stamp finalize_at/contact_duration_s.
- contact_duration_s is computed from started_at -> finalize_at.
- patch_activity(is_edit_mode=True) on an already-final row writes an audit
  trail (edited_at/edited_by/previous_outcome) into custom_fields.
"""
from __future__ import annotations

import pathlib
import sys
import time
import uuid

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

from application.activity_service import (  # noqa: E402
    ActivityFinalizeConflictError,
    ActivityNotFoundError,
    ActivityService,
)
from adapters.outbound.sqlite.activity_repository import SQLiteActivityRepository  # noqa: E402


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


def _make_service(db) -> ActivityService:
    return ActivityService(SQLiteActivityRepository(db), last_contact_repo=None, db=db)


class TestCreateDraftIdempotent:
    def test_second_call_adopts_same_draft(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)

        first = svc.create_draft(party_id, "staff-1", channel_identity_id="idn-1")
        second = svc.create_draft(party_id, "staff-1", channel_identity_id="idn-1")

        assert first.activity_id == second.activity_id
        assert first.status == "draft"
        assert first.started_at is not None

    def test_different_staff_get_different_drafts(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)

        a = svc.create_draft(party_id, "staff-a")
        b = svc.create_draft(party_id, "staff-b")

        assert a.activity_id != b.activity_id


class TestPatchActivityValidation:
    def test_rejects_outcome_invalid_for_channel_type(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")  # channel_type='call'

        with pytest.raises(ValueError):
            # 'replied' is a messaging outcome, not valid for channel_type='call'.
            svc.patch_activity(draft.activity_id, {"contact_outcome": "replied"}, "staff-1")

    def test_accepts_valid_outcome_and_reason(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")

        updated = svc.patch_activity(
            draft.activity_id,
            {"contact_outcome": "refused", "outcome_reason": "budget"},
            "staff-1",
        )
        assert updated.contact_outcome == "refused"
        assert updated.outcome_reason == "budget"
        assert updated.status == "draft"  # PATCH never finalizes

    def test_unknown_activity_id_raises_not_found(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        with pytest.raises(ActivityNotFoundError):
            svc.patch_activity("does-not-exist", {"body": "x"}, "staff-1")

    def test_custom_fields_patch_merges_not_replaces(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1", channel_identity_id="idn-9")

        updated = svc.patch_activity(
            draft.activity_id,
            {"custom_fields_patch": {"zalo_connected": True}},
            "staff-1",
        )
        assert updated.custom_fields.get("channel_identity_id") == "idn-9"
        assert updated.custom_fields.get("zalo_connected") is True


class TestFinalizeActivity:
    def test_409_when_no_contact_outcome(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")

        with pytest.raises(ActivityFinalizeConflictError):
            svc.finalize_activity(draft.activity_id)

    def test_finalize_sets_status_and_duration(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "answered"}, "staff-1")

        time.sleep(0.05)
        activity, already_final = svc.finalize_activity(draft.activity_id)

        assert already_final is False
        assert activity.status == "final"
        assert activity.finalize_at is not None
        assert activity.contact_duration_s is not None
        assert activity.contact_duration_s >= 0

    def test_finalize_idempotent_second_call_is_noop(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "answered"}, "staff-1")

        first, first_already = svc.finalize_activity(draft.activity_id)
        second, second_already = svc.finalize_activity(draft.activity_id)

        assert first_already is False
        assert second_already is True
        assert first.finalize_at == second.finalize_at
        assert first.contact_duration_s == second.contact_duration_s

    def test_manual_duration_override_wins(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "answered"}, "staff-1")

        activity, _ = svc.finalize_activity(draft.activity_id, contact_duration_s_override=999)
        assert activity.contact_duration_s == 999

    def test_unknown_activity_id_raises_not_found(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        with pytest.raises(ActivityNotFoundError):
            svc.finalize_activity("does-not-exist")


class TestTwoStepPatchThenFinalize:
    """Regression coverage for the disposition-strip bug (260711): the strip's
    JS PATCHes contact_outcome the instant a pill is clicked, BEFORE the reason
    is known (the reason sheet opens after) — reason arrives in a SEPARATE,
    later PATCH call. patch_activity used to validate REASON_REQUIRED_OUTCOMES
    on every intermediate call, computing next_reason from the not-yet-patched
    activity — so the very first PATCH (outcome only) always raised, and
    contact_outcome was never actually committed. Finalize then always 409'd.
    Fix: patch_activity no longer enforces this; finalize_activity does, as the
    single commit point."""

    def test_outcome_then_reason_in_separate_patches_then_finalize_succeeds(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")

        # Step 1: the exact click-through — pill click PATCHes contact_outcome
        # alone. This must NOT raise (previously raised immediately).
        after_outcome = svc.patch_activity(
            draft.activity_id, {"contact_outcome": "refused"}, "staff-1",
        )
        assert after_outcome.contact_outcome == "refused"
        assert after_outcome.outcome_reason is None
        assert after_outcome.status == "draft"

        # Step 2: reason sheet closes — a SEPARATE, later PATCH call.
        after_reason = svc.patch_activity(
            draft.activity_id, {"outcome_reason": "budget"}, "staff-1",
        )
        assert after_reason.contact_outcome == "refused"
        assert after_reason.outcome_reason == "budget"

        # Step 3: finalize must now succeed — both fields present by commit time.
        activity, already_final = svc.finalize_activity(draft.activity_id)
        assert already_final is False
        assert activity.status == "final"
        assert activity.contact_outcome == "refused"
        assert activity.outcome_reason == "budget"

    def test_finalize_still_rejects_refused_outcome_missing_reason(self, seeded_crm_db):
        """Enforcement is relocated to finalize, not removed."""
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")

        svc.patch_activity(draft.activity_id, {"contact_outcome": "refused"}, "staff-1")

        with pytest.raises(ActivityFinalizeConflictError, match="outcome_reason is required"):
            svc.finalize_activity(draft.activity_id)

    def test_finalize_still_rejects_irritation_reason_missing_body(self, seeded_crm_db):
        """Same relocation applies to the 'irritation' body-required check."""
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")

        svc.patch_activity(draft.activity_id, {"contact_outcome": "answered"}, "staff-1")
        svc.patch_activity(draft.activity_id, {"outcome_reason": "irritation"}, "staff-1")

        with pytest.raises(ActivityFinalizeConflictError, match="body is required"):
            svc.finalize_activity(draft.activity_id)


class TestEditActivityAudit:
    def test_edit_mode_on_final_row_stamps_audit_trail(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "no_answer"}, "staff-1")
        svc.finalize_activity(draft.activity_id)

        edited = svc.patch_activity(
            draft.activity_id,
            {"contact_outcome": "answered"},
            "staff-2",
            is_edit_mode=True,
        )

        assert edited.contact_outcome == "answered"
        assert edited.custom_fields.get("previous_outcome") == "no_answer"
        assert edited.custom_fields.get("edited_by") == "staff-2"
        assert edited.custom_fields.get("edited_at") is not None

    def test_edit_mode_same_outcome_does_not_stamp_audit(self, seeded_crm_db):
        """Re-saving the same outcome (no actual change) shouldn't add audit noise."""
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2", "staff-a", "staff-b"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "no_answer"}, "staff-1")
        svc.finalize_activity(draft.activity_id)

        edited = svc.patch_activity(
            draft.activity_id,
            {"contact_outcome": "no_answer"},
            "staff-1",
            is_edit_mode=True,
        )
        assert (edited.custom_fields or {}).get("previous_outcome") is None

    def test_edit_mode_on_final_row_rejects_refused_without_reason(self, seeded_crm_db):
        """Editing an already-FINAL row has no future finalize_activity call to
        catch a missing reason — patch_activity itself must enforce it here,
        server-side, not rely on the client-side M08 form guard alone."""
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "no_answer"}, "staff-1")
        svc.finalize_activity(draft.activity_id)

        with pytest.raises(ValueError, match="outcome_reason is required"):
            svc.patch_activity(
                draft.activity_id,
                {"contact_outcome": "refused"},
                "staff-2",
                is_edit_mode=True,
            )

    def test_edit_mode_on_final_row_rejects_irritation_without_body(self, seeded_crm_db):
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "no_answer"}, "staff-1")
        svc.finalize_activity(draft.activity_id)

        with pytest.raises(ValueError, match="body is required"):
            svc.patch_activity(
                draft.activity_id,
                {"contact_outcome": "refused", "outcome_reason": "irritation"},
                "staff-2",
                is_edit_mode=True,
            )

    def test_edit_mode_on_final_row_accepts_refused_with_reason(self, seeded_crm_db):
        """Sanity check: the guard only blocks the invalid combination, not
        'refused' edits in general."""
        svc = _make_service(seeded_crm_db)
        party_id = str(uuid.uuid4())
        _insert_party(seeded_crm_db, party_id)
        for _sid in ("staff-1", "staff-2"):
            _insert_staff(seeded_crm_db, _sid)
        draft = svc.create_draft(party_id, "staff-1")
        svc.patch_activity(draft.activity_id, {"contact_outcome": "no_answer"}, "staff-1")
        svc.finalize_activity(draft.activity_id)

        edited = svc.patch_activity(
            draft.activity_id,
            {"contact_outcome": "refused", "outcome_reason": "still_stocked"},
            "staff-2",
            is_edit_mode=True,
        )
        assert edited.contact_outcome == "refused"
        assert edited.outcome_reason == "still_stocked"

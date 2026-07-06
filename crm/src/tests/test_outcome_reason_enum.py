"""Unit tests for D2 Phase 03 — contact_outcome + outcome_reason enum validation.

Covers:
- CONTACT_OUTCOMES_* constants completeness
- VALID_CONTACT_OUTCOMES deduplication
- CONTACT_OUTCOMES_BY_CHANNEL_TYPE per-channel lists
- VALID_OUTCOME_REASONS count and membership
- REASON_REQUIRED_OUTCOMES set contents
- ActivityService validation: wrong channel, missing reason, unknown reason, valid path
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import MagicMock

import pytest

# ── sys.path setup (mirrors conftest.py pattern) ──────────────────────────────
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # data-integration/
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1]) # crm/src/
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.domain.entities.activity import (  # noqa: E402
    CONTACT_OUTCOMES_CALL,
    CONTACT_OUTCOMES_MESSAGING,
    CONTACT_OUTCOMES_VISIT,
    VALID_CONTACT_OUTCOMES,
    CONTACT_OUTCOMES_BY_CHANNEL_TYPE,
    VALID_OUTCOME_REASONS,
    REASON_REQUIRED_OUTCOMES,
)


# ── Contact outcome constants ─────────────────────────────────────────────────

class TestContactOutcomeConstants:
    def test_all_call_outcomes_in_valid(self):
        for o in CONTACT_OUTCOMES_CALL:
            assert o in VALID_CONTACT_OUTCOMES

    def test_all_messaging_outcomes_in_valid(self):
        for o in CONTACT_OUTCOMES_MESSAGING:
            assert o in VALID_CONTACT_OUTCOMES

    def test_all_visit_outcomes_in_valid(self):
        for o in CONTACT_OUTCOMES_VISIT:
            assert o in VALID_CONTACT_OUTCOMES

    def test_call_has_busy_and_wrong_number(self):
        assert "busy" in CONTACT_OUTCOMES_CALL
        assert "wrong_number" in CONTACT_OUTCOMES_CALL

    def test_messaging_has_blocked(self):
        assert "blocked" in CONTACT_OUTCOMES_MESSAGING

    def test_call_outcomes_not_in_visit(self):
        # call-only outcomes should not bleed into visit
        assert "busy" not in CONTACT_OUTCOMES_VISIT
        assert "no_answer" not in CONTACT_OUTCOMES_VISIT

    def test_valid_outcomes_no_duplicates(self):
        assert len(VALID_CONTACT_OUTCOMES) == len(set(VALID_CONTACT_OUTCOMES))

    def test_channel_type_mapping_keys(self):
        expected_keys = {"call", "zalo", "fb", "email", "visit"}
        assert set(CONTACT_OUTCOMES_BY_CHANNEL_TYPE.keys()) == expected_keys

    def test_zalo_and_fb_share_messaging_outcomes(self):
        assert CONTACT_OUTCOMES_BY_CHANNEL_TYPE["zalo"] == CONTACT_OUTCOMES_MESSAGING
        assert CONTACT_OUTCOMES_BY_CHANNEL_TYPE["fb"] == CONTACT_OUTCOMES_MESSAGING


# ── Outcome reason constants ──────────────────────────────────────────────────

class TestOutcomeReasonConstants:
    def test_valid_reasons_count(self):
        assert len(VALID_OUTCOME_REASONS) == 11

    def test_refused_in_required_set(self):
        assert "refused" in REASON_REQUIRED_OUTCOMES

    def test_answered_not_required(self):
        assert "answered" not in REASON_REQUIRED_OUTCOMES

    def test_known_reasons_present(self):
        for r in ("budget", "timing", "product_fit", "competitor",
                  "stock", "trust", "no_need", "other",
                  "still_stocked", "wait_promo", "irritation"):
            assert r in VALID_OUTCOME_REASONS

    def test_unknown_reason_not_in_list(self):
        assert "xyz" not in VALID_OUTCOME_REASONS
        assert "price" not in VALID_OUTCOME_REASONS


# ── ActivityService validation ────────────────────────────────────────────────

def _make_service():
    """Return an ActivityService with mocked repos."""
    from crm.src.application.activity_service import ActivityService
    repo = MagicMock()
    repo.insert.return_value = None
    svc = ActivityService(activity_repo=repo)
    return svc


def _base_data(**kwargs) -> dict:
    return {
        "party_id": "party-001",
        "activity_type": "call",
        "channel_type": "call",
        **kwargs,
    }


class TestActivityServiceContactOutcomeValidation:
    def test_valid_call_outcome_accepted(self):
        svc = _make_service()
        # Should not raise
        act = svc.log_activity(_base_data(contact_outcome="answered"))
        assert act.contact_outcome == "answered"

    def test_wrong_outcome_for_channel_raises(self):
        svc = _make_service()
        with pytest.raises(ValueError, match="not valid for channel_type"):
            svc.log_activity(_base_data(
                channel_type="call",
                contact_outcome="replied",  # messaging-only outcome
            ))

    def test_refused_without_reason_raises(self):
        svc = _make_service()
        with pytest.raises(ValueError, match="outcome_reason is required"):
            svc.log_activity(_base_data(
                contact_outcome="refused",
                outcome_reason="",
            ))

    def test_refused_with_valid_reason_accepted(self):
        svc = _make_service()
        act = svc.log_activity(_base_data(
            contact_outcome="refused",
            outcome_reason="budget",
        ))
        assert act.contact_outcome == "refused"
        assert act.outcome_reason == "budget"

    def test_unknown_outcome_reason_raises(self):
        svc = _make_service()
        with pytest.raises(ValueError, match="unknown outcome_reason"):
            svc.log_activity(_base_data(
                contact_outcome="answered",
                outcome_reason="xyz_invalid",
            ))

    def test_visit_outcome_met_accepted(self):
        svc = _make_service()
        act = svc.log_activity(_base_data(
            activity_type="visit",
            channel_type="visit",
            contact_outcome="met",
        ))
        assert act.contact_outcome == "met"

    def test_no_contact_outcome_accepted(self):
        """contact_outcome is optional — omitting it is valid."""
        svc = _make_service()
        act = svc.log_activity(_base_data())
        assert act.contact_outcome is None

    def test_unknown_channel_type_falls_back_to_all_outcomes(self):
        """Unknown channel_type accepts any outcome from VALID_CONTACT_OUTCOMES."""
        svc = _make_service()
        act = svc.log_activity(_base_data(
            channel_type="other",
            contact_outcome="answered",
        ))
        assert act.contact_outcome == "answered"

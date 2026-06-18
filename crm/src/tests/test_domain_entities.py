"""test_domain_entities.py — unit tests for CRM domain entity dataclasses and constants."""
from __future__ import annotations

import pathlib, sys  # noqa: E401
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.domain.entities.party import (  # noqa: E402
    Party, PartyIdentity,
    PARTY_TYPE_PERSON, PARTY_TYPE_ORG, VALID_PARTY_TYPES,
    PARTY_STATUS_ACTIVE, PARTY_STATUS_INACTIVE, PARTY_STATUS_BLOCKED, VALID_PARTY_STATUSES,
    IDENTITY_TYPE_SAPO_CUSTOMER, IDENTITY_TYPE_PHONE, IDENTITY_TYPE_EMAIL, VALID_IDENTITY_TYPES,
    CONTACT_QUALITY_UNVERIFIED, CONTACT_QUALITY_MASKED, CONTACT_QUALITY_VERIFIED,
    DEDUP_STATUS_PENDING, DEDUP_STATUS_MERGED, DEDUP_STATUS_REJECTED,
)
from crm.src.domain.entities.task import (  # noqa: E402
    Task, TASK_STATUS_OPEN, TASK_STATUS_DONE, TASK_STATUS_CANCELLED,
    VALID_TASK_STATUSES, TASK_PRIORITY_NORMAL, TASK_PRIORITY_HIGH, TASK_PRIORITY_URGENT,
    TASK_ALLOWED_TRANSITIONS,
)

_TS = "2026-06-15T00:00:00.000Z"


# ── Party ─────────────────────────────────────────────────────────────────────

def test_party_creation_and_defaults():
    p = Party(party_id="p-001", party_type=PARTY_TYPE_PERSON, display_name="Nguyen Van A",
              primary_phone="+84901000001", primary_email="a@test.vn",
              status=PARTY_STATUS_ACTIVE, is_merged=False, created_at=_TS, updated_at=_TS)
    assert p.party_id == "p-001"
    assert p.is_merged is False
    assert p.merged_into is None          # optional; default None


def test_party_type_constants():
    assert PARTY_TYPE_PERSON == "person"
    assert PARTY_TYPE_ORG == "org"
    assert set(VALID_PARTY_TYPES) == {"person", "org"}


def test_party_status_constants():
    assert PARTY_STATUS_ACTIVE == "active"
    assert PARTY_STATUS_INACTIVE == "inactive"
    assert PARTY_STATUS_BLOCKED == "blocked"
    assert len(VALID_PARTY_STATUSES) == 3


def test_party_merged_into_field():
    p = Party(party_id="p-002", party_type=PARTY_TYPE_PERSON, display_name="",
              primary_phone="", primary_email="", status=PARTY_STATUS_INACTIVE,
              is_merged=True, created_at=_TS, updated_at=_TS, merged_into="p-001")
    assert p.merged_into == "p-001"


# ── PartyIdentity ─────────────────────────────────────────────────────────────

def test_party_identity_creation_and_defaults():
    ident = PartyIdentity(
        identity_id="i-001", party_id="p-001", source_system="sapo_v2",
        identity_type=IDENTITY_TYPE_SAPO_CUSTOMER, identity_value="1001",
        confidence=1.0, is_primary=True,
        source_contact_quality=CONTACT_QUALITY_UNVERIFIED,
        contact_quality=CONTACT_QUALITY_UNVERIFIED, created_at=_TS,
    )
    assert ident.confidence == 1.0
    assert ident.verified_at is None      # optional; default None


def test_identity_type_constants():
    assert IDENTITY_TYPE_SAPO_CUSTOMER == "sapo_customer"
    assert IDENTITY_TYPE_PHONE == "phone"
    assert IDENTITY_TYPE_EMAIL == "email"
    assert len(VALID_IDENTITY_TYPES) == 6


def test_contact_quality_constants():
    assert CONTACT_QUALITY_MASKED == "masked"
    assert CONTACT_QUALITY_UNVERIFIED == "unverified"
    assert CONTACT_QUALITY_VERIFIED == "verified"


def test_dedup_status_constants():
    assert DEDUP_STATUS_PENDING == "pending"
    assert DEDUP_STATUS_MERGED == "merged"
    assert DEDUP_STATUS_REJECTED == "rejected"


# ── Task ──────────────────────────────────────────────────────────────────────

def test_task_status_constants():
    assert TASK_STATUS_OPEN == "open"
    assert TASK_STATUS_DONE == "done"
    assert TASK_STATUS_CANCELLED == "cancelled"
    assert len(VALID_TASK_STATUSES) == 4


def test_task_priority_constants():
    assert TASK_PRIORITY_NORMAL == 0
    assert TASK_PRIORITY_HIGH == 1
    assert TASK_PRIORITY_URGENT == 2


def test_task_allowed_transitions():
    # open → doing; done/cancelled allow re-open
    assert "doing" in TASK_ALLOWED_TRANSITIONS[TASK_STATUS_OPEN]
    assert TASK_STATUS_OPEN in TASK_ALLOWED_TRANSITIONS[TASK_STATUS_DONE]
    assert TASK_STATUS_OPEN in TASK_ALLOWED_TRANSITIONS[TASK_STATUS_CANCELLED]


def test_task_optional_fields_default_to_none():
    t = Task(task_id="t-001", title="Call", priority=TASK_PRIORITY_NORMAL,
             status=TASK_STATUS_OPEN, source="manual",
             created_at=_TS, updated_at=_TS)
    assert t.party_id is None
    assert t.due_at is None
    assert t.assignee_user_id is None

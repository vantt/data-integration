"""test_party_service.py — unit tests for PartyService normalize helpers and upsert logic."""
from __future__ import annotations

import pathlib, sys  # noqa: E401
from unittest.mock import MagicMock
import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from crm.src.application.party_service import normalize_phone, normalize_email, phone_to_e164, PartyService  # noqa: E402
from crm.src.domain.entities.party import Party  # noqa: E402

_TS = "2026-06-15T00:00:00.000Z"


# ── normalize_phone ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("0912345678",      "0912345678"),     # VN 0-prefix kept as-is
    ("0 912 345 678",   "0912345678"),     # spaces stripped
    ("0912.345.678",    "0912345678"),     # dots stripped
    ("+84912345678",    "0912345678"),     # +84 → 0
    ("+84 912 345 678", "0912345678"),     # +84 + spaces → 0
    ("84912345678",     "0912345678"),     # 84-prefix (11 digits) → 0
    ("",                ""),
    ("+1 800 555 1234", "+18005551234"),   # non-VN: strip non-digit-non-plus, keep +
    ("   ",             ""),
    ("+",               ""),              # no digits
    ("abcdef",          ""),
])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_normalize_phone_zero_edge():
    assert normalize_phone("0") == "0"  # 0-prefix keeps as-is


# ── normalize_email ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("User@Example.COM", "user@example.com"),
    ("  trim@me.vn  ",   "trim@me.vn"),
    ("",                 ""),
    ("UPPER@DOMAIN.VN",  "upper@domain.vn"),
])
def test_normalize_email(raw, expected):
    assert normalize_email(raw) == expected


# ── Helpers ───────────────────────────────────────────────────────────────────

def _repo(existing=None):
    r = MagicMock()
    r.find_by_identity.return_value = existing
    r.create_with_identities.side_effect = lambda p, ids: p
    return r


def _party(name="Nguyen Van A", phone="0901000001"):
    return Party(party_id="p-001", party_type="person", display_name=name,
                 primary_phone=phone, primary_email="a@test.vn", status="active",
                 is_merged=False, created_at=_TS, updated_at=_TS)


def _upsert(svc, phone="0901000001", email="a@test.vn", name="Nguyen Van A"):
    return svc.upsert_from_sapo_identity(
        sapo_id="1001", phone=phone, email=email, display_name=name,
        src_quality="unverified", quality="unverified")


# ── upsert tests ──────────────────────────────────────────────────────────────

def test_upsert_creates_party_and_sapo_identity():
    repo = _repo()
    _upsert(PartyService(repo))
    party, ids = repo.create_with_identities.call_args[0]
    assert party.primary_phone == "0901000001"
    assert ids[0].identity_type == "sapo_customer" and ids[0].identity_value == "1001"


def test_upsert_returns_existing_party_without_recreating():
    repo = _repo(existing=_party())
    result = _upsert(PartyService(repo))
    repo.create_with_identities.assert_not_called()
    assert result.party_id == "p-001"


def test_upsert_attaches_phone_and_email():
    repo = _repo()
    _upsert(PartyService(repo))
    types = [c[0][0].identity_type for c in repo.upsert_identity.call_args_list]
    assert "phone" in types and "email" in types


def test_upsert_skips_phone_identity_when_blank():
    repo = _repo()
    _upsert(PartyService(repo), phone="")
    types = [c[0][0].identity_type for c in repo.upsert_identity.call_args_list]
    assert "phone" not in types and "email" in types


def test_upsert_backfills_empty_name():
    repo = _repo(existing=_party(name=""))
    _upsert(PartyService(repo), name="Nguyen Van A")
    repo.update.assert_called_once()
    assert repo.update.call_args[0][0].display_name == "Nguyen Van A"


def test_upsert_does_not_overwrite_existing_name():
    repo = _repo(existing=_party(name="Original"))
    _upsert(PartyService(repo), name="New")
    repo.update.assert_not_called()


# ── phone_to_e164 ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("local,expected", [
    ("0912345678",   "+84912345678"),
    ("+84912345678", "+84912345678"),  # already E.164
    ("12345",        "12345"),         # unrecognized, pass-through
])
def test_phone_to_e164(local, expected):
    assert phone_to_e164(local) == expected

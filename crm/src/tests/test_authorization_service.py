"""test_authorization_service.py — unit tests for AuthorizationService.

Pure logic class (no IO, no fixtures needed). Covers the 2 v1 methods:
  - is_owner: identity-ownership check (Phase 2 unclaim ownership consumer)
  - is_same_party: scope-containment check (Phase 3 resolve-actions IDOR consumer)
"""
from __future__ import annotations

import pathlib
import sys

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from application.authorization_service import AuthorizationService  # noqa: E402


def _svc() -> AuthorizationService:
    return AuthorizationService()


# ── is_owner ──────────────────────────────────────────────────────────────

def test_is_owner_matching_ids_returns_true():
    assert _svc().is_owner("user-1", "user-1") is True


def test_is_owner_mismatched_ids_returns_false():
    assert _svc().is_owner("user-1", "user-2") is False


def test_is_owner_empty_actor_returns_false():
    assert _svc().is_owner("user-1", None) is False
    assert _svc().is_owner("user-1", "") is False


def test_is_owner_empty_resource_returns_false():
    assert _svc().is_owner(None, "user-1") is False
    assert _svc().is_owner("", "user-1") is False


# ── is_same_party ─────────────────────────────────────────────────────────

def test_is_same_party_matching_ids_returns_true():
    assert _svc().is_same_party("party-1", "party-1") is True


def test_is_same_party_mismatched_ids_returns_false():
    assert _svc().is_same_party("party-1", "party-2") is False


def test_is_same_party_none_resource_fails_closed():
    assert _svc().is_same_party(None, "party-1") is False

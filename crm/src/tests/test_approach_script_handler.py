"""test_approach_script_handler.py — Integration tests for GET /api/parties/{id}/approach-script.

Cases:
  - party with sapo_customer identity + script file → 200, correct script + meta
  - party with no sapo_customer identity → 404
  - party with sapo_customer identity but no script file → 200, script=null, meta=null

Uses FastAPI TestClient (requires httpx: pip install httpx).
Repos are wired with minimal mocks — no DB required.

Run inside container:
  docker compose exec crm python -m pytest src/tests/test_approach_script_handler.py -q
Or from repo root:
  PYTHONPATH="crm/src" python -m pytest crm/src/tests/test_approach_script_handler.py -q
"""
from __future__ import annotations

import json
import pathlib
import sys
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])    # .../data-integration
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # .../crm/src
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI                                                      # noqa: E402
from starlette.testclient import TestClient                                      # noqa: E402
from adapters.inbound.http import approach_script_handler                        # noqa: E402
from adapters.inbound.http.approach_script_handler import wire_approach_script_router  # noqa: E402
from adapters.outbound.file.approach_script_file_repository import FileApproachScriptRepository  # noqa: E402
from domain.entities.party import PartyIdentity                                  # noqa: E402


# ── Helpers ───────────────────────────────────────────────────────────────────

_VALID_DATA = {
    "profile_read": "Test profile",
    "approach": {
        "recommended": True,
        "primary_channel": "phone",
        "fallback_channel": "sms",
        "timing": "",
        "opening_message": "Xin chào",
        "fallback_message": "",
        "talking_points": [],
        "cross_sell": [],
        "objection_handling": [],
        "do_not": [],
    },
    "confidence": "high",
    "data_gaps": [],
}


def _make_identity(identity_type: str, identity_value: str) -> PartyIdentity:
    return PartyIdentity(
        identity_id="i-001",
        party_id="p-001",
        source_system="sapo_v2",
        identity_type=identity_type,
        identity_value=identity_value,
        confidence=1.0,
        is_primary=True,
        source_contact_quality="unverified",
        contact_quality="unverified",
        created_at="2026-01-01T00:00:00Z",
    )


def _make_app(party_repo, approach_repo) -> FastAPI:
    """Build a minimal FastAPI app with approach_script_handler wired."""
    # Reset module-level holders between tests.
    approach_script_handler._party_repo = None
    approach_script_handler._approach_repo = None

    wire_approach_script_router(party_repo, approach_repo)
    app = FastAPI()
    app.include_router(approach_script_handler.router)
    return app


def _party_repo_with_sapo_customer(customer_id: int):
    """PartyRepository mock returning one sapo_customer identity."""
    repo = MagicMock()
    repo.list_identities.return_value = [
        _make_identity("sapo_customer", str(customer_id)),
    ]
    return repo


def _party_repo_no_identity():
    """PartyRepository mock returning no identities."""
    repo = MagicMock()
    repo.list_identities.return_value = []
    return repo


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_party_with_script_returns_200_correct_body(tmp_path):
    """Party with sapo_customer identity + file → 200, script + meta present."""
    customer_id = 603264280
    script_file = tmp_path / f"{customer_id}.json"
    script_file.write_text(json.dumps(_VALID_DATA, ensure_ascii=False), encoding="utf-8")

    party_repo = _party_repo_with_sapo_customer(customer_id)
    approach_repo = FileApproachScriptRepository(tmp_path)
    client = TestClient(_make_app(party_repo, approach_repo))

    resp = client.get("/api/parties/p-test/approach-script")

    assert resp.status_code == 200
    body = resp.json()
    assert body["script"] is not None
    assert body["script"]["approach"]["recommended"] is True
    assert body["meta"]["recommended"] is True
    assert body["meta"]["confidence"] == "high"
    assert body["meta"]["refreshed_at"].endswith("Z")


def test_party_no_sapo_identity_returns_404(tmp_path):
    """Party with no sapo_customer identity → 404."""
    party_repo = _party_repo_no_identity()
    approach_repo = FileApproachScriptRepository(tmp_path)
    client = TestClient(_make_app(party_repo, approach_repo))

    resp = client.get("/api/parties/p-no-ident/approach-script")

    assert resp.status_code == 404
    assert "sapo_customer" in resp.json()["detail"]


def test_party_with_identity_but_no_file_returns_200_null(tmp_path):
    """Valid party with sapo_customer identity but no script file → 200, null."""
    customer_id = 999999999  # no file for this id
    party_repo = _party_repo_with_sapo_customer(customer_id)
    approach_repo = FileApproachScriptRepository(tmp_path)
    client = TestClient(_make_app(party_repo, approach_repo))

    resp = client.get("/api/parties/p-no-file/approach-script")

    assert resp.status_code == 200
    body = resp.json()
    assert body["script"] is None
    assert body["meta"] is None

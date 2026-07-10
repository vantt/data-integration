"""Tests for fix 260710-1447 (UX feedback):

- GET /modals/m08?prefill_body=... renders the value into #m08-body server-side
  (replaces the old client-side .then() inject, which raced the HTMX swap).
- REASON_PILLS 'irritation' label is "Tác dụng phụ" in the rendered fragment
  (label-only change; enum value stays 'irritation' for data compatibility).

Follows the real-Jinja2-template rendering pattern from
test_claim_context_snooze_r14.py's TestQueuePosAutoCorrection (`_make_templates`)
so the assertions exercise the actual template, not a mock.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

# ── sys.path setup (mirrors conftest.py / sibling test files) ────────────────
_REPO_ROOT = str(pathlib.Path(__file__).parents[4])   # data-integration/
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])  # crm/src/
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI, APIRouter                                        # noqa: E402
from fastapi.testclient import TestClient                                     # noqa: E402
from fastapi.templating import Jinja2Templates                                # noqa: E402
from unittest.mock import MagicMock                                           # noqa: E402

_TEMPLATES_DIR = str(
    pathlib.Path(__file__).parents[1] / "adapters" / "inbound" / "web" / "templates"
)


def _make_templates() -> Jinja2Templates:
    import jinja2
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(_TEMPLATES_DIR),
        autoescape=True,
        auto_reload=False,
    )
    return Jinja2Templates(env=env)


def _build_m08_app() -> TestClient:
    import adapters.inbound.web.screens.customer360.screen_customer_360_activity as mod

    templates = _make_templates()
    app = FastAPI()
    router = APIRouter()

    notes_mock = MagicMock()
    notes_mock.list_notes.return_value = []
    identities_mock = MagicMock()
    identities_mock.list_identities.return_value = []

    mod.register_activity_routes(
        router, templates,
        profile=MagicMock(), identities=identities_mock, notes=notes_mock,
        activity_log=MagicMock(), task_svc=None, app_users=None, action_state=None,
    )
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestM08PrefillBody:
    def test_prefill_body_rendered_into_textarea(self):
        client = _build_m08_app()
        r = client.get(
            "/modals/m08?party_id=party-1&mode=log&prefill_body=Kh%C3%A1ch%20h%E1%BA%B9n%20g%E1%BB%8Di%20l%E1%BA%A1i"
        )
        assert r.status_code == 200
        assert 'id="m08-body"' in r.text
        assert "Khách hẹn gọi lại" in r.text

    def test_no_prefill_body_leaves_textarea_empty(self):
        client = _build_m08_app()
        r = client.get("/modals/m08?party_id=party-1&mode=log")
        assert r.status_code == 200
        # Empty textarea: opening tag immediately followed by closing tag (no stray text).
        assert '>{{ prefill_body }}</textarea>' not in r.text  # sanity: not a raw unrendered var
        idx = r.text.index('id="m08-body"')
        snippet = r.text[idx:idx + 400]
        assert "></textarea>" in snippet or ">\n" in snippet


class TestIrritationReasonLabel:
    def test_reason_pill_label_is_tac_dung_phu(self):
        """Label shown to staff is 'Tác dụng phụ', not the old 'Kích ứng/không hợp da'."""
        client = _build_m08_app()
        r = client.get("/modals/m08?party_id=party-1&mode=log")
        assert r.status_code == 200
        assert "l:'Tác dụng phụ'" in r.text
        assert "Kích ứng" not in r.text

    def test_irritation_enum_value_unchanged(self):
        """Data-compat: the underlying enum value staff picks must stay 'irritation'."""
        client = _build_m08_app()
        r = client.get("/modals/m08?party_id=party-1&mode=log")
        assert "v:'irritation'" in r.text

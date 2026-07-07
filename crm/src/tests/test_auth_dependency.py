"""Tests for require_admin (crm/src/adapters/inbound/http/auth_dependency.py):
CF Access admin-role gate on /settings routes.
"""
from __future__ import annotations

import pathlib
import sys
from unittest.mock import patch

_REPO_ROOT = str(pathlib.Path(__file__).parents[4])
_PYTHON_ROOT = str(pathlib.Path(__file__).parents[1])
for _p in (_REPO_ROOT, _PYTHON_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from crm.src.adapters.inbound.http.auth_dependency import require_admin
from crm.src.domain.entities.app_user import AppUser


def _user(role: str) -> AppUser:
    return AppUser(
        user_id="u1", email="a@b.com", full_name="A", role=role,
        is_active=True, created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )


def _build_app(current_user) -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def _inject_user(request, call_next):
        request.state.current_user = current_user
        return await call_next(request)

    @app.get("/settings")
    async def settings(_admin: None = Depends(require_admin)):
        return {"ok": True}

    return TestClient(app, raise_server_exceptions=False)


class TestRequireAdmin:
    def test_dev_bypass_when_audience_unset(self):
        with patch("config.cf_access_audience", return_value=""):
            client = _build_app(None)
            r = client.get("/settings")
            assert r.status_code == 200

    def test_forbidden_when_no_current_user(self):
        with patch("config.cf_access_audience", return_value="aud"):
            client = _build_app(None)
            r = client.get("/settings")
            assert r.status_code == 403

    def test_forbidden_when_role_not_admin(self):
        with patch("config.cf_access_audience", return_value="aud"):
            client = _build_app(_user("sales"))
            r = client.get("/settings")
            assert r.status_code == 403

    def test_allowed_when_role_is_admin(self):
        with patch("config.cf_access_audience", return_value="aud"):
            client = _build_app(_user("admin"))
            r = client.get("/settings")
            assert r.status_code == 200

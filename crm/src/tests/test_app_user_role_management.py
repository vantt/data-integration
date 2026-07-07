"""Tests for user role/active management routes in screen_mgmt_settings.py:
require_admin guard, role validation, self-demote/self-deactivate protection.
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

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from crm.src.adapters.inbound.web.screens.management.screen_mgmt_settings import make_settings_router
from crm.src.domain.entities.app_user import AppUser


def _user(user_id: str, role: str) -> AppUser:
    return AppUser(
        user_id=user_id, email=f"{user_id}@x.com", full_name=user_id, role=role,
        is_active=True, created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )


class _FakeAppUsersSvc:
    def __init__(self):
        self.updates: list = []

    def list_active(self):
        return []

    def update(self, user_id, **kwargs):
        self.updates.append((user_id, kwargs))


def _build_app(current_user, app_users_svc) -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def _inject_user(request, call_next):
        request.state.current_user = current_user
        return await call_next(request)

    templates = Jinja2Templates(directory=str(pathlib.Path(_PYTHON_ROOT) / "adapters/inbound/web/templates"))
    app.include_router(make_settings_router(templates, settings_svc=object(), app_users_svc=app_users_svc))
    return TestClient(app, raise_server_exceptions=False)


class TestUserRoleUpdate:
    def test_requires_admin(self):
        with patch("config.cf_access_audience", return_value="aud"):
            svc = _FakeAppUsersSvc()
            client = _build_app(_user("u1", "sales"), svc)
            r = client.patch("/settings/users/u2/role", data={"role": "manager"})
            assert r.status_code == 403
            assert svc.updates == []

    def test_invalid_role_rejected(self):
        with patch("config.cf_access_audience", return_value="aud"):
            svc = _FakeAppUsersSvc()
            client = _build_app(_user("admin1", "admin"), svc)
            r = client.patch("/settings/users/u2/role", data={"role": "superuser"})
            assert r.status_code == 400
            assert svc.updates == []

    def test_admin_can_change_other_user_role(self):
        with patch("config.cf_access_audience", return_value="aud"):
            svc = _FakeAppUsersSvc()
            client = _build_app(_user("admin1", "admin"), svc)
            r = client.patch("/settings/users/u2/role", data={"role": "manager"})
            assert r.status_code == 200
            assert svc.updates == [("u2", {"role": "manager"})]

    def test_admin_cannot_demote_self(self):
        with patch("config.cf_access_audience", return_value="aud"):
            svc = _FakeAppUsersSvc()
            client = _build_app(_user("admin1", "admin"), svc)
            r = client.patch("/settings/users/admin1/role", data={"role": "sales"})
            assert r.status_code == 400
            assert svc.updates == []


class TestUserActiveUpdate:
    def test_admin_can_deactivate_other_user(self):
        with patch("config.cf_access_audience", return_value="aud"):
            svc = _FakeAppUsersSvc()
            client = _build_app(_user("admin1", "admin"), svc)
            r = client.patch("/settings/users/u2/active", data={"is_active": "false"})
            assert r.status_code == 200
            assert svc.updates == [("u2", {"is_active": False})]

    def test_admin_cannot_deactivate_self(self):
        with patch("config.cf_access_audience", return_value="aud"):
            svc = _FakeAppUsersSvc()
            client = _build_app(_user("admin1", "admin"), svc)
            r = client.patch("/settings/users/admin1/active", data={"is_active": "false"})
            assert r.status_code == 400
            assert svc.updates == []

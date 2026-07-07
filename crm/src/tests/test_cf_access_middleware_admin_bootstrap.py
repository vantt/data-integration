"""Tests for CFAccessMiddleware admin bootstrap (CRM_ADMIN_EMAILS):
first-login-only elevation via _compute_initial_role, no auto re-elevation.
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

from crm.src.adapters.inbound.http.cf_access_middleware import CFAccessMiddleware


class _FakeUserSvc:
    def __init__(self, registered_emails=()):
        self._registered = {e.lower() for e in registered_emails}

    def is_registered(self, email: str) -> bool:
        return email.lower() in self._registered


def _dummy_app(scope, receive, send):  # pragma: no cover — never invoked in these tests
    raise NotImplementedError


_MW = "crm.src.adapters.inbound.http.cf_access_middleware"


def _build_middleware(user_svc, admin_emails=(), role_map=None):
    # cf_access_middleware imports these via `from config import ...` at module
    # load time, so the patch target must be the bound name in THIS module
    # (patching "config.xxx" would miss the already-bound reference).
    with patch(f"{_MW}.cf_access_audience", return_value="aud"), \
         patch(f"{_MW}.cf_team_domain", return_value="team.cloudflareaccess.com"), \
         patch(f"{_MW}.cf_dept_claim", return_value="custom.departments"), \
         patch(f"{_MW}.cf_func_role_claim", return_value="custom.functional_roles"), \
         patch(f"{_MW}.cf_role_map", return_value=role_map or {}), \
         patch(f"{_MW}.cf_manager_prefixes", return_value=("truong-phong-", "head-of-")), \
         patch(f"{_MW}.cf_admin_emails", return_value=set(admin_emails)):
        return CFAccessMiddleware(_dummy_app, user_svc=user_svc)


class TestAdminBootstrap:
    def test_new_admin_email_bootstraps_as_admin(self):
        mw = _build_middleware(_FakeUserSvc(), admin_emails={"boss@fgorg.vn"})
        assert mw._compute_initial_role("boss@fgorg.vn", []) == "admin"

    def test_existing_user_not_auto_elevated(self):
        mw = _build_middleware(
            _FakeUserSvc(registered_emails={"boss@fgorg.vn"}), admin_emails={"boss@fgorg.vn"}
        )
        assert mw._compute_initial_role("boss@fgorg.vn", []) == "sales"

    def test_non_admin_email_uses_claim_role_map(self):
        mw = _build_middleware(_FakeUserSvc(), admin_emails=set(), role_map={"Managers": "manager"})
        assert mw._compute_initial_role("someone@fgorg.vn", ["Managers"]) == "manager"

    def test_admin_email_wins_over_claim_map_on_first_login(self):
        mw = _build_middleware(_FakeUserSvc(), admin_emails={"boss@fgorg.vn"}, role_map={"Sales": "sales"})
        assert mw._compute_initial_role("boss@fgorg.vn", ["Sales"]) == "admin"

    def test_email_match_is_case_insensitive(self):
        mw = _build_middleware(_FakeUserSvc(), admin_emails={"boss@fgorg.vn"})
        assert mw._compute_initial_role("Boss@FGorg.vn", []) == "admin"

"""Tenant settings: env override, tenant config value, fail closed when missing."""
from __future__ import annotations

import pytest
import yaml

from orchestration import tenants
from orchestration.tenants.fine_japan import config as fine_japan

CRM_KEYS = ("CRM_REFRESH_URL", "CRM_BACKUP_URL", "CRM_DRILL_URL", "APPROACH_SCRIPT_LOAD_URL")


@pytest.fixture
def no_env(monkeypatch):
    for key in CRM_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def enabled_tenants(tmp_path, monkeypatch):
    def write(ids):
        path = tmp_path / "modules.yaml"
        path.write_text(yaml.safe_dump({"connectors": [], "packs": [], "tenants": ids}))
        monkeypatch.setattr(tenants, "_MODULES_FILE", path)
    return write


def test_fine_japan_is_the_enabled_tenant():
    assert tenants.enabled_ids() == ["fine_japan"]


def test_value_comes_from_tenant_config(no_env):
    assert tenants.setting("CRM_REFRESH_URL") == "http://crm:8090/admin/refresh"
    assert tenants.setting("APPROACH_SCRIPT_LOAD_URL") == fine_japan.APPROACH_SCRIPT_LOAD_URL


def test_env_var_overrides_even_when_empty(no_env, monkeypatch):
    monkeypatch.setenv("CRM_REFRESH_URL", "http://example.invalid/refresh")
    monkeypatch.setenv("CRM_BACKUP_URL", "")
    assert tenants.setting("CRM_REFRESH_URL") == "http://example.invalid/refresh"
    assert tenants.setting("CRM_BACKUP_URL") == ""


def test_missing_value_fails_closed(no_env, monkeypatch):
    monkeypatch.delattr(fine_japan, "CRM_DRILL_URL")
    with pytest.raises(tenants.TenantConfigError, match="CRM_DRILL_URL"):
        tenants.setting("CRM_DRILL_URL")


def test_sheet_urls_are_not_tenant_settings(no_env):
    """Each Google Sheet URL is declared once, in SOURCES__SPREADSHEET_URL__<NAME>."""
    assert not [name for name in vars(fine_japan) if "SHEET" in name]


def test_no_enabled_tenant_fails_closed(no_env, enabled_tenants):
    enabled_tenants([])
    for key in CRM_KEYS:
        with pytest.raises(tenants.TenantConfigError, match="enabled: none"):
            tenants.setting(key)


def test_unknown_tenant_fails_loudly(no_env, enabled_tenants):
    enabled_tenants(["no_such_tenant"])
    with pytest.raises(ModuleNotFoundError):
        tenants.setting("CRM_REFRESH_URL")

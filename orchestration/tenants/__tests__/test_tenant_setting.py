"""Tenant settings: env override, tenant config value, fail closed when missing."""
from __future__ import annotations

import pytest
import yaml

from orchestration import tenants
from orchestration.sensors import sheets_modified_sensor
from orchestration.tenants.fine_japan import config as fine_japan

SHEET_KEYS = ("SHEETS_SENSOR_TARGETS_URL", "SHEETS_SENSOR_MARKETING_URL", "SHEETS_SENSOR_US_SHIPMENT_PRICES_URL")
CRM_KEYS = ("CRM_REFRESH_URL", "CRM_BACKUP_URL", "CRM_DRILL_URL", "APPROACH_SCRIPT_LOAD_URL")


@pytest.fixture
def no_env(monkeypatch):
    for key in (*SHEET_KEYS, *CRM_KEYS):
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
    assert sheets_modified_sensor.sheet_urls() == {
        "targets": fine_japan.SHEETS_SENSOR_TARGETS_URL,
        "marketing_spend": fine_japan.SHEETS_SENSOR_MARKETING_URL,
        "us_shipment_prices": fine_japan.SHEETS_SENSOR_US_SHIPMENT_PRICES_URL,
    }


def test_env_var_overrides_even_when_empty(no_env, monkeypatch):
    monkeypatch.setenv("SHEETS_SENSOR_TARGETS_URL", "https://example.invalid/sheet.csv")
    monkeypatch.setenv("CRM_BACKUP_URL", "")
    assert sheets_modified_sensor.sheet_urls()["targets"] == "https://example.invalid/sheet.csv"
    assert tenants.setting("CRM_BACKUP_URL") == ""


def test_missing_value_fails_closed(no_env, monkeypatch):
    monkeypatch.delattr(fine_japan, "SHEETS_SENSOR_MARKETING_URL")
    with pytest.raises(tenants.TenantConfigError, match="SHEETS_SENSOR_MARKETING_URL"):
        sheets_modified_sensor.sheet_urls()


def test_no_enabled_tenant_fails_closed(no_env, enabled_tenants):
    enabled_tenants([])
    for key in (*SHEET_KEYS, *CRM_KEYS):
        with pytest.raises(tenants.TenantConfigError, match="enabled: none"):
            tenants.setting(key)


def test_unknown_tenant_fails_loudly(no_env, enabled_tenants):
    enabled_tenants(["no_such_tenant"])
    with pytest.raises(ModuleNotFoundError):
        tenants.setting("CRM_REFRESH_URL")

"""ingest_sheets_modified_sensor polls the sheets configured by SOURCES__SPREADSHEET_URL__<NAME>
(the same variables the ingestion readers use) and fails closed when one is missing."""
from __future__ import annotations

import pytest
from dagster import build_sensor_context

from orchestration.sensors import sheets_modified_sensor as sensor_mod

ENV = {
    "TARGETS": "https://docs.example.com/spreadsheets/d/TARGETS_id-1/edit?usp=sharing",
    "MARKETING_SPEND": "https://docs.example.com/spreadsheets/d/MKT_id_2/edit#gid=0",
    "US_SHIPMENT_PRICES": "https://docs.example.com/spreadsheets/d/US_id3/edit?gid=304875363",
}


@pytest.fixture
def sheet_env(monkeypatch):
    for name, url in ENV.items():
        monkeypatch.setenv(f"SOURCES__SPREADSHEET_URL__{name}", url)
    return monkeypatch


def test_urls_come_from_the_reader_env_variables(sheet_env):
    assert sensor_mod.sheet_urls() == {
        "targets": "https://docs.example.com/spreadsheets/d/TARGETS_id-1/export?format=csv",
        "marketing_spend": "https://docs.example.com/spreadsheets/d/MKT_id_2/export?format=csv",
        "us_shipment_prices": "https://docs.example.com/spreadsheets/d/US_id3/export?format=csv&gid=304875363",
    }


def test_export_url_matches_the_former_tenant_value_shape():
    """An edit link of the same sheet yields the CSV export URL the sensor polled before."""
    edit = "https://docs.google.com/spreadsheets/d/AbC-123_x/edit?gid=304875363"
    assert sensor_mod.csv_export_url(edit, "304875363") == (
        "https://docs.google.com/spreadsheets/d/AbC-123_x/export?format=csv&gid=304875363"
    )
    assert sensor_mod.csv_export_url(edit.replace("?gid=304875363", "?usp=sharing"), None) == (
        "https://docs.google.com/spreadsheets/d/AbC-123_x/export?format=csv"
    )


@pytest.mark.parametrize("bad", ["not a url", "https://docs.example.com/document/d/x/edit", "/spreadsheets/d/x"])
def test_export_url_rejects_non_sheet_urls(bad):
    with pytest.raises(ValueError, match="not a Google Sheet URL"):
        sensor_mod.csv_export_url(bad, None)


@pytest.mark.parametrize("missing", list(ENV))
def test_missing_variable_fails_the_tick_with_its_name(sheet_env, missing):
    sheet_env.delenv(f"SOURCES__SPREADSHEET_URL__{missing}")
    with pytest.raises(RuntimeError, match=f"SOURCES__SPREADSHEET_URL__{missing} is not set"):
        sensor_mod.sheet_urls()
    # The sensor itself raises on evaluation (tick error); importing the module did not.
    with pytest.raises(RuntimeError, match=f"SOURCES__SPREADSHEET_URL__{missing}"):
        sensor_mod.ingest_sheets_modified_sensor(build_sensor_context())


def test_tick_polls_the_configured_urls(sheet_env, monkeypatch):
    polled = []
    monkeypatch.setattr(sensor_mod, "_fetch_sheet_hash", lambda url: polled.append(url) or "h")
    result = sensor_mod.ingest_sheets_modified_sensor(build_sensor_context())
    assert "Cold start" in str(result.skip_message)
    assert polled == list(sensor_mod.sheet_urls().values())

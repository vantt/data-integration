"""Google Sheet readers take their URL only from SOURCES__SPREADSHEET_URL__<NAME>: no default in
code, a clear error naming the variable when it is missing, and the configured URL when set.
The URL is resolved when the sheet is read, so importing a reader never fails on it (Dagster
imports every reader when it loads definitions).

Run:
  python -m pytest ingestion/tests/test_gsheet_sheet_urls.py -q
"""
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gsheet_auth  # noqa: E402 — same module object the readers import

# reader module -> (sheet name, fetch function, gsheet_auth function it reads the sheet with)
READERS = {
    "gsheet_targets": ("TARGETS", "fetch_and_save_targets", "fetch_tab_as_dataframe"),
    "gsheet_marketing_spend": ("MARKETING_SPEND", "fetch_and_save_marketing_spend", "fetch_tab_as_dataframe"),
    "gsheet_us_shipment_prices": ("US_SHIPMENT_PRICES", "fetch_and_save_us_shipment_prices", "fetch_tab_as_dataframe"),
    "gsheet_team_config": ("TEAM_CONFIG", "fetch_and_save_team_config", "fetch_workbook_tabs"),
    "gsheet_overhead_classification": ("OVERHEAD_CLASSIFICATION", "fetch_and_save_overhead_classification", "fetch_tab_as_dataframe"),
}


class _Fetched(Exception):
    """Stops the reader right after it asked for the sheet, before it writes anything."""


@pytest.fixture
def no_sheet_env(monkeypatch):
    for name in gsheet_auth.SPREADSHEET_NAMES:
        monkeypatch.delenv(gsheet_auth.SPREADSHEET_URL_ENV_PREFIX + name, raising=False)
    return monkeypatch


def test_every_reader_is_covered():
    assert sorted(n for n, *_ in READERS.values()) == sorted(set(gsheet_auth.SPREADSHEET_NAMES) - {"BUDGET"})


@pytest.mark.parametrize("value", [None, "", "   "])
def test_spreadsheet_url_missing_or_empty_is_an_error(no_sheet_env, value):
    if value is not None:
        no_sheet_env.setenv("SOURCES__SPREADSHEET_URL__TARGETS", value)
    with pytest.raises(gsheet_auth.SpreadsheetUrlNotConfigured, match="SOURCES__SPREADSHEET_URL__TARGETS is not set"):
        gsheet_auth.spreadsheet_url("TARGETS")


def test_spreadsheet_url_returns_the_env_value(no_sheet_env):
    no_sheet_env.setenv("SOURCES__SPREADSHEET_URL__BUDGET", "https://example.invalid/spreadsheets/d/b/edit")
    assert gsheet_auth.spreadsheet_url("BUDGET") == "https://example.invalid/spreadsheets/d/b/edit"


def test_spreadsheet_url_rejects_unknown_names():
    with pytest.raises(ValueError, match="unknown spreadsheet"):
        gsheet_auth.spreadsheet_url("NOPE")


@pytest.mark.parametrize("module_name", list(READERS))
def test_reader_without_variable_fails_with_its_name(no_sheet_env, module_name):
    name, fetch_fn, api_fn = READERS[module_name]
    reader = importlib.import_module(module_name)  # import must not need the URL
    called = []
    no_sheet_env.setattr(reader.gsheet_auth, api_fn, lambda *a, **k: called.append(a))
    with pytest.raises(gsheet_auth.SpreadsheetUrlNotConfigured, match=f"SOURCES__SPREADSHEET_URL__{name}"):
        getattr(reader, fetch_fn)()
    assert called == []  # no request to any sheet


@pytest.mark.parametrize("module_name", list(READERS))
def test_reader_uses_the_configured_url(no_sheet_env, module_name):
    name, fetch_fn, api_fn = READERS[module_name]
    reader = importlib.import_module(module_name)
    url = f"https://example.invalid/spreadsheets/d/{name.lower()}/edit"
    no_sheet_env.setenv(f"SOURCES__SPREADSHEET_URL__{name}", url)
    seen = []

    def fake(sheet_url, *a, **k):
        seen.append(sheet_url)
        raise _Fetched

    no_sheet_env.setattr(reader.gsheet_auth, api_fn, fake)
    with pytest.raises(_Fetched):
        getattr(reader, fetch_fn)()
    assert seen == [url]


def test_no_reader_carries_a_sheet_url():
    src = os.path.join(os.path.dirname(__file__), "..", "src")
    paths = [os.path.join(src, f"{m}.py") for m in READERS]
    budget = os.path.join(src, "gsheet_budget_sync")
    paths += [os.path.join(budget, f) for f in os.listdir(budget) if f.endswith(".py")]
    offenders = [p for p in paths if "docs.google.com" in open(p, encoding="utf-8").read()]
    assert offenders == []

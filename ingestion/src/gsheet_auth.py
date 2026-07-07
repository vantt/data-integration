"""Centralized Google Sheets service-account auth + fetch helper.

Single source of the `gspread` client, shared by the 5 read-only gsheet_* readers
and gsheet_budget_sync's write-back — replaces per-reader public-link CSV/xlsx export
with authenticated API access. See
plans/260707-1201-google-sheets-service-account/phase-01-service-account-setup.md.
"""

import os

import pandas as pd

GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH_ENV = "GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH"


def get_gspread_client():
    """Authenticated gspread client. Raises RuntimeError with setup instructions if
    the key path env var is unset/missing, or if gspread isn't installed — mirrors the
    existing lazy-import pattern in gsheet_budget_sync/sheet_writeback.py so module import
    always succeeds regardless of GCP setup state."""
    key_path = os.environ.get(GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH_ENV, "").strip()
    if not key_path:
        raise RuntimeError(
            f"{GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH_ENV} chưa được cấu hình — xem "
            f"plans/260707-1201-google-sheets-service-account/phase-01-service-account-setup.md"
        )
    if not os.path.exists(key_path):
        raise RuntimeError(f"Service account key không tồn tại tại {key_path}")
    import gspread

    return gspread.service_account(filename=key_path)


def fetch_tab_as_dataframe(sheet_url: str, gid: str) -> pd.DataFrame:
    """One worksheet (by gid) -> raw all-string DataFrame, header=None (row 0 = header
    row as data), matching the shape gsheet_budget_sync.fetch._fetch_tab_csv already
    returns — so callers that expect that raw-grid shape need zero downstream changes."""
    gc = get_gspread_client()
    sh = gc.open_by_url(sheet_url)
    ws = sh.get_worksheet_by_id(int(gid))
    values = ws.get_all_values()
    return pd.DataFrame(values)


def fetch_workbook_tabs(sheet_url: str) -> dict:
    """All tabs by name -> {tab_name: DataFrame with row 0 as column headers}. For
    multi-tab-by-name readers (team_config), replacing pd.read_excel(sheet_name=name)."""
    gc = get_gspread_client()
    sh = gc.open_by_url(sheet_url)
    result = {}
    for ws in sh.worksheets():
        values = ws.get_all_values()
        if not values:
            continue
        header, *rows = values
        result[ws.title] = pd.DataFrame(rows, columns=header)
    return result

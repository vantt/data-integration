"""Fetch Google Sheet tabs as raw CSV DataFrames + shared parse/format helpers used
across the gsheet_budget_sync package (budget_transform, policy_transform, merge,
suggestions).

Sheet layout is documented in scripts/budget/validate-budget-sheet.gs (source of truth
for column positions — BI_COL/AP_COL in budget_transform.py / policy_transform.py mirror
it 1:1, just 0-indexed).

Tabs (single spreadsheet, 3 gids):
  BUDGET_ITEMS      gid=0          — finance enters monthly planned amounts
  ALLOCATION_POLICY gid=1662021004 — quarterly waterfall config
  __REF (hidden)    gid=2061002942 — valid recurring cashflow_line values (col B),
                                      col A = direction, populated from dim_gl_account

Environment:
  SOURCES__SPREADSHEET_URL__BUDGET   Google Sheet URL (optional, has a working default)
  GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH   Shared GCP service-account JSON key path — see
    plans/260707-1201-google-sheets-service-account/phase-01-service-account-setup.md.
"""
import os
from datetime import datetime, timezone, timedelta

import pandas as pd

from ingestion.src import gsheet_auth


def _load_dotenv_local():
    """Load environment variables from .env.local if it exists (for local dev)."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
    env_local = os.path.join(project_root, ".env.local")

    if os.path.exists(env_local):
        with open(env_local, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value


_load_dotenv_local()

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, "../../.."))
SEEDS_DIR = os.path.join(_PROJECT_ROOT, "transformation", "seeds")

_DEFAULT_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/15hba6bzrTRXUDXBeUg5_DhefrETX9kLGG8SnPJZzTfA/edit"
)
SHEET_URL = os.environ.get("SOURCES__SPREADSHEET_URL__BUDGET", _DEFAULT_SHEET_URL)

# gids — 3 tabs in the one spreadsheet (see module docstring)
GID_BUDGET_ITEMS = "0"
GID_ALLOCATION_POLICY = "1662021004"
GID_REF = "2061002942"

_ICT = timezone(timedelta(hours=7))  # Asia/Ho_Chi_Minh, no DST — matches definitions.py convention


class ValidationError(Exception):
    """Raised on any validation failure. Caller must not write seeds when this is raised."""


def _fetch_tab_csv(sheet_url: str, gid: str, tab_name: str) -> pd.DataFrame:
    """Fetch one tab via the shared Sheets-API service account. Returns a raw
    (header=None, all-string) DataFrame — same shape the old public-CSV-export path
    returned, so budget_transform/policy_transform/merge/suggestions need zero changes.
    """
    try:
        df = gsheet_auth.fetch_tab_as_dataframe(sheet_url, gid)
    except Exception as e:
        raise ValidationError(f"Không tải được tab {tab_name} ({sheet_url}, gid={gid}): {e}")

    df = df.fillna("")
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise ValidationError(f"Tab {tab_name}: sheet rỗng — abort, không đè seed cũ")
    return df


def _parse_vnd(raw) -> float | None:
    """Strip VND currency formatting ('6,000,000 ₫') and parse as float.

    Also strips a trailing '%' — Google Sheets' CSV export renders Percent-formatted
    cells as display text (e.g. raw 0.2 -> '20%'), so pct_remaining values arrive here
    with the sign baked into the export text, not just Sheets UI display.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() == "nan":
        return None
    s = s.replace("₫", "").replace("%", "").replace(",", "").replace("\xa0", "").replace(" ", "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _fmt_num(v) -> str:
    """Format a parsed numeric value for CSV output — int-looking when it's a whole number."""
    if v is None:
        return ""
    try:
        f = float(v)
    except (ValueError, TypeError):
        return ""
    return str(int(f)) if f.is_integer() else str(f)


def _current_month_start(now: datetime | None = None) -> str:
    now = now or datetime.now(_ICT)
    return now.strftime("%Y-%m-01")


def load_ref_lines(ref_raw: pd.DataFrame) -> set[str]:
    """__REF col B = cashflow_line, trimmed. __REF has real trailing-space rows in prod."""
    if ref_raw.shape[1] < 2:
        raise ValidationError("__REF tab structure invalid: cần tối thiểu 2 cột (A=Chiều, B=Dòng Tiền)")
    col_b = ref_raw[1].astype(str).str.strip()
    return {v for v in col_b if v}

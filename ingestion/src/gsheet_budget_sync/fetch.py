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
"""
import os
import io
from datetime import datetime, timezone, timedelta

import requests
import pandas as pd


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

_HTTP_TIMEOUT = 30
_ICT = timezone(timedelta(hours=7))  # Asia/Ho_Chi_Minh, no DST — matches definitions.py convention


class ValidationError(Exception):
    """Raised on any validation failure. Caller must not write seeds when this is raised."""


def _get_csv_url(sheet_url: str, gid: str) -> str:
    base = sheet_url.split("/edit")[0].split("/view")[0]
    return f"{base}/export?format=csv&gid={gid}"


def _fetch_tab_csv(sheet_url: str, gid: str, tab_name: str) -> pd.DataFrame:
    """Download one tab as CSV and return a raw (header=None, all-string) DataFrame."""
    url = _get_csv_url(sheet_url, gid)
    try:
        resp = requests.get(url, timeout=_HTTP_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        raise ValidationError(f"Không tải được tab {tab_name} ({url}): {e}")

    content = resp.content.decode("utf-8", errors="replace")
    if content[:200].strip().lower().startswith("<html"):
        raise ValidationError(
            f"Tab {tab_name}: server trả về HTML thay vì CSV — kiểm tra quyền chia sẻ sheet "
            f"hoặc gid ({gid}) có đúng không"
        )

    try:
        df = pd.read_csv(io.StringIO(content), header=None, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        raise ValidationError(f"Tab {tab_name}: sheet rỗng — abort, không đè seed cũ")

    df = df.fillna("")
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise ValidationError(f"Tab {tab_name}: sheet rỗng — abort, không đè seed cũ")
    return df


def _parse_vnd(raw) -> float | None:
    """Strip VND currency formatting ('6,000,000 ₫') and parse as float."""
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "" or s.lower() == "nan":
        return None
    s = s.replace("₫", "").replace(",", "").replace("\xa0", "").replace(" ", "").strip()
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

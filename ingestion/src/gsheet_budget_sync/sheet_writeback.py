"""A1-cell targeting helpers + the credentialed Google Sheets API write path for the
"Gợi Ý" write-back (Phase 5).

HARD EXTERNAL BLOCKER — writing needs Editor access to the live Google Sheet, a materially
higher privilege than every other gsheet_*.py script in this repo (all read-only via public
CSV export). No Google service-account/OAuth credential exists in this repo yet. A human must,
OUTSIDE this repo:
  1. Create a GCP project (or reuse one) and enable the Google Sheets API.
  2. Create a service account, generate + download a JSON key.
  3. Share the budget Google Sheet with the service account's email as EDITOR.
  4. Place the JSON key file somewhere readable by the data_platform container and set
     GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH to its path.
  5. Rebuild the data_platform image so `gspread` (already in requirements.txt) is installed —
     the import below is deferred/lazy specifically so code-load works BEFORE this step too.
Until these steps are done, the orchestration in __init__.py's write_suggestions_to_sheet works
fully in --dry-run (prints the exact cells + values it would write, no network call to Sheets
API) but _write_cells_via_sheets_api raises a clear RuntimeError if invoked for a real write.
"""
import os

from .fetch import GID_BUDGET_ITEMS, SHEET_URL, _fmt_num
from .suggestions import _assert_gio_column

GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH_ENV = "GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH"


def _col_num_to_a1(col_idx_0based: int) -> str:
    """0-indexed column -> A1 letter(s) (0->A, 6->G, 25->Z, 26->AA, ...)."""
    n = col_idx_0based + 1
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _to_a1_cell(sheet_row_1based: int, col_idx_0based: int) -> str:
    return f"{_col_num_to_a1(col_idx_0based)}{sheet_row_1based}"


def _fmt_suggestion_value(v) -> str:
    """Format a suggestion value the same way Budget values are formatted in the seed."""
    return _fmt_num(v)


def _write_cells_via_sheets_api(writes: list):
    """The ONLY function in this module that requires real Google credentials. Isolated
    deliberately: everything upstream (fetch/compute/target) works with zero credentials,
    so module import and --dry-run always succeed regardless of GCP setup state.
    """
    key_path = os.environ.get(GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH_ENV, "").strip()
    if not key_path:
        raise RuntimeError(
            f"{GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH_ENV} chưa được cấu hình — cần tạo GCP "
            f"service account, share sheet quyền Editor, và set biến môi trường này trỏ tới "
            f"file JSON key. Xem docstring đầu module sheet_writeback.py để biết chi tiết setup."
        )
    if not os.path.exists(key_path):
        raise RuntimeError(f"Service account key không tồn tại tại {key_path}")

    try:
        import gspread
    except ImportError as e:
        raise RuntimeError(
            "Thư viện 'gspread' chưa được cài trong container — thêm vào "
            "ingestion/requirements.txt (đã có sẵn) và rebuild "
            f"(docker compose build data_platform). Lỗi gốc: {e}"
        )

    for w in writes:
        _assert_gio_column(w["col"])

    gc = gspread.service_account(filename=key_path)
    sh = gc.open_by_url(SHEET_URL)
    ws = sh.get_worksheet_by_id(int(GID_BUDGET_ITEMS))

    cell_updates = [
        {"range": _to_a1_cell(w["sheet_row"], w["col"]), "values": [[_fmt_suggestion_value(w["value"])]]}
        for w in writes
    ]
    ws.batch_update(cell_updates)

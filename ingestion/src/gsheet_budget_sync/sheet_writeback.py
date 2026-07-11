"""A1-cell targeting helpers + the credentialed Google Sheets API write path for the
"Gợi Ý" write-back (Phase 5).

Writing needs Editor access to the live Google Sheet — a materially higher privilege than
the other gsheet_*.py readers (Viewer). Credential is the shared service account set up in
plans/260707-1201-google-sheets-service-account/phase-01-service-account-setup.md — same
GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH env var and gsheet_auth.get_gspread_client() helper
used by every other gsheet_*.py reader, just with Editor (not Viewer) share on this one sheet.
"""
from ingestion.src import gsheet_auth

from .fetch import GID_BUDGET_ITEMS, GID_REF, SHEET_URL, _fmt_num
from .suggestions import _assert_gio_column

# Generous fixed upper bound for the __REF clear range (phase-02) — the dropdown list is
# expected to stay ~50-80 rows; clearing well past any plausible size before each write means
# a shorter run never leaves stale rows below the fresh data (__REF has no header row, and
# scripts/budget/validate-budget-sheet.gs reads it via getLastRow(), so leftover rows would
# otherwise silently stay selectable).
_REF_CLEAR_ROWS = 1000


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
    for w in writes:
        _assert_gio_column(w["col"])

    gc = gsheet_auth.get_gspread_client()
    sh = gc.open_by_url(SHEET_URL)
    ws = sh.get_worksheet_by_id(int(GID_BUDGET_ITEMS))

    cell_updates = [
        {"range": _to_a1_cell(w["sheet_row"], w["col"]), "values": [[_fmt_suggestion_value(w["value"])]]}
        for w in writes
    ]
    ws.batch_update(cell_updates)


def _write_ref_accounts(rows: list):
    """Full overwrite of __REF cols A:B (direction, label) with freshly generated account-based
    dropdown rows — see plans/260709-1415-budget-account-level-remap/phase-02-sheet-ref-
    dropdown-writeback.md. Drops any pre-existing content in A:B (including legacy hand-
    maintained cashflow_line rows) — accepted migration consequence, decided 2026-07-11.
    Only cols A/B are touched (never C onward), per the phase's own risk note.

    Writes the fresh rows FIRST, then clears only the trailing rows beyond them — not
    clear-then-write. batch_clear/update are 2 separate non-atomic Sheets API calls; if the
    write step failed after an upfront clear, __REF would be left completely empty (dropdown
    + .gs cha/con cross-row validation both silently lose all options) until the next
    successful run. Writing first means a failure in the trailing-clear step leaves __REF
    at-worst-stale, never empty.
    """
    gc = gsheet_auth.get_gspread_client()
    sh = gc.open_by_url(SHEET_URL)
    ws = sh.get_worksheet_by_id(int(GID_REF))

    if rows:
        ws.update(f"A1:B{len(rows)}", [[direction, label] for direction, label in rows])
    ws.batch_clear([f"A{len(rows) + 1}:B{_REF_CLEAR_ROWS}"])

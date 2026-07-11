"""Build the __REF tab's account-based dropdown rows (Phase 2,
plans/260709-1415-budget-account-level-remap/phase-02-sheet-ref-dropdown-writeback.md).

Pure targeting logic — no I/O. See duckdb_actuals._fetch_ref_accounts_from_duckdb for the
DuckDB read that feeds `accounts` below, and sheet_writeback._write_ref_accounts for the
credentialed Sheets API write path.
"""
_DIRECTION_VN = {"inflow": "Thu", "outflow": "Chi"}


def build_ref_rows(accounts: list) -> list:
    """accounts: [{'account_code','direction','account_name','parent_account_code',
    'parent_account_name'}, ...] — one entry per (offset_account, direction) pair actually
    observed in fact_cash_movement (see duckdb_actuals._fetch_ref_accounts_from_duckdb).

    Emits 2 selectable rows per account when it has a real parent — the child itself (Chế độ
    B: budget per sub-account) and its nearest real ancestor (Chế độ A: budget the whole family
    at once) — both under the SAME direction the child was actually observed with. Dedupes
    accounts/parents shared by multiple ledger lines, then fixed-width right-justifies every
    account_code to the widest code in the whole list (not just its own row) so the padding is
    consistent across the dropdown — see plan.md §Khó khăn #2 (dropdown-only, never typed, so
    Sheets never auto-trims the leading spaces).

    Returns [(direction_vn, label), ...] sorted by (direction, label) — label's fixed-width
    prefix means text sort already matches numeric account_code order.
    """
    selectable = {}  # (account_code, direction_vn) -> display name
    for a in accounts:
        direction_vn = _DIRECTION_VN[a["direction"]]
        selectable[(a["account_code"], direction_vn)] = a["account_name"]
        if a.get("parent_account_code"):
            selectable[(a["parent_account_code"], direction_vn)] = a["parent_account_name"]

    if not selectable:
        return []

    width = max(len(code) for code, _direction in selectable)
    rows = [
        (direction_vn, f"{code.rjust(width)}  {name}")
        for (code, direction_vn), name in selectable.items()
    ]
    rows.sort()
    return rows

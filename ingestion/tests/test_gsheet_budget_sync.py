"""Unit tests for gsheet_budget_sync transform/validation logic.

Covers acceptance criteria from
plans/260705-1459-budget-cashflow-workable-loop/phase-01-sheet-to-seed-sync.md:
  - all 3 item_types transform correctly (recurring / one_off / reserve)
  - empty/zero budget cells emit no row
  - Thu/Chi -> inflow/outflow mapping
  - section-header rows + "Type present, name blank" junk rows are skipped
  - __REF trailing-whitespace is trimmed before matching
  - reject cases: recurring line not in __REF, policy gap/overlap, missing remainder
  - historical merge preserves rows before the current month, replaces current+future
"""
import io
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import gsheet_budget_sync as sync  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _raw_df(csv_text: str) -> pd.DataFrame:
    """Parse a raw CSV block the same way _fetch_tab_csv does (header=None, all-string)."""
    df = pd.read_csv(io.StringIO(csv_text), header=None, dtype=str, keep_default_na=False)
    return df.fillna("")


BUDGET_CSV = """\
,,,,,,2026-07,,2026-08,
Dòng Tiền,Chiều,Type,Tháng Cần,Tuần TT,Tổng Cần,Gợi Ý,Budget,Gợi Ý,Budget
,THU,,,,,,,,
Bán hàng & phải thu KH,Thu,recurring,,,,,"480,000,000 ₫",,"480,000,000 ₫"
,Thu,recurring,,,,,,,
Chi lương,Chi,recurring,,,1,,"240,000,000 ₫",,
Quỹ Phúc Lợi Nhân Viên,Chi,reserve,,,,,"6,000,000 ₫",,
Mua SSD,Chi,one_off,,,"6,000,000 ₫",,,,
Dòng Zero,Chi,recurring,,,,,0,,
"""

REF_CSV = """\
Thu,Bán hàng & phải thu KH
Chi,Chi lương
Chi,Dòng Zero
Chi,Dòng Trailing Space \
"""


def _budget_and_months():
    return sync.parse_budget_matrix(_raw_df(BUDGET_CSV))


# ---------------------------------------------------------------------------
# parse_budget_matrix
# ---------------------------------------------------------------------------

def test_parse_budget_matrix_skips_section_header_and_blank_name_rows():
    months, items, warnings = _budget_and_months()

    assert months == [(6, "2026-07-01"), (8, "2026-08-01")]
    # 5 real item rows kept: Bán hàng, Chi lương, Quỹ Phúc Lợi, Mua SSD, Dòng Zero
    # (section header row + blank-name junk row are skipped)
    labels = [it["cashflow_line"] for it in items]
    assert labels == ["Bán hàng & phải thu KH", "Chi lương", "Quỹ Phúc Lợi Nhân Viên", "Mua SSD", "Dòng Zero"]
    assert len(warnings) == 1
    assert "trống" in warnings[0]


# ---------------------------------------------------------------------------
# validate_and_build_budget_rows — happy path, all 3 item_types
# ---------------------------------------------------------------------------

def test_transforms_all_three_item_types_and_thu_chi_mapping():
    months, items, _warnings = _budget_and_months()
    ref_lines = sync.load_ref_lines(_raw_df(REF_CSV))

    df, errors = sync.validate_and_build_budget_rows(items, ref_lines)

    assert errors == []
    by_line = {(r.cashflow_line, r.period_month): r for r in df.itertuples()}

    recurring = by_line[("Bán hàng & phải thu KH", "2026-07-01")]
    assert recurring.direction == "inflow"
    assert recurring.planned_amount == "480000000"
    assert recurring.item_type == "recurring"
    assert recurring.item_label == ""

    outflow_recurring = by_line[("Chi lương", "2026-07-01")]
    assert outflow_recurring.direction == "outflow"
    assert outflow_recurring.planned_amount == "240000000"

    reserve = by_line[("Quỹ Phúc Lợi Nhân Viên", "2026-07-01")]
    assert reserve.item_type == "reserve"
    assert reserve.item_label == "Quỹ Phúc Lợi Nhân Viên"  # one_off/reserve: item_label = cashflow_line

    # Mua SSD has item_target but no monthly Budget Tx cells filled -> no rows at all
    assert not any(r.cashflow_line == "Mua SSD" for r in df.itertuples())


def test_empty_and_zero_budget_cells_emit_no_row():
    months, items, _warnings = _budget_and_months()
    ref_lines = sync.load_ref_lines(_raw_df(REF_CSV))
    df, errors = sync.validate_and_build_budget_rows(items, ref_lines)

    assert errors == []
    # "Dòng Zero" 2026-07 cell = 0 -> no row; 2026-08 cell empty -> no row either
    assert not any(r.cashflow_line == "Dòng Zero" for r in df.itertuples())
    # Chi lương 2026-08 cell is empty in fixture -> no row for that month
    assert not any(
        r.cashflow_line == "Chi lương" and r.period_month == "2026-08-01"
        for r in df.itertuples()
    )


# ---------------------------------------------------------------------------
# __REF matching — trailing whitespace trim
# ---------------------------------------------------------------------------

def test_ref_trailing_whitespace_is_trimmed_before_matching():
    ref_lines = sync.load_ref_lines(_raw_df(REF_CSV))
    assert "Dòng Trailing Space" in ref_lines  # trailing space in source stripped on load


def test_recurring_line_not_in_ref_is_rejected():
    bad_csv = BUDGET_CSV.replace("Chi lương,Chi,recurring", "Chi Không Tồn Tại,Chi,recurring")
    months, items, _warnings = sync.parse_budget_matrix(_raw_df(bad_csv))
    ref_lines = sync.load_ref_lines(_raw_df(REF_CSV))

    df, errors = sync.validate_and_build_budget_rows(items, ref_lines)

    assert df is None
    assert any("Chi Không Tồn Tại" in e and "__REF" in e for e in errors)


def test_one_off_and_reserve_rows_never_checked_against_ref():
    # "Mua SSD" and "Quỹ Phúc Lợi Nhân Viên" are not in REF_CSV at all, yet must pass
    months, items, _warnings = _budget_and_months()
    ref_lines = sync.load_ref_lines(_raw_df(REF_CSV))
    df, errors = sync.validate_and_build_budget_rows(items, ref_lines)
    assert errors == []


# ---------------------------------------------------------------------------
# ALLOCATION_POLICY
# ---------------------------------------------------------------------------

POLICY_CSV_VALID = """\
Ưu Tiên,Bucket,Rule Type,Value,Effective From,Effective To
1,Chi Lương,from_plan,,2026-01-01,
2,Để dành mua SSD,fixed,"6,000,000 ₫",2026-01-01,
3,Tiền mặt tự do,remainder,,2026-01-01,
"""


def test_policy_valid_rows_transform_correctly():
    items, _warnings = sync.parse_policy_matrix(_raw_df(POLICY_CSV_VALID))
    df, errors = sync.validate_and_build_policy_rows(items)

    assert errors == []
    assert list(df["rule_type"]) == ["from_plan", "fixed", "remainder"]
    fixed_row = df[df["bucket"] == "Để dành mua SSD"].iloc[0]
    assert fixed_row["value"] == "6000000"


def test_policy_missing_remainder_row_is_rejected():
    csv_no_remainder = """\
Ưu Tiên,Bucket,Rule Type,Value,Effective From,Effective To
1,Chi Lương,from_plan,,2026-01-01,
2,Để dành mua SSD,fixed,"6,000,000 ₫",2026-01-01,
"""
    items, _warnings = sync.parse_policy_matrix(_raw_df(csv_no_remainder))
    df, errors = sync.validate_and_build_policy_rows(items)

    assert df is None
    assert any("remainder" in e for e in errors)


def test_policy_remainder_not_last_priority_is_rejected():
    csv_bad_order = """\
Ưu Tiên,Bucket,Rule Type,Value,Effective From,Effective To
1,Chi Lương,from_plan,,2026-01-01,
2,Tiền mặt tự do,remainder,,2026-01-01,
3,Để dành mua SSD,fixed,"6,000,000 ₫",2026-01-01,
"""
    items, _warnings = sync.parse_policy_matrix(_raw_df(csv_bad_order))
    df, errors = sync.validate_and_build_policy_rows(items)

    assert df is None
    assert any("priority cuối" in e for e in errors)


def test_policy_overlap_between_effective_ranges_is_rejected():
    csv_overlap = """\
Ưu Tiên,Bucket,Rule Type,Value,Effective From,Effective To
1,operating_reserve,fill_to_target,200000000,2026-01-01,2026-06-30
2,operating_reserve,fill_to_target,300000000,2026-06-01,
3,Tiền mặt tự do,remainder,,2026-01-01,
"""
    items, _warnings = sync.parse_policy_matrix(_raw_df(csv_overlap))
    df, errors = sync.validate_and_build_policy_rows(items)

    assert df is None
    assert any("OVERLAP" in e for e in errors)


def test_policy_gap_between_effective_ranges_is_rejected():
    csv_gap = """\
Ưu Tiên,Bucket,Rule Type,Value,Effective From,Effective To
1,operating_reserve,fill_to_target,200000000,2026-01-01,2026-03-31
2,operating_reserve,fill_to_target,300000000,2026-06-01,
3,Tiền mặt tự do,remainder,,2026-01-01,
"""
    items, _warnings = sync.parse_policy_matrix(_raw_df(csv_gap))
    df, errors = sync.validate_and_build_policy_rows(items)

    assert df is None
    assert any("GAP" in e for e in errors)


def test_policy_value_required_for_fixed_rule_type():
    csv_missing_value = """\
Ưu Tiên,Bucket,Rule Type,Value,Effective From,Effective To
1,Để dành mua SSD,fixed,,2026-01-01,
2,Tiền mặt tự do,remainder,,2026-01-01,
"""
    items, _warnings = sync.parse_policy_matrix(_raw_df(csv_missing_value))
    df, errors = sync.validate_and_build_policy_rows(items)

    assert df is None
    assert any("bắt buộc value" in e for e in errors)


def test_policy_empty_template_rows_are_skipped_silently():
    csv_with_padding = POLICY_CSV_VALID + "4,,,,,\n5,,,,,\n"
    items, warnings = sync.parse_policy_matrix(_raw_df(csv_with_padding))
    assert len(items) == 3  # padding rows (priority filled, bucket/rule_type blank) are dropped
    assert warnings == []


# ---------------------------------------------------------------------------
# Historical merge
# ---------------------------------------------------------------------------

def test_merge_historical_preserves_past_months_keeps_current_and_future(tmp_path):
    existing_path = tmp_path / "seed_cashflow_budget.csv"
    existing_path.write_text(
        "cashflow_line,period_month,direction,planned_amount,payment_week,item_type,item_label,item_target,target_month,notes\n"
        "Chi lương,2026-05-01,outflow,240000000,1,recurring,,,,\n"
        "Chi lương,2026-06-01,outflow,240000000,1,recurring,,,,Placeholder — update\n"
        "Chi lương,2026-07-01,outflow,999999999,1,recurring,,,,STALE — must be replaced\n",
        encoding="utf-8",
    )

    new_df = pd.DataFrame([{
        "cashflow_line": "Chi lương", "period_month": "2026-07-01", "direction": "outflow",
        "planned_amount": "240000000", "payment_week": "1", "item_type": "recurring",
        "item_label": "", "item_target": "", "target_month": "", "notes": "",
    }], columns=sync.SEED_BUDGET_COLUMNS)

    merged = sync.merge_historical_budget(str(existing_path), new_df, current_month_start="2026-07-01")

    rows = {r.period_month: r for r in merged.itertuples()}
    assert rows["2026-05-01"].planned_amount == "240000000"  # past month kept verbatim
    assert rows["2026-06-01"].notes == "Placeholder — update"  # past month notes preserved
    assert rows["2026-07-01"].planned_amount == "240000000"  # current month replaced by fresh pull
    assert rows["2026-07-01"].notes == ""  # stale note gone — row came from fresh data


def test_merge_historical_with_no_existing_seed_file(tmp_path):
    missing_path = tmp_path / "does_not_exist.csv"
    new_df = pd.DataFrame([{
        "cashflow_line": "Chi lương", "period_month": "2026-07-01", "direction": "outflow",
        "planned_amount": "240000000", "payment_week": "1", "item_type": "recurring",
        "item_label": "", "item_target": "", "target_month": "", "notes": "",
    }], columns=sync.SEED_BUDGET_COLUMNS)

    merged = sync.merge_historical_budget(str(missing_path), new_df, current_month_start="2026-07-01")
    assert len(merged) == 1


# ---------------------------------------------------------------------------
# Sheet-level abort cases (structural failures)
# ---------------------------------------------------------------------------

def test_fetch_tab_csv_rejects_html_response(monkeypatch):
    class _FakeResp:
        content = b"<HTML><BODY>Temporary Redirect</BODY></HTML>"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(sync.requests, "get", lambda *a, **k: _FakeResp())

    with pytest.raises(sync.ValidationError, match="HTML"):
        sync._fetch_tab_csv("https://example.com/edit", "0", "BUDGET_ITEMS")


def test_fetch_tab_csv_rejects_empty_sheet(monkeypatch):
    class _FakeResp:
        content = b""

        def raise_for_status(self):
            pass

    monkeypatch.setattr(sync.requests, "get", lambda *a, **k: _FakeResp())

    with pytest.raises(sync.ValidationError, match="rỗng"):
        sync._fetch_tab_csv("https://example.com/edit", "0", "BUDGET_ITEMS")


def test_full_sync_aborts_and_does_not_write_seed_on_validation_failure(monkeypatch, tmp_path):
    """End-to-end: a bad recurring line must abort before any seed file is written."""
    bad_csv = BUDGET_CSV.replace("Chi lương,Chi,recurring", "Chi Không Tồn Tại,Chi,recurring")

    budget_seed = tmp_path / "seed_cashflow_budget.csv"
    policy_seed = tmp_path / "seed_cash_allocation_policy.csv"
    budget_seed.write_text("cashflow_line,period_month,direction,planned_amount,payment_week,item_type,item_label,item_target,target_month,notes\nGOOD,2026-01-01,inflow,1,1,recurring,,,,\n", encoding="utf-8")
    policy_seed.write_text("priority,bucket,rule_type,value,effective_from,effective_to,notes\n1,x,remainder,,2026-01-01,,\n", encoding="utf-8")

    monkeypatch.setattr(sync, "SEEDS_DIR", str(tmp_path))

    def _fake_fetch(url, gid, tab_name):
        if tab_name == "BUDGET_ITEMS":
            return _raw_df(bad_csv)
        if tab_name == "ALLOCATION_POLICY":
            return _raw_df(POLICY_CSV_VALID)
        return _raw_df(REF_CSV)

    monkeypatch.setattr(sync, "_fetch_tab_csv", _fake_fetch)

    with pytest.raises(sync.ValidationError):
        sync.fetch_transform_and_save(dry_run=False)

    # Seeds must be untouched
    assert budget_seed.read_text(encoding="utf-8").count("\n") == 2
    assert "GOOD" in budget_seed.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 5 — suggestion computation ("Gợi Ý" write-back), all pure/mocked, no real
# network or Sheets API calls. Covers
# plans/260705-1459-budget-cashflow-workable-loop/phase-05-prefill-suggestions.md
# ---------------------------------------------------------------------------

def test_next_month_start_rolls_over_year():
    from datetime import datetime
    assert sync.next_month_start(datetime(2026, 7, 15)) == "2026-08-01"
    assert sync.next_month_start(datetime(2026, 12, 3)) == "2027-01-01"


def test_preceding_months_returns_oldest_first_and_handles_year_rollover():
    assert sync._preceding_months("2026-08-01") == ["2026-05-01", "2026-06-01", "2026-07-01"]
    assert sync._preceding_months("2026-02-01") == ["2025-11-01", "2025-12-01", "2026-01-01"]


def test_compute_recurring_suggestions_averages_over_full_window_not_present_count():
    # "Chi lương" outflow has actual in only 2 of the 3 window months -> still /3, not /2.
    rows = [
        {"cashflow_line": "Chi lương", "direction": "outflow", "amount": 240000000},
        {"cashflow_line": "Chi lương", "direction": "outflow", "amount": 240000000},
        {"cashflow_line": "Bán hàng & phải thu KH", "direction": "inflow", "amount": 480000000},
    ]
    result = sync.compute_recurring_suggestions(rows, window_size=3)
    assert result[("Chi lương", "outflow")] == 160000000.0  # 480M / 3, not / 2
    assert result[("Bán hàng & phải thu KH", "inflow")] == 160000000.0


def test_compute_reserve_suggestions_skips_null_required_monthly_adj():
    rows = [
        {"cashflow_line": "Quỹ Phúc Lợi Nhân Viên", "required_monthly_adj": 3000000},
        {"cashflow_line": "Deadline Đã Qua", "required_monthly_adj": None},
    ]
    result = sync.compute_reserve_suggestions(rows)
    assert result == {"Quỹ Phúc Lợi Nhân Viên": 3000000.0}


# --- build_suggestion_writes ------------------------------------------------

_SUGGESTION_MONTHS = [(6, "2026-07-01"), (8, "2026-08-01")]

_SUGGESTION_ITEMS = [
    {
        "sheet_row": 4, "cashflow_line": "Bán hàng & phải thu KH", "direction_raw": "Thu",
        "item_type": "recurring", "target_month_raw": "", "item_target_raw": "",
    },
    {
        "sheet_row": 5, "cashflow_line": "Chi lương", "direction_raw": "Chi",
        "item_type": "recurring", "target_month_raw": "", "item_target_raw": "",
    },
    {
        # reserve WITH deadline (item_target + target_month both set) -> required_monthly_adj
        "sheet_row": 6, "cashflow_line": "Quỹ Phúc Lợi Nhân Viên", "direction_raw": "Chi",
        "item_type": "reserve", "target_month_raw": "2026-12", "item_target_raw": "60,000,000 ₫",
    },
    {
        # reserve OPEN-ENDED (item_target set, no target_month) -> never write
        "sheet_row": 7, "cashflow_line": "Quỹ Dự Phòng Mở", "direction_raw": "Chi",
        "item_type": "reserve", "target_month_raw": "", "item_target_raw": "100,000,000 ₫",
    },
    {
        # one_off due IN the target month -> skip (finance enters manually)
        "sheet_row": 8, "cashflow_line": "Mua SSD", "direction_raw": "Chi",
        "item_type": "one_off", "target_month_raw": "2026-08", "item_target_raw": "6,000,000 ₫",
    },
    {
        # one_off due in a DIFFERENT month -> suggestion = 0
        "sheet_row": 9, "cashflow_line": "Mua Laptop", "direction_raw": "Chi",
        "item_type": "one_off", "target_month_raw": "2026-09", "item_target_raw": "20,000,000 ₫",
    },
]

_RECURRING_MAP = {
    ("Bán hàng & phải thu KH", "inflow"): 500000000.0,
    # "Chi lương" (outflow) deliberately absent -> no data available, must be skipped
}
_RESERVE_MAP = {"Quỹ Phúc Lợi Nhân Viên": 2000000.0}


def test_build_suggestion_writes_covers_all_item_type_branches():
    writes = sync.build_suggestion_writes(
        _SUGGESTION_ITEMS, _SUGGESTION_MONTHS, "2026-08-01", _RECURRING_MAP, _RESERVE_MAP
    )
    by_row = {w["sheet_row"]: w for w in writes}

    assert by_row[4]["value"] == 500000000.0  # recurring, has data
    assert 5 not in by_row  # recurring, no data in map -> skipped
    assert by_row[6]["value"] == 2000000.0  # reserve w/ deadline -> required_monthly_adj
    assert 7 not in by_row  # open-ended reserve -> never written
    assert 8 not in by_row  # one_off's own due month -> skipped (manual entry)
    assert by_row[9]["value"] == 0  # one_off, different month -> 0

    # Every write must target the "Gợi Ý" column (8), never the adjacent "Budget" column (9)
    assert all(w["col"] == 8 for w in writes)


def test_build_suggestion_writes_returns_empty_when_target_month_column_missing():
    writes = sync.build_suggestion_writes(
        _SUGGESTION_ITEMS, _SUGGESTION_MONTHS, "2026-09-01", _RECURRING_MAP, _RESERVE_MAP
    )
    assert writes == []


def test_assert_gio_column_rejects_the_budget_column():
    sync._assert_gio_column(6)  # G — a real "Gợi Ý" column — must not raise
    with pytest.raises(AssertionError):
        sync._assert_gio_column(7)  # H — the adjacent "Budget" column — must raise


# --- cell targeting helpers --------------------------------------------------

def test_col_num_to_a1_matches_sheet_layout():
    assert sync._col_num_to_a1(0) == "A"
    assert sync._col_num_to_a1(6) == "G"  # BI_COL_DATA_START, first "Gợi Ý" column
    assert sync._col_num_to_a1(25) == "Z"
    assert sync._col_num_to_a1(26) == "AA"


def test_to_a1_cell_combines_row_and_column():
    assert sync._to_a1_cell(6, 8) == "I6"


# --- write_suggestions_to_sheet (dry-run, fully mocked I/O) -----------------

def test_write_suggestions_dry_run_never_touches_budget_and_needs_no_credentials(monkeypatch):
    """End-to-end dry-run: fetch/parse/validate/compute all mocked or pure — proves the
    whole pipeline works with zero Google credentials and zero real DuckDB access.
    """
    budget_csv = """\
,,,,,,2026-07,,2026-08,
Dòng Tiền,Chiều,Type,Tháng Cần,Tuần TT,Tổng Cần,Gợi Ý,Budget,Gợi Ý,Budget
Bán hàng & phải thu KH,Thu,recurring,,,,,"480,000,000 ₫",,
Chi lương,Chi,recurring,,,1,,"240,000,000 ₫",,
Mua SSD,Chi,one_off,2026-09,,"6,000,000 ₫",,,,
"""

    def _fake_fetch(url, gid, tab_name):
        if tab_name == "BUDGET_ITEMS":
            return _raw_df(budget_csv)
        return _raw_df(REF_CSV)

    monkeypatch.setattr(sync, "_fetch_tab_csv", _fake_fetch)
    monkeypatch.setattr(
        sync, "_fetch_recurring_actuals_from_duckdb",
        lambda serving_db_path, window_months: [
            {"cashflow_line": "Bán hàng & phải thu KH", "direction": "inflow", "amount": 1500000000},
        ],
    )
    monkeypatch.setattr(sync, "_fetch_reserve_status_from_duckdb", lambda serving_db_path: [])

    called = {"sheets_api": False}

    def _fail_if_called(writes):
        called["sheets_api"] = True

    monkeypatch.setattr(sync, "_write_cells_via_sheets_api", _fail_if_called)

    n = sync.write_suggestions_to_sheet(target_month="2026-08-01", dry_run=True)

    assert n == 2  # Bán hàng (recurring, has data) + Mua SSD (one_off, different month -> 0)
    assert called["sheets_api"] is False  # dry-run must never call the write path


def test_write_suggestions_aborts_on_structural_validation_error(monkeypatch):
    bad_csv = """\
,,,,,,2026-08,
Dòng Tiền,Chiều,Type,Tháng Cần,Tuần TT,Tổng Cần,Gợi Ý,Budget
Chi Không Tồn Tại,Chi,recurring,,,,,"1,000 ₫"
"""

    def _fake_fetch(url, gid, tab_name):
        if tab_name == "BUDGET_ITEMS":
            return _raw_df(bad_csv)
        return _raw_df(REF_CSV)

    monkeypatch.setattr(sync, "_fetch_tab_csv", _fake_fetch)

    with pytest.raises(sync.ValidationError):
        sync.write_suggestions_to_sheet(target_month="2026-08-01", dry_run=True)


# --- _write_cells_via_sheets_api (credential/dependency guard rails) --------

def test_write_cells_via_sheets_api_requires_env_var(monkeypatch):
    monkeypatch.delenv(sync.GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH_ENV, raising=False)
    with pytest.raises(RuntimeError, match=sync.GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH_ENV):
        sync._write_cells_via_sheets_api([{"sheet_row": 4, "col": 6, "value": 1, "cashflow_line": "x", "item_type": "recurring"}])


def test_write_cells_via_sheets_api_requires_key_file_to_exist(monkeypatch, tmp_path):
    missing_key = tmp_path / "does_not_exist.json"
    monkeypatch.setenv(sync.GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH_ENV, str(missing_key))
    with pytest.raises(RuntimeError, match="không tồn tại"):
        sync._write_cells_via_sheets_api([{"sheet_row": 4, "col": 6, "value": 1, "cashflow_line": "x", "item_type": "recurring"}])

"""Parse + validate + build long-format rows for the BUDGET_ITEMS tab.

Column positions (0-indexed) mirror BI_COL in scripts/budget/validate-budget-sheet.gs.
Only "Budget Tx" columns are read here (never "Gợi ý Tx" — see suggestions.py for that).
"""
import re
from collections import defaultdict

import pandas as pd

from .fetch import ValidationError, _parse_vnd, _fmt_num

# Fixed-width padded account label from __REF dropdown, e.g. "  3383  Bảo hiểm xã hội"
# (see plans/260709-1415-budget-account-level-remap/phase-02). Group 2 (the name) is NEVER
# used for logic — account_code is the only trustworthy source; the name is display-only and
# can drift from __REF's own text without the code itself being wrong.
_ACCOUNT_PREFIX_RE = re.compile(r"^\s*(\d+)\s+(.+)$")

# --- BUDGET_ITEMS column positions (0-indexed) — mirrors BI_COL in validate-budget-sheet.gs ---
# Ghi chú (col B) inserted 2026-07-09 — purely informational passthrough to seed `notes`,
# lets finance distinguish multiple recurring rows that map to the SAME account_code (e.g.
# "Internet" and "Cloud Hosting" both landing on 642282) — see plans/260709-1415-budget-
# account-level-remap/plan.md.
BI_COL_CASHFLOW_LINE = 0   # A — Dòng Tiền
BI_COL_NOTES = 1           # B — Ghi chú (free text, display-only, never parsed for logic)
BI_COL_DIRECTION = 2       # C — Chiều: Thu | Chi
BI_COL_ITEM_TYPE = 3       # D — Type: recurring | one_off | reserve
BI_COL_TARGET_MONTH = 4    # E — Tháng Cần
BI_COL_PAYMENT_WEEK = 5    # F — Tuần TT
BI_COL_ITEM_TARGET = 6     # G — Tổng Cần
BI_COL_DATA_START = 7      # H onward: [Gợi Ý][Budget] pairs per month
BUDGET_HEADER_ROWS = 2     # row1 = month header, row2 = column names

VALID_ITEM_TYPES = {"recurring", "one_off", "reserve"}
VALID_DIRECTIONS = {"Thu", "Chi"}
VALID_PAYMENT_WEEKS = {"1", "2", "3", "4", "spread"}

_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")

SEED_BUDGET_COLUMNS = [
    "cashflow_line", "account_code", "period_month", "direction", "planned_amount", "payment_week",
    "item_type", "item_label", "item_target", "target_month", "notes",
]


def _parse_account_prefixed_label(raw: str):
    """(account_code, display_name) from a padded __REF label, or (None, raw.strip()) if raw
    has no numeric prefix — i.e. a legacy plain cashflow_line value (pre-migration recurring
    row) or a free-text one_off/reserve label. display_name is returned for completeness but
    callers must not use it for validation/joining — only account_code is trustworthy.
    """
    m = _ACCOUNT_PREFIX_RE.match(raw or "")
    if not m:
        return None, (raw or "").strip()
    return m.group(1), m.group(2).strip()


def _validate_no_prefix_collision(rows: list) -> list:
    """Reject a cha+con account_code pair budgeted in the same (period_month, direction) —
    the mart's prefix-match join would double-count the child's actual under both rows.
    Scoped strictly per (period_month, direction) on THIS sync's fresh rows only — never runs
    against historical rows kept by merge.py, so a legitimate granularity change across months
    (cha this month, con next month) is never rejected. See plans/260709-1415-budget-account-
    level-remap/plan.md §Khó khăn #5.
    """
    errors = []
    groups = defaultdict(list)
    for r in rows:
        if r.get("account_code"):
            groups[(r["period_month"], r["direction"])].append(r["account_code"])
    for (period, direction), codes in groups.items():
        codes = sorted(set(codes))
        for i, a in enumerate(codes):
            for b in codes[i + 1:]:
                if b.startswith(a):
                    errors.append(
                        f"Cha/con account_code trùng trong cùng kỳ {period} ({direction}): "
                        f"'{a}' là tiền tố của '{b}' — chỉ được chọn 1 trong 2, không cả hai "
                        f"(double-count actual nếu để cả hai)"
                    )
    return errors


def parse_budget_matrix(raw_df: pd.DataFrame):
    """Parse the raw BUDGET_ITEMS grid into (months, item_rows, warnings).

    months: list of (gio_col_idx, period_month_str) — one per detected month pair.
    item_rows: list of dict, one per non-skipped data row (not yet validated).
    warnings: skip-with-warning messages (template junk rows) — non-fatal.
    """
    if raw_df.shape[0] < BUDGET_HEADER_ROWS or raw_df.shape[1] <= BI_COL_DATA_START:
        raise ValidationError(
            "BUDGET_ITEMS tab structure invalid: cần >= 2 header rows và cột tháng bắt đầu từ G"
        )

    month_header = raw_df.iloc[0]
    ncols = raw_df.shape[1]
    months = []
    col = BI_COL_DATA_START
    while col < ncols:
        label = str(month_header[col]).strip()
        if label:
            m = _MONTH_RE.match(label)
            if not m:
                raise ValidationError(
                    f"BUDGET_ITEMS: không parse được header tháng '{label}' ở cột {col + 1}"
                )
            y, mo = int(m.group(1)), int(m.group(2))
            months.append((col, f"{y:04d}-{mo:02d}-01"))
        col += 2

    if not months:
        raise ValidationError("BUDGET_ITEMS: không tìm thấy cột tháng nào ở header row 1")

    items = []
    warnings = []
    for i in range(BUDGET_HEADER_ROWS, raw_df.shape[0]):
        sheet_row = i + 1  # df row0 == sheet row1
        row = raw_df.iloc[i]
        cashflow_line = str(row[BI_COL_CASHFLOW_LINE]).strip()
        item_type = str(row[BI_COL_ITEM_TYPE]).strip()

        if not item_type:
            continue  # blank row or section header (THU / CHI THƯỜNG XUYÊN / ...) — silent skip

        if not cashflow_line:
            warnings.append(
                f"BUDGET_ITEMS row {sheet_row}: Type='{item_type}' nhưng Dòng Tiền (cột A) trống "
                f"— skip dòng rác"
            )
            continue

        monthly_cells = []
        for gio_col, period_month in months:
            budget_col = gio_col + 1
            raw_val = row[budget_col] if budget_col < ncols else ""
            monthly_cells.append((period_month, str(raw_val).strip()))

        items.append({
            "sheet_row": sheet_row,
            "cashflow_line": cashflow_line,
            "notes": str(row[BI_COL_NOTES]).strip() if BI_COL_NOTES < len(row) else "",
            "direction_raw": str(row[BI_COL_DIRECTION]).strip(),
            "item_type": item_type,
            "target_month_raw": str(row[BI_COL_TARGET_MONTH]).strip(),
            "payment_week_raw": str(row[BI_COL_PAYMENT_WEEK]).strip(),
            "item_target_raw": str(row[BI_COL_ITEM_TARGET]).strip(),
            "monthly_cells": monthly_cells,
        })

    return months, items, warnings


def validate_and_build_budget_rows(items: list, ref_lines: set[str], account_taxonomy: dict = None):
    """Return (DataFrame|None, errors). errors non-empty => caller must abort (no seed write).

    account_taxonomy: account_code -> cashflow_line, from dim_gl_account (see
    duckdb_actuals._fetch_account_taxonomy_from_duckdb). Recurring rows whose "Dòng Tiền" cell
    parses as a padded account label (__REF dropdown, phase-02) are validated against this;
    rows still using a plain legacy cashflow_line value fall back to `ref_lines` (pre-migration
    compatibility — see plans/260709-1415-budget-account-level-remap/). None/empty
    account_taxonomy is treated as "no account-coded rows possible" (every recurring row must
    then match ref_lines) — safe default when a caller hasn't wired DuckDB access.
    """
    account_taxonomy = account_taxonomy or {}
    errors = []
    out_rows = []

    for it in items:
        row_no = it["sheet_row"]
        direction_raw = it["direction_raw"]
        item_type = it["item_type"]
        cashflow_line = it["cashflow_line"]
        notes = it.get("notes", "")

        if direction_raw not in VALID_DIRECTIONS:
            errors.append(f"BUDGET_ITEMS row {row_no}: Chiều phải là 'Thu' hoặc 'Chi', nhận '{direction_raw}'")
            continue
        if item_type not in VALID_ITEM_TYPES:
            errors.append(
                f"BUDGET_ITEMS row {row_no}: item_type '{item_type}' không hợp lệ "
                f"(phải là {sorted(VALID_ITEM_TYPES)})"
            )
            continue
        payment_week = it["payment_week_raw"]
        if payment_week and payment_week not in VALID_PAYMENT_WEEKS:
            errors.append(
                f"BUDGET_ITEMS row {row_no}: Tuần TT '{payment_week}' không hợp lệ "
                f"(phải là {sorted(VALID_PAYMENT_WEEKS)})"
            )
            continue

        item_target_raw = it["item_target_raw"]
        item_target_val = _parse_vnd(item_target_raw) if item_target_raw else None
        if item_target_raw and item_target_val is None:
            errors.append(f"BUDGET_ITEMS row {row_no}: Tổng Cần '{item_target_raw}' không parse được thành số")
            continue

        target_month_raw = it["target_month_raw"]
        target_month_val = None
        if target_month_raw:
            try:
                target_month_val = pd.to_datetime(target_month_raw).strftime("%Y-%m-01")
            except Exception:
                errors.append(f"BUDGET_ITEMS row {row_no}: Tháng Cần '{target_month_raw}' không phải ngày hợp lệ")
                continue

        if target_month_val and item_target_val is None:
            errors.append(
                f"BUDGET_ITEMS row {row_no}: Tháng Cần có giá trị nhưng Tổng Cần trống/không hợp lệ "
                f"— bắt buộc có target nếu có deadline"
            )
            continue

        cashflow_line_trim = cashflow_line.strip()
        if item_type == "recurring":
            account_code, _parsed_name = _parse_account_prefixed_label(cashflow_line_trim)
            if account_code is not None:
                if account_code not in account_taxonomy:
                    errors.append(
                        f"BUDGET_ITEMS row {row_no}: account_code '{account_code}' không tồn tại "
                        f"trong dim_gl_account — chọn lại đúng dòng từ dropdown __REF"
                    )
                    continue
                out_account_code = account_code
                # Derived legacy bucket (not finance's choice) — keeps the existing Metabase
                # "Cashflow Line" filter working for account-coded rows without a schema change.
                out_cashflow_line = account_taxonomy[account_code]
            else:
                if cashflow_line_trim not in ref_lines:
                    errors.append(
                        f"BUDGET_ITEMS row {row_no}: Dòng tiền '{cashflow_line}' (recurring) không có "
                        f"trong __REF — phải khớp chính xác để join sổ cái MISA"
                    )
                    continue
                out_account_code = ""
                out_cashflow_line = cashflow_line_trim
            out_item_label = ""
        else:  # one_off | reserve — plan-side only, never matched against __REF
            out_account_code = ""
            out_cashflow_line = cashflow_line_trim
            out_item_label = cashflow_line_trim

        direction = "inflow" if direction_raw == "Thu" else "outflow"

        for period_month, raw_val in it["monthly_cells"]:
            if not raw_val:
                continue  # empty cell — no row emitted
            amount = _parse_vnd(raw_val)
            if amount is None:
                errors.append(
                    f"BUDGET_ITEMS row {row_no}: Budget Tx '{raw_val}' tại {period_month} "
                    f"không parse được thành số"
                )
                continue
            if amount == 0:
                continue  # zero — no row emitted

            out_rows.append({
                "cashflow_line": out_cashflow_line,
                "account_code": out_account_code,
                "period_month": period_month,
                "direction": direction,
                "planned_amount": _fmt_num(amount),
                "payment_week": payment_week,
                "item_type": item_type,
                "item_label": out_item_label,
                "item_target": _fmt_num(item_target_val),
                "target_month": target_month_val or "",
                "notes": notes,
            })

    all_errors = errors + _validate_no_prefix_collision(out_rows)
    if all_errors:
        return None, all_errors

    df = pd.DataFrame(out_rows, columns=SEED_BUDGET_COLUMNS)
    return df, []

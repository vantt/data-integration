"""Sync Google Sheet budget matrix (BUDGET_ITEMS + ALLOCATION_POLICY) into dbt seed CSVs,
and (Phase 5) write computed suggestions back into the "Gợi Ý" column. See
plans/260705-1459-budget-cashflow-workable-loop/phase-01-sheet-to-seed-sync.md and
phase-05-prefill-suggestions.md for full design notes.

Package layout — this file re-exports the below for `import gsheet_budget_sync` compatibility
and holds the top-level orchestration (fetch_transform_and_save, write_suggestions_to_sheet, run):
  fetch.py             CSV tab fetch + shared parse/format helpers + ValidationError
  budget_transform.py  BUDGET_ITEMS parse/validate/build
  policy_transform.py  ALLOCATION_POLICY parse/validate/build
  merge.py             historical merge + atomic seed CSV write
  suggestions.py       suggestion targeting/compute logic (pure, no I/O)
  ref_accounts.py      __REF dropdown row targeting logic (pure, no I/O) — phase-02
  duckdb_actuals.py    serving-DB reads that feed suggestion/ref computation
  sheet_writeback.py   A1-cell helpers + credentialed Sheets API write

Writes 2 dbt seeds (transformation/seeds/): seed_cashflow_budget.csv (long format, 1 row per
cashflow_line/period_month/direction/item_type/item_label) and seed_cash_allocation_policy.csv
(1 row per waterfall bucket priority). Only "Budget Tx" columns are read by the default sync
(never "Gợi ý Tx"); item_type=recurring must match __REF; ANY validation failure aborts the
whole sync (both seeds unchanged, non-zero exit).

Environment:
  DBT_DATA_LAKE_PATH required by BOTH sync modes as of the account-code migration (see
    plans/260709-1415-budget-account-level-remap/phase-03) — the default sync now also reads
    dim_gl_account (via serving/olap.duckdb) to validate/derive account_code on recurring rows,
    not just --write-suggestions (which reads fact_cash_movement / mart_cashflow_reserve_status).
  SOURCES__SPREADSHEET_URL__BUDGET   Google Sheet URL (optional, has a working default)
  GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH   Shared GCP service-account JSON key path (Editor
    access on this sheet specifically) — required ONLY by --write-suggestions (not --dry-run).
    See plans/260707-1201-google-sheets-service-account/phase-01-service-account-setup.md.
"""
import os

import pandas as pd

from .fetch import (  # noqa: F401 — re-exported for `sync.X` compatibility
    SHEET_URL, SEEDS_DIR, GID_BUDGET_ITEMS, GID_ALLOCATION_POLICY, GID_REF,
    ValidationError, _fetch_tab_csv, load_ref_lines, _current_month_start,
)
from .budget_transform import (  # noqa: F401
    SEED_BUDGET_COLUMNS, parse_budget_matrix, validate_and_build_budget_rows,
    _parse_account_prefixed_label, _validate_no_prefix_collision,
)
from .policy_transform import (  # noqa: F401
    SEED_POLICY_COLUMNS, parse_policy_matrix, validate_and_build_policy_rows,
)
from .merge import merge_historical_budget, _write_csv_atomic  # noqa: F401
from .suggestions import (  # noqa: F401
    next_month_start, _preceding_months, compute_recurring_suggestions,
    compute_reserve_suggestions, build_suggestion_writes, _assert_gio_column,
)
from .duckdb_actuals import (  # noqa: F401
    _fetch_recurring_actuals_from_duckdb, _fetch_reserve_status_from_duckdb,
    _fetch_account_taxonomy_from_duckdb, _fetch_ref_accounts_from_duckdb,
)
from .ref_accounts import build_ref_rows  # noqa: F401
from .sheet_writeback import (  # noqa: F401
    _col_num_to_a1, _to_a1_cell, _fmt_suggestion_value, _write_cells_via_sheets_api,
    _write_ref_accounts,
)


def _serving_db_path() -> str:
    data_lake = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
    return os.path.join(data_lake, "serving", "olap.duckdb")


def fetch_transform_and_save(dry_run: bool = False) -> int:
    print("Starting Budget Sheet Sync (gsheet_budget_sync)...")

    budget_raw = _fetch_tab_csv(SHEET_URL, GID_BUDGET_ITEMS, "BUDGET_ITEMS")
    policy_raw = _fetch_tab_csv(SHEET_URL, GID_ALLOCATION_POLICY, "ALLOCATION_POLICY")
    ref_raw = _fetch_tab_csv(SHEET_URL, GID_REF, "__REF")

    ref_lines = load_ref_lines(ref_raw)
    if not ref_lines:
        raise ValidationError("__REF tab trống hoặc không đọc được — recurring cần __REF để validate")

    account_taxonomy = _fetch_account_taxonomy_from_duckdb(_serving_db_path())

    _months, budget_items, budget_warnings = parse_budget_matrix(budget_raw)
    budget_df, budget_errors = validate_and_build_budget_rows(budget_items, ref_lines, account_taxonomy)

    policy_items, policy_warnings = parse_policy_matrix(policy_raw)
    policy_df, policy_errors = validate_and_build_policy_rows(policy_items)

    for w in budget_warnings + policy_warnings:
        print(f"  WARNING: {w}")

    all_errors = (budget_errors or []) + (policy_errors or [])
    if all_errors:
        print(f"\nValidation FAILED ({len(all_errors)} error(s)) — seed files NOT written:")
        for e in all_errors:
            print(f"  ERROR: {e}")
        # Full detail in the exception message (not just a count) — the caller (Dagster asset,
        # orchestration layer) surfaces this to Lark. ingestion must not import orchestration
        # directly (architectural boundary, plans/260705-1704-modular-monorepo-boundary-hardening).
        detail = "\n".join(all_errors[:10])
        raise ValidationError(
            f"{len(all_errors)} validation error(s) — aborted, seeds unchanged:\n{detail}"
        )

    current_month_start = _current_month_start()
    budget_seed_path = os.path.join(SEEDS_DIR, "seed_cashflow_budget.csv")
    policy_seed_path = os.path.join(SEEDS_DIR, "seed_cash_allocation_policy.csv")

    merged_budget = merge_historical_budget(budget_seed_path, budget_df, current_month_start)

    print(
        f"\nBUDGET_ITEMS: {len(budget_df)} fresh row(s) (current+future, from={current_month_start}) "
        f"merged with historical -> {len(merged_budget)} total row(s)."
    )
    print(f"ALLOCATION_POLICY: {len(policy_df)} row(s).")

    if dry_run:
        print("\n[DRY RUN] Not writing seed files. Preview follows.")
        print("--- seed_cashflow_budget.csv (merged) ---")
        print(merged_budget.to_string(index=False))
        print("--- seed_cash_allocation_policy.csv ---")
        print(policy_df.to_string(index=False))
        return 0

    _write_csv_atomic(merged_budget, budget_seed_path)
    _write_csv_atomic(policy_df, policy_seed_path)

    print("\nSync complete. Seeds written:")
    print(f"  {budget_seed_path}")
    print(f"  {policy_seed_path}")
    return 1 if (budget_warnings or policy_warnings) else 0


def write_suggestions_to_sheet(target_month: str = None, dry_run: bool = True) -> int:
    """Compute + write next-month 'Gợi Ý' suggestions into BUDGET_ITEMS. Never touches Budget.

    dry_run=True (default): fetch (read-only, public CSV — no credentials needed) + compute +
    print the exact cell/value diff, no Sheets API call at all. Safe to run with zero Google
    credentials configured anywhere.
    dry_run=False: additionally requires GOOGLE_SERVICE_ACCOUNT_BUDGET_WRITE_PATH (see
    sheet_writeback.py module docstring) — raises RuntimeError with a clear message if unset,
    rather than silently no-op'ing or crashing obscurely.

    Idempotent: re-running for the same target_month recomputes the same rolling-avg /
    required_monthly_adj values from the same underlying actuals and overwrites the same
    cells — no drift, no duplication.
    """
    target_month = target_month or next_month_start()
    print(f"Computing suggestions for target month {target_month}...")

    budget_raw = _fetch_tab_csv(SHEET_URL, GID_BUDGET_ITEMS, "BUDGET_ITEMS")
    ref_raw = _fetch_tab_csv(SHEET_URL, GID_REF, "__REF")
    ref_lines = load_ref_lines(ref_raw)

    months, items, warnings = parse_budget_matrix(budget_raw)
    for w in warnings:
        print(f"  WARNING: {w}")

    serving_db_path = _serving_db_path()
    account_taxonomy = _fetch_account_taxonomy_from_duckdb(serving_db_path)

    # Reuse the same strict validation the daily sync uses — a structurally malformed sheet
    # must not be written into (this is exactly the class of drift that would mistarget cells).
    _validated_df, errors = validate_and_build_budget_rows(items, ref_lines, account_taxonomy)
    if errors:
        raise ValidationError(
            f"{len(errors)} validation error(s) trên BUDGET_ITEMS — không thể tính gợi ý an toàn: "
            + "; ".join(errors[:3])
        )

    window_months = _preceding_months(target_month)
    actual_rows = _fetch_recurring_actuals_from_duckdb(serving_db_path, window_months)
    reserve_rows = _fetch_reserve_status_from_duckdb(serving_db_path)

    recurring_map = compute_recurring_suggestions(actual_rows)
    reserve_map = compute_reserve_suggestions(reserve_rows)

    writes = build_suggestion_writes(items, months, target_month, recurring_map, reserve_map)

    if not writes:
        print(
            f"Không có gợi ý nào để ghi cho tháng {target_month} "
            f"(cột chưa có trên sheet hoặc không có dữ liệu nguồn)."
        )
        return 0

    print(f"\n{'[DRY RUN] ' if dry_run else ''}{len(writes)} cell(s) to write:")
    for w in writes:
        cell = _to_a1_cell(w["sheet_row"], w["col"])
        print(f"  {cell}  {w['cashflow_line']} ({w['item_type']})  ->  {_fmt_suggestion_value(w['value'])}")

    if dry_run:
        return len(writes)

    _write_cells_via_sheets_api(writes)
    print(f"\nĐã ghi {len(writes)} ô 'Gợi Ý' vào sheet (tháng {target_month}).")
    return len(writes)


def refresh_ref_accounts(dry_run: bool = True) -> int:
    """Regenerate __REF cols A:B from dim_gl_account + fact_cash_movement (phase-02). Full
    overwrite: any pre-existing content in A:B — including legacy hand-maintained
    cashflow_line rows — is replaced by the freshly computed account-based dropdown rows.
    Accepted migration consequence (decided 2026-07-11, see plan.md): any recurring
    BUDGET_ITEMS row still using a plain legacy cashflow_line label (not yet switched to the
    account dropdown) will fail __REF validation after this runs, until re-mapped.

    dry_run=True (default): fetch (read-only DuckDB, no credentials needed) + compute + print
    the row list, no Sheets API call.
    dry_run=False: requires GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH (Editor access) — see
    sheet_writeback.py module docstring.

    Idempotent: re-running recomputes the same rows from the same underlying dim_gl_account /
    fact_cash_movement state and overwrites the same range — no drift, no duplication.
    """
    accounts = _fetch_ref_accounts_from_duckdb(_serving_db_path())
    rows = build_ref_rows(accounts)

    print(f"{'[DRY RUN] ' if dry_run else ''}__REF refresh: {len(rows)} row(s).")
    for direction, label in rows:
        print(f"  {direction}  {label}")

    if dry_run:
        return len(rows)

    _write_ref_accounts(rows)
    print(f"\nĐã ghi {len(rows)} dòng vào __REF.")
    return len(rows)


def run(argv=None):
    argv = argv or []
    dry_run = "--dry-run" in argv

    if "--refresh-ref" in argv:
        n = refresh_ref_accounts(dry_run=dry_run)
        return 0 if n >= 0 else 1

    if "--write-suggestions" in argv:
        target_month = None
        if "--target-month" in argv:
            idx = argv.index("--target-month")
            if idx + 1 < len(argv):
                target_month = pd.to_datetime(argv[idx + 1]).strftime("%Y-%m-01")
        n = write_suggestions_to_sheet(target_month=target_month, dry_run=dry_run)
        return 0 if n >= 0 else 1

    return fetch_transform_and_save(dry_run=dry_run)

"""Entry point: MISA AMIS account ledger ('Sổ chi tiết các tài khoản') file-drop ingestion.

Parses MISA account-ledger Excel files and writes 1 partitioned parquet table:
  - misa_raw/account_ledger (grain: 1 row per journal line, partition year/month)

Idempotency strategy: UPSERT (replace-touched-months, always on).
  Rationale: one export covers ALL 642-group accounts for its date range.
  Re-exporting or dropping the same file a second time is safe: the touched
  (year, month) partitions are cleared before write, so data converges to the
  latest export (last-write-wins per month). This differs from sales-ledger
  which uses append-only, because account-ledger is complete-per-period.
  TODO (future): if partial-account exports are needed (e.g. only 6421),
  the idempotency key must narrow to (account, month) rather than (month),
  matching the design note in overhead-account-ledger-ingestion-design.md §4.

Usage:
  python ingestion/run-misa-account-ledger-file-drop.py
  python ingestion/run-misa-account-ledger-file-drop.py --file path/to/So_chi_tiet_6421_6422.xlsx
"""

import os
import sys
import argparse
from pathlib import Path
from glob import glob

# Resolve project root so imports work when called from any directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ingestion"))

# Kebab-case filenames require importlib
import importlib.util


def _import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


parser_mod = _import_from_file(
    "account_ledger_parser",
    PROJECT_ROOT / "ingestion" / "src" / "misa_amis" / "account-ledger-parser.py",
)
utils = _import_from_file(
    "file_drop_utils",
    PROJECT_ROOT / "ingestion" / "src" / "file-drop-utils.py",
)


# ── Input directory ────────────────────────────────────────────────────────────
# Env var for Docker; fallback to local relative path.
# If fallback path doesn't exist (e.g. Docker where volume is mounted at /app/var/),
# use the Docker-standard mount path to match asset and sensor resolution.
_DEFAULT_INPUT_DIR = os.environ.get(
    "MISA_ACCOUNT_LEDGER_INPUT_DIR",
    str(PROJECT_ROOT / "app_data" / "input_source" / "misa-account-ledger"),
)
DEFAULT_INPUT_DIR = (
    _DEFAULT_INPUT_DIR
    if os.path.isdir(_DEFAULT_INPUT_DIR)
    else "/app/var/input_source/misa-account-ledger"
)


def run(argv=None, file_path=None):
    """Parse MISA account-ledger Excel file(s) and emit 1 partitioned parquet table.

    If file_path is None, processes every *.xlsx under the input directory
    (excluding _archive/). Dagster reactive sensor drives this mode.

    Idempotency is ALWAYS ON (no opt-in flag needed):
      Before writing each file's data, full_refresh_partitions() clears all
      existing parquet in the touched (year, month) directories.
      This makes repeated ingestion of the same file safe (idempotent).
    """
    arg_parser = argparse.ArgumentParser(
        description="MISA AMIS account ledger file-drop ingestion"
    )
    arg_parser.add_argument("--file", type=str, default=None, help="Process a single Excel file")
    args = arg_parser.parse_args(argv)

    data_lake_path = utils.get_data_lake_path()
    base_path = os.path.join(data_lake_path, "misa_raw")
    input_dir = DEFAULT_INPUT_DIR

    # Override with CLI --file if provided, or function argument
    target_file = args.file or file_path

    if target_file:
        files = [str(Path(target_file).resolve())]
    else:
        # Glob all xlsx in input dir, exclude _archive/
        files = sorted(glob(os.path.join(input_dir, "*.xlsx")))
        files = [f for f in files if "_archive" not in f]

    if not files:
        print("No files to process.")
        return

    print(f"Found {len(files)} file(s) to process")

    failed = []
    for fpath in files:
        print(f"\n{'='*60}")
        try:
            df, recon = parser_mod.parse_misa_account_ledger(fpath)
        except Exception as e:
            print(f"  ERROR parsing {os.path.basename(fpath)}: {e}")
            failed.append(fpath)
            continue

        if df.empty:
            print(f"  Empty result, skipping: {fpath}")
            continue

        # ── Idempotency: always replace touched (year, month) partitions ───────
        # Account-ledger exports are complete-per-period: every export of a given
        # month includes ALL accounts for that month. Replace-then-write is safe
        # and idempotent on re-export or duplicate drop.
        # Assumption: one export covers ALL 642 accounts for its months. If a
        # future export is partial (single account), narrow the key to
        # (account, month) — see design doc §4 and the TODO in module docstring.
        touched = set(df[["year", "month"]].drop_duplicates().itertuples(index=False, name=None))
        print(f"\n  Upsert: clearing {len(touched)} partition(s) before write: {sorted(touched)}")
        utils.full_refresh_partitions(base_path, "account_ledger", touched)

        # Write parquet
        utils.write_partitioned_parquet(
            df, base_path, "account_ledger", "misa_account", "posting_date"
        )

        # ── Reconciliation log ─────────────────────────────────────────────────
        total_debit = recon.get("total_debit", 0)
        print(f"\n  Reconciliation summary:")
        print(f"    Total Nợ (all accounts): {total_debit:,} VND")

        per_account = recon.get("per_account", {})
        for acct in sorted(per_account.keys()):
            info = per_account[acct]
            lines_val = info.get("lines", 0)
            marker_val = info.get("marker")
            cong_val = info.get("cong")
            status = "OK"
            if marker_val is not None and lines_val != marker_val:
                status = f"MISMATCH (lines={lines_val:,} marker={marker_val:,})"
            elif cong_val is not None and lines_val != cong_val:
                status = f"MISMATCH (lines={lines_val:,} cong={cong_val:,})"
            print(f"    {acct}: Nợ={lines_val:,} [{status}]")

        mismatches = recon.get("mismatches", [])
        if mismatches:
            print(f"  [!] RECON_MISMATCH accounts: {mismatches} — review source file")

        if recon.get("ket_chuyen_911"):
            print(
                f"  [!] KET_CHUYEN_911 present in this file — "
                f"net overhead = Nợ − Có(≠911); verify rollup model applies exclusion"
            )

        # ── Archive source file ────────────────────────────────────────────────
        max_date = (
            max(d for d in df["posting_date"].dropna() if d is not None)
            if df["posting_date"].notna().any()
            else None
        )
        if max_date:
            utils.archive_source_file(fpath, DEFAULT_INPUT_DIR, max_date)
        else:
            print(f"  WARNING: no valid posting_date; file NOT archived: {fpath}")

    print(f"\nMISA account-ledger ingestion complete. Processed {len(files)} file(s).")

    if failed:
        names = ", ".join(os.path.basename(f) for f in failed)
        raise RuntimeError(f"{len(failed)} file(s) failed to parse: {names}")


if __name__ == "__main__":
    run()

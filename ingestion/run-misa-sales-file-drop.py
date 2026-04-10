"""Entry point: MISA AMIS sales ledger file-drop ingestion.

Parses MISA 'So_chi_tiet_ban_hang_*.xlsx' files and writes 1 parquet table:
  - misa_raw/sales_lines

Usage:
  python ingestion/run-misa-sales-file-drop.py
  python ingestion/run-misa-sales-file-drop.py --file path/to/So_chi_tiet_ban_hang.xlsx
  python ingestion/run-misa-sales-file-drop.py --full-refresh-touched-months --force
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

parser = _import_from_file("sales_ledger_parser", PROJECT_ROOT / "ingestion" / "src" / "misa_amis" / "sales-ledger-parser.py")
utils = _import_from_file("file_drop_utils", PROJECT_ROOT / "ingestion" / "src" / "file-drop-utils.py")


# Default input directory (relative to project root)
DEFAULT_INPUT_DIR = str(PROJECT_ROOT / "app_data" / "input_source" / "misa-amis")


def run(argv=None, file_path=None):
    """Parse MISA sales ledger Excel file(s) and emit 1 parquet table.

    If file_path is None, process every *.xlsx under the input directory
    (excluding _archive/). Dagster reactive sensor drives this mode.
    """
    arg_parser = argparse.ArgumentParser(description="MISA AMIS sales ledger file-drop ingestion")
    arg_parser.add_argument("--file", type=str, default=None, help="Process a single Excel file")
    arg_parser.add_argument("--full-refresh-touched-months", action="store_true",
                            help="Delete existing parquet in touched partitions before writing (opt-in)")
    arg_parser.add_argument("--force", action="store_true",
                            help="Skip the 7-day guardrail warning for --full-refresh-touched-months")
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

    for fpath in files:
        print(f"\n{'='*60}")
        df, cogs_total_claimed = parser.parse_misa_sales_ledger(fpath)

        if df.empty:
            print(f"  Empty result, skipping: {fpath}")
            continue

        # Full-refresh: delete existing parquet in touched partitions
        if args.full_refresh_touched_months:
            if not args.force:
                safe = utils.check_full_refresh_guardrail(df, "posting_date")
                if not safe:
                    print("Aborting. Add --force to override.")
                    sys.exit(1)

            touched = set(df[["year", "month"]].drop_duplicates().itertuples(index=False, name=None))
            print(f"\n  Full-refresh: clearing {len(touched)} partition(s)")
            utils.full_refresh_partitions(base_path, "sales_lines", touched)

        # Write parquet
        utils.write_partitioned_parquet(df, base_path, "sales_lines", "misa_sales", "posting_date")

        # Reconciliation log
        actual_cogs = df["cogs_amount"].sum()
        print(f"  Reconciliation: SUM(cogs_amount) = {actual_cogs:,} VND")
        if cogs_total_claimed is not None:
            delta = abs(actual_cogs - cogs_total_claimed)
            status = "✓ MATCH" if delta == 0 else f"⚠ DELTA={delta:,} VND"
            print(f"  vs Tổng cộng footer: {cogs_total_claimed:,} VND → {status}")

        # Archive source file
        max_date = max(d for d in df["posting_date"].dropna() if d is not None) if df["posting_date"].notna().any() else None
        if max_date:
            utils.archive_source_file(fpath, DEFAULT_INPUT_DIR, max_date)
        else:
            print(f"  WARNING: no valid posting_date; file NOT archived: {fpath}")

    print(f"\nMISA ingestion complete. Processed {len(files)} file(s).")


if __name__ == "__main__":
    run()

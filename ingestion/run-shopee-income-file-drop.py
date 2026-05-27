"""Entry point: Shopee released-income file-drop ingestion.

Parses Shopee Income Excel files and writes 4 parquet tables:
  - shopee_raw/order_revenue
  - shopee_raw/order_revenue_items
  - shopee_raw/order_service_fees
  - shopee_raw/order_adjustments

Usage:
  python ingestion/run-shopee-income-file-drop.py
  python ingestion/run-shopee-income-file-drop.py --file path/to/Income.xlsx
  python ingestion/run-shopee-income-file-drop.py --full-refresh-touched-months --force
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

parser = _import_from_file("income_parser", PROJECT_ROOT / "ingestion" / "src" / "shopee" / "income-parser.py")
utils = _import_from_file("file_drop_utils", PROJECT_ROOT / "ingestion" / "src" / "file-drop-utils.py")


# Input directory — env var for Docker, fallback to local relative path.
# If fallback path doesn't exist (e.g. Docker where volume is at /app/var/),
# use the Docker-standard mount path to match the asset and sensor resolution.
_DEFAULT_INPUT_DIR = os.environ.get(
    "SHOPEE_INPUT_DIR",
    str(PROJECT_ROOT / "app_data" / "input_source" / "shopee"),
)
DEFAULT_INPUT_DIR = (
    _DEFAULT_INPUT_DIR
    if os.path.isdir(_DEFAULT_INPUT_DIR)
    else "/app/var/input_source/shopee"
)


def run(argv=None, file_path=None):
    """Parse Shopee income Excel file(s) and emit 4 parquet tables.

    If file_path is None, process every *.xlsx under the input directory
    (excluding _archive/). Dagster reactive sensor drives this mode.
    """
    arg_parser = argparse.ArgumentParser(description="Shopee income file-drop ingestion")
    arg_parser.add_argument("--file", type=str, default=None, help="Process a single Excel file")
    arg_parser.add_argument("--full-refresh-touched-months", action="store_true",
                            help="Delete existing parquet in touched partitions before writing (opt-in)")
    arg_parser.add_argument("--force", action="store_true",
                            help="Skip the 7-day guardrail warning for --full-refresh-touched-months")
    args = arg_parser.parse_args(argv)

    data_lake_path = utils.get_data_lake_path()
    base_path = os.path.join(data_lake_path, "shopee_raw")
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

    entities = ["order_revenue", "order_revenue_items", "order_service_fees", "order_adjustments"]

    for fpath in files:
        print(f"\n{'='*60}")
        df_order, df_sku, df_sfd, df_adj = parser.parse_shopee_income(fpath)

        entity_dfs = [
            ("order_revenue", df_order, "payout_released_at"),
            ("order_revenue_items", df_sku, "payout_released_at"),
            ("order_service_fees", df_sfd, "payout_released_at"),
            ("order_adjustments", df_adj, "payout_released_at"),
        ]

        # Full-refresh: delete existing parquet in touched partitions
        if args.full_refresh_touched_months:
            # Guardrail: check date range
            if not args.force:
                safe = utils.check_full_refresh_guardrail(df_order, "payout_released_at")
                if not safe:
                    print("Aborting. Add --force to override.")
                    sys.exit(1)

            # Collect all touched (year, month) across all entities
            all_touched = set()
            for _, df, _ in entity_dfs:
                if not df.empty:
                    all_touched.update(df[["year", "month"]].drop_duplicates().itertuples(index=False, name=None))

            print(f"\n  Full-refresh: clearing {len(all_touched)} partition(s) across {len(entities)} entities")
            for entity in entities:
                utils.full_refresh_partitions(base_path, entity, all_touched)

        # Write parquet tables
        for entity_name, df, date_col in entity_dfs:
            if df.empty:
                print(f"  {entity_name}: empty, skipping")
                continue
            utils.write_partitioned_parquet(df, base_path, entity_name, "shopee_income", date_col)

        # Archive source file
        max_date = df_order["payout_released_at"].dropna().max() if not df_order.empty else None
        if max_date:
            utils.archive_source_file(fpath, DEFAULT_INPUT_DIR, max_date)
        else:
            print(f"  WARNING: no valid payout_released_at dates; file NOT archived: {fpath}")

    print(f"\nShopee ingestion complete. Processed {len(files)} file(s).")


if __name__ == "__main__":
    run()

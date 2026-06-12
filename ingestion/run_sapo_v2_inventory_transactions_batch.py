"""
Runner: Sapo Inventory Transactions v2 — Date-Windowed Batch Pipeline
Mirrors run_products_batch.py. Dagster imports and calls run(argv=[...]).

Usage examples:
  python run_inventory_transactions_v2_batch.py --window hour
  python run_inventory_transactions_v2_batch.py --window day
  python run_inventory_transactions_v2_batch.py --window backfill --backfill-start 2021-05-01
  python run_inventory_transactions_v2_batch.py --window custom --start 2024-01-01T00:00:00Z --end 2024-01-31T23:59:59Z
  python run_inventory_transactions_v2_batch.py --window hour --full-refresh
"""

import sys
import os
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sapo.sapo_v2_inventory_transactions import sapo_v2_inventory_transactions_source
from utils.pipeline_runner import run_pipeline


def run(argv=None):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--window",
        choices=["hour", "day", "backfill", "custom"],
        default="hour",
        help="Window mode: hour (default), day, backfill, custom",
    )
    parser.add_argument(
        "--start",
        default=None,
        dest="start_date",
        help="UTC ISO start date for custom window (e.g. 2024-01-01T00:00:00Z)",
    )
    parser.add_argument(
        "--end",
        default=None,
        dest="end_date",
        help="UTC ISO end date for custom window (e.g. 2024-01-31T23:59:59Z)",
    )
    parser.add_argument(
        "--backfill-start",
        default="2021-05-01",
        dest="backfill_start",
        help="Earliest date for backfill mode (YYYY-MM-DD, default 2021-05-01)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=250,
        dest="page_size",
        help="Items per API page (max 250, default 250)",
    )

    args, remaining_argv = parser.parse_known_args(argv)

    source_args = {
        "window_mode":    args.window,
        "start_date":     args.start_date,
        "end_date":       args.end_date,
        "backfill_start": args.backfill_start,
        "page_size":      args.page_size,
    }

    return run_pipeline(
        pipeline_name="sapo_v2_inventory_transactions_batch",
        dataset_name="sapo_v2_raw",
        source_factory=sapo_v2_inventory_transactions_source,
        source_args=source_args,
        argv=argv,
    )


if __name__ == "__main__":
    run()

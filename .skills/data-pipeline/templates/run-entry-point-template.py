"""
Entry Point Template — dlt Pipeline Runner

Thay thế trước khi dùng:
  {SOURCE}        → tên source (sapo, shopify, ...)
  {ENTITY}        → tên entity (order, customer, ...)
  {PIPELINE_NAME} → tên pipeline (sapo_orders_batch, ...)
  {DATASET_NAME}  → tên dataset trong data lake (sapo_raw, shopify_raw, ...)

Đặt file này tại: ingestion/run_{ENTITY}_{method}.py
"""

import sys
import os

# Thêm src/ vào path để import source module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from {SOURCE}.{ENTITY} import {SOURCE}_{ENTITY}_source
from utils.pipeline_runner import run_pipeline


def run(argv=None):
    """
    Entry point cho pipeline {ENTITY}.
    argv: truyền [] khi gọi từ Dagster để tránh pick up Dagster's sys.argv.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Run {ENTITY} batch pipeline.")
    # Source-specific args — thêm tùy theo source
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Max pages to fetch (default: 1000).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Items per page (default: 100).",
    )
    args, _ = parser.parse_known_args(argv)

    return run_pipeline(
        pipeline_name="{PIPELINE_NAME}",
        dataset_name="{DATASET_NAME}",
        source_factory={SOURCE}_{ENTITY}_source,
        source_args={
            "max_pages": args.limit,
            "page_size": args.page_size,
        },
        argv=argv,
    )


if __name__ == "__main__":
    run()

"""
Dagster Asset Template — dlt Pipeline Integration

Thay thế trước khi dùng:
  {SOURCE}      → tên source (sapo, shopify, ...)
  {ENTITY}      → tên entity (order, customer, ...)
  {JOB}         → tên job phù hợp (xem Job Selection Guide bên dưới)

Thêm vào: orchestration/assets/{SOURCE}_assets.py

Job Selection Guide:
  sapo_realtime_sync_job        → webhook consumer (mỗi 3 phút)
  sapo_incremental_sync_job     → history log, event polling (mỗi 10 phút)
  sapo_nightly_reconciliation_job → batch sync: orders, customers, accounts (04:00 AM)

Thêm asset mới vào job trong orchestration/definitions.py:
  {JOB}.selection.add(AssetSelection.assets({SOURCE}/{ENTITY}_batch_asset))
"""

from dagster import asset, Output
import sys
import os
from orchestration.assets.utils import load_dlt_configuration, DLT_DIR

# Thêm ingestion/ vào sys.path để import run_* modules
if DLT_DIR not in sys.path:
    sys.path.append(DLT_DIR)

# Import entry point — thêm dòng này vào đầu file assets (cùng chỗ với các import khác)
import run_{ENTITY}_batch


@asset(
    group_name="{SOURCE}_ingestion",
    key_prefix=["{SOURCE}"],
    # QUAN TRỌNG: thêm nếu asset ghi vào DuckDB (dbt models) để tránh concurrent write deadlock
    # op_tags={"dagster/concurrency_key": "duckdb_lock"},
)
def {SOURCE}_{ENTITY}_batch_asset(context):
    """
    Batch sync cho {SOURCE} {ENTITY}.
    Chạy incremental — chỉ load data mới kể từ lần chạy trước.
    """
    context.log.info("Starting {SOURCE} {ENTITY} Batch Sync...")

    # 1. Load credentials từ .env.local + secrets.toml
    load_dlt_configuration(context.log.info)

    # 2. chdir vào ingestion/ để dlt resolve .dlt/config.toml đúng
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        # argv=[] bắt buộc — tránh Dagster's sys.argv gây lỗi argparse
        load_info = run_{ENTITY}_batch.run(argv=[])
    finally:
        os.chdir(cwd)

    context.log.info(f"{ENTITY} Batch Sync Finished.")
    return Output(
        value="{ENTITY} Batch Sync Completed",
        metadata={"load_info": str(load_info)},
    )

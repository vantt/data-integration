"""
Dagster Asset Template — dlt Pipeline Integration

Thay thế trước khi dùng:
  {SOURCE}      → tên source (sapo, shopify, ...)
  {ENTITY}      → tên entity (order, customer, ...)
  {JOB}         → tên job phù hợp (xem Job Selection Guide bên dưới)

Thêm vào: orchestration/assets/{SOURCE}_assets.py

Job Selection Guide:
  ingest_sapo_realtime_job          → webhook consumer (mỗi 3 phút)
  ingest_sapo_incremental_job       → history log, event polling (mỗi 10 phút)
  pipeline_batch_nightly_job       → batch sync: orders, customers, accounts (04:00 AM)
  pipeline_batch_fullrefresh_job   → manual one-time full reload (tag "full_refresh=true" baked in)

Thêm asset mới vào job trong orchestration/definitions.py:
  {JOB}.selection.add(AssetSelection.assets({SOURCE}/{ENTITY}_batch_asset))

QUAN TRỌNG — Full-refresh design (xem L32):
  - pipeline_batch_nightly_job KHÔNG có full_refresh tag → chạy incremental bình thường
  - pipeline_batch_fullrefresh_job có tag {"full_refresh": "true"} baked in → asset tự đọc tag, truyền argv
  - Cả hai job share cùng pipeline_name → cursor liên tục giữa 2 job
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
    Mặc định: incremental — chỉ load data mới kể từ lần chạy trước.
    Full-refresh: khi job được launch với tag {"full_refresh": "true"} (pipeline_batch_fullrefresh_job).
    """
    context.log.info("Starting {SOURCE} {ENTITY} Batch Sync...")

    # Đọc full_refresh từ run tag — set bởi pipeline_batch_fullrefresh_job definition
    # Không bao giờ set tag này trên nightly schedule (wasteful, scan toàn bộ API mỗi đêm)
    full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--full-refresh"] if full_refresh else []
    if full_refresh:
        context.log.info("Full-refresh mode — resetting cursor, scanning all data")

    # 1. Load credentials từ .env.local (project root) + secrets.toml
    load_dlt_configuration(context.log.info)

    # 2. chdir vào ingestion/ để dlt resolve .dlt/config.toml đúng
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        # argv=[] (incremental) hoặc argv=["--full-refresh"] — tránh Dagster's sys.argv
        load_info = run_{ENTITY}_batch.run(argv=argv)
    finally:
        os.chdir(cwd)

    context.log.info(f"{ENTITY} Batch Sync Finished.")
    return Output(
        value="{ENTITY} Batch Sync Completed",
        metadata={"load_info": str(load_info), "full_refresh": full_refresh},
    )

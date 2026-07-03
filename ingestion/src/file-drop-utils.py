"""Shared utilities for file-drop ingestion pipelines (Shopee, MISA, etc.).

Common patterns: parquet writing with append-only semantics,
post-ingest archiving, and full-refresh guardrails.
"""

import os
import time
import shutil
from pathlib import Path
from datetime import datetime, timezone


def get_data_lake_path():
    """Get DBT_DATA_LAKE_PATH from environment, raise if not set."""
    path = os.environ.get("DBT_DATA_LAKE_PATH")
    if not path:
        raise ValueError("DBT_DATA_LAKE_PATH environment variable is not set")
    return path


def write_partitioned_parquet(df, base_path, entity_name, source_prefix, date_col):
    """Write a DataFrame to partitioned parquet files (append-only).

    Each (year, month) group gets its own file with a unique ingested_at timestamp
    in the filename. Existing files are NEVER overwritten.

    Args:
        df: DataFrame with 'year' and 'month' partition columns already set.
        base_path: e.g. "{DATA_LAKE_PATH}/shopee_raw"
        entity_name: e.g. "order_revenue"
        source_prefix: e.g. "shopee_income" for filename prefix
        date_col: name of the date column used for partitioning (for logging)

    Returns:
        list of written file paths
    """
    written_files = []
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    grouped = df.groupby(["year", "month"])
    for (year, month), group in grouped:
        output_dir = os.path.join(
            base_path, entity_name,
            "ingest_method=file_drop",
            f"year={year}", f"month={month}",
        )
        os.makedirs(output_dir, exist_ok=True)

        filename = f"{source_prefix}_{year}-{int(month):02d}_{ts}.parquet"
        file_path = os.path.join(output_dir, filename)

        # Drop partition cols before writing — they're in the hive path already
        cols_to_drop = [c for c in ["year", "month"] if c in group.columns]
        group.drop(columns=cols_to_drop).to_parquet(file_path, index=False)

        print(f"  Written {len(group)} rows -> {file_path}")
        written_files.append(file_path)

    return written_files


def archive_source_file(source_file, archive_base, max_date, ingested_at_ts=None):
    """Move processed source file to _archive/ directory.

    Args:
        source_file: Path to the .xlsx file to archive.
        archive_base: Base directory for archives (e.g. "app_data/input_source/shopee")
        max_date: datetime.date — used for the posting_month subfolder.
        ingested_at_ts: optional UTC timestamp string; generated if None.
    """
    if ingested_at_ts is None:
        ingested_at_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    posting_month = f"{max_date.year}-{max_date.month:02d}"
    archive_dir = os.path.join(archive_base, "_archive", posting_month)
    os.makedirs(archive_dir, exist_ok=True)

    original_name = os.path.basename(source_file)
    dest = os.path.join(archive_dir, f"{ingested_at_ts}__{original_name}")
    # Retry up to 3× with 1s delay — Windows may hold the xlsx handle briefly after openpyxl read.
    for attempt in range(3):
        try:
            shutil.move(str(source_file), dest)
            print(f"  Archived: {source_file} -> {dest}")
            return
        except PermissionError:
            if attempt < 2:
                time.sleep(1)
            else:
                print(f"  WARNING: could not archive {source_file} (file locked) — ingest succeeded, file left in place.")


def full_refresh_partitions(base_path, entity_name, touched_partitions):
    """Delete all parquet files in touched (year, month) partitions.

    Used with --full-refresh-touched-months flag only.

    Args:
        base_path: e.g. "{DATA_LAKE_PATH}/shopee_raw"
        entity_name: e.g. "order_revenue"
        touched_partitions: set of (year, month) tuples
    """
    for year, month in touched_partitions:
        partition_dir = Path(base_path) / entity_name / "ingest_method=file_drop" / f"year={year}" / f"month={month}"
        if not partition_dir.exists():
            continue
        parquet_files = list(partition_dir.glob("*.parquet"))
        if parquet_files:
            print(f"  Full-refresh: deleting {len(parquet_files)} files in {partition_dir}")
            for f in parquet_files:
                f.unlink()


def check_full_refresh_guardrail(df, date_col):
    """Warn if date range is < 7 days (likely a small corrective drop, not full snapshot).

    Returns True if safe to proceed, False if guardrail triggered.
    """
    import pandas as pd
    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if dates.empty:
        return True
    date_range_days = (dates.max() - dates.min()).days
    if date_range_days < 7:
        print(f"  WARNING: date range is only {date_range_days} days.")
        print(f"    This looks like a small corrective drop, not a full snapshot.")
        print(f"    --full-refresh-touched-months will DELETE existing data in touched partitions.")
        print(f"    Add --force to confirm, or remove --full-refresh-touched-months.")
        return False
    return True

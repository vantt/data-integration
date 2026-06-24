"""Shared DLT metrics helpers for ingestion asset health reporting.

Extracted from sapo_v2_assets.py::_extract_rows_written so all DLT-based
asset modules share a single implementation (DRY).

Public API:
    extract_rows_written(info_dict) -> int | None
    extract_loaded_packages(info_dict) -> list[str]
    derive_status(load_info_or_none) -> str
"""
from __future__ import annotations

import glob
import logging
import os
from pathlib import Path
from typing import Any, Optional

import duckdb

logger = logging.getLogger(__name__)


def extract_rows_written(info_dict: dict) -> Optional[int]:
    """Best-effort extraction of total rows written from a DLT LoadInfo dict.

    Strategy:
      1. Walk load_packages[].jobs[] for metrics.items_count / row_count
         (works on older dlt versions that carry per-job metrics).
      2. Fallback: the current dlt + filesystem destination does NOT populate
         item counts anywhere in LoadInfo. Read each produced parquet file
         directly via DuckDB and sum COUNT(*). Uses DBT_DATA_LAKE_PATH env
         var to resolve the bucket root.

    Returns:
        int >= 0 if determinable, including 0 when no packages loaded.
        None only if the dict is empty / structure unparseable.
    """
    if not info_dict:
        return None

    load_packages = info_dict.get("load_packages", []) or []
    # Empty packages = DLT ran but found nothing new (skipped) -> 0 rows written
    if not load_packages:
        return 0

    total = 0
    matched = False
    for pkg in load_packages:
        jobs = pkg.get("jobs")
        if isinstance(jobs, dict):
            job_list = jobs.get("completed_jobs", []) or []
        elif isinstance(jobs, list):
            job_list = jobs
        else:
            job_list = []
        for job in job_list:
            metrics = job.get("metrics") if isinstance(job, dict) else None
            if isinstance(metrics, dict):
                n = metrics.get("items_count") or metrics.get("row_count")
                if isinstance(n, int):
                    total += n
                    matched = True

    if matched:
        return total

    # Fast fallback — glob parquets by dlt file_id. Works for plain-parquet
    # filesystem destinations where the on-disk name equals {file_id}.parquet.
    fast = _count_rows_from_parquet_jobs(info_dict)
    if fast is not None:
        return fast

    # Slow fallback — Delta Lake and other destinations rewrite files with
    # their own naming scheme (e.g. part-00000-{uuid}-c000.snappy.parquet), so
    # file_id won't match on disk. Every dlt row still carries _dlt_load_id,
    # so we scan all parquets under the table dir and filter by this load's ids.
    slow = _count_rows_by_load_id(info_dict)
    if slow is not None:
        return slow

    # Packages exist but counts couldn't be determined → 0 is best we have.
    return 0


def _count_rows_from_parquet_jobs(info_dict: dict) -> Optional[int]:
    """Sum COUNT(*) across parquet files produced by this dlt load.

    Resolves final destination paths by globbing
    ``{DBT_DATA_LAKE_PATH}/{dataset_name}/{table_name}/**/{file_id}*.parquet``.
    Skips dlt-internal tables (``_dlt_*``). Returns None when DBT_DATA_LAKE_PATH
    is unset or no parquet files can be matched.
    """
    root = os.environ.get("DBT_DATA_LAKE_PATH")
    if not root:
        return None

    dataset = info_dict.get("dataset_name")
    if not dataset:
        return None

    root_path = Path(root)
    total = 0
    matched_any = False
    conn = duckdb.connect(":memory:")
    try:
        for pkg in info_dict.get("load_packages", []) or []:
            jobs = pkg.get("jobs")
            if isinstance(jobs, dict):
                job_list = jobs.get("completed_jobs", []) or []
            elif isinstance(jobs, list):
                job_list = jobs
            else:
                job_list = []
            for job in job_list:
                if not isinstance(job, dict):
                    continue
                if job.get("file_format") != "parquet":
                    continue
                table = job.get("table_name")
                file_id = job.get("file_id")
                if not table or not file_id or str(table).startswith("_dlt_"):
                    continue
                pattern = str(root_path / dataset / table / "**" / f"{file_id}*.parquet")
                for f in glob.glob(pattern, recursive=True):
                    try:
                        n = conn.execute(
                            "SELECT COUNT(*) FROM read_parquet(?)", [f]
                        ).fetchone()[0]
                        total += int(n or 0)
                        matched_any = True
                    except Exception as exc:
                        logger.warning(
                            "dlt_metrics: failed to count rows in %s: %s", f, exc
                        )
    finally:
        conn.close()

    return total if matched_any else None


def _count_rows_by_load_id(info_dict: dict) -> Optional[int]:
    """Sum rows across all parquets under the table dir, filtered by _dlt_load_id.

    Needed for Delta Lake destinations where dlt's file_id does not match the
    on-disk parquet file names. Every dlt row carries a ``_dlt_load_id``
    column, so filtering by the load's ids yields an accurate count even
    after Delta rewrites file names.

    Trade-off: reads parquet metadata for EVERY file under the table dir, so
    costs grow with table size. Acceptable at current scale (low thousands of
    files per table). Returns None when env/dataset/loads_ids cannot resolve.
    """
    root = os.environ.get("DBT_DATA_LAKE_PATH")
    if not root:
        return None

    loads_ids = info_dict.get("loads_ids") or []
    dataset = info_dict.get("dataset_name")
    if not loads_ids or not dataset:
        return None

    # Collect data-carrying table names from load_packages (skip dlt internals).
    tables: set[str] = set()
    for pkg in info_dict.get("load_packages", []) or []:
        jobs = pkg.get("jobs")
        if isinstance(jobs, dict):
            job_list = jobs.get("completed_jobs", []) or []
        elif isinstance(jobs, list):
            job_list = jobs
        else:
            job_list = []
        for job in job_list:
            if not isinstance(job, dict):
                continue
            t = job.get("table_name")
            if t and not str(t).startswith("_dlt_"):
                tables.add(str(t))

    if not tables:
        return 0

    root_path = Path(root)
    total = 0
    scanned_any = False
    conn = duckdb.connect(":memory:")
    try:
        placeholders = ", ".join("?" * len(loads_ids))
        for table in tables:
            files = glob.glob(
                str(root_path / dataset / table / "**" / "*.parquet"),
                recursive=True,
            )
            if not files:
                continue
            try:
                q = (
                    f"SELECT COUNT(*) FROM read_parquet(?, union_by_name=true) "
                    f"WHERE _dlt_load_id IN ({placeholders})"
                )
                n = conn.execute(q, [files, *loads_ids]).fetchone()[0]
                total += int(n or 0)
                scanned_any = True
            except Exception as exc:
                logger.warning(
                    "dlt_metrics: load_id scan failed for %s/%s: %s",
                    dataset, table, exc,
                )
    finally:
        conn.close()

    return total if scanned_any else None


def extract_loaded_packages(info_dict: dict) -> list[str]:
    """Return load IDs from a DLT LoadInfo dict (empty list if none or missing)."""
    return info_dict.get("loads_ids", []) or []


def derive_status(load_info_or_none: Any) -> str:
    """Derive ingestion status string from a DLT LoadInfo object (or None).

    Returns:
        'failed'  — load_info is None (run raised before DLT returned)
        'skipped' — DLT ran but produced 0 packages (no new data)
        'success' — at least one package was loaded
    """
    if load_info_or_none is None:
        return "failed"
    raw = load_info_or_none.asdict() if hasattr(load_info_or_none, "asdict") else {}
    pkgs = extract_loaded_packages(raw)
    return "success" if pkgs else "skipped"

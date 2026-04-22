"""dlt row-count extractor — reusable 3-layer fallback template.

dlt's LoadInfo from the filesystem destination (plain parquet or Delta Lake)
does NOT populate items_count / row_count reliably — it returns file_size
only. Downstream health tracking that trusts the metric walk records 0 rows
even when MB of data landed, silently hiding real ingestion volume.

Three layers, tried in order:
  1. Metric walk        — works if future dlt exposes items_count
  2. file_id glob       — fast path for plain-parquet destinations
  3. _dlt_load_id scan  — slow path for Delta and any other format that
                          rewrites file names. Every dlt row carries
                          _dlt_load_id, so this is always correct.

Public API unchanged: ``extract_rows_written(info_dict) -> int | None``.

Drop into ``orchestration/ops/dlt_metrics.py`` and customize the
DBT_DATA_LAKE_PATH env var name if your project uses a different one.
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
    """Total rows written by a dlt load. Returns None only when structure is
    unparseable; otherwise an int >= 0 (including 0 for genuinely empty loads).
    """
    if not info_dict:
        return None

    load_packages = info_dict.get("load_packages", []) or []
    if not load_packages:
        return 0

    # Layer 1: metric walk ----------------------------------------------------
    total = 0
    matched = False
    for pkg in load_packages:
        for job in _iter_jobs(pkg):
            metrics = job.get("metrics") if isinstance(job, dict) else None
            if isinstance(metrics, dict):
                n = metrics.get("items_count") or metrics.get("row_count")
                if isinstance(n, int):
                    total += n
                    matched = True
    if matched:
        return total

    # Layer 2: file_id glob (fast, plain-parquet destination) -----------------
    fast = _count_via_file_id_glob(info_dict)
    if fast is not None:
        return fast

    # Layer 3: _dlt_load_id scan (slow, Delta-compatible) ---------------------
    slow = _count_via_load_id_scan(info_dict)
    if slow is not None:
        return slow

    return 0


def extract_loaded_packages(info_dict: dict) -> list[str]:
    return info_dict.get("loads_ids", []) or []


def derive_status(load_info_or_none: Any) -> str:
    """'failed' if None, 'skipped' if ran but no packages, 'success' otherwise."""
    if load_info_or_none is None:
        return "failed"
    raw = load_info_or_none.asdict() if hasattr(load_info_or_none, "asdict") else {}
    return "success" if extract_loaded_packages(raw) else "skipped"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _iter_jobs(pkg: dict) -> list[dict]:
    """Normalise the two shapes dlt uses for pkg['jobs']."""
    jobs = pkg.get("jobs")
    if isinstance(jobs, dict):
        return jobs.get("completed_jobs", []) or []
    if isinstance(jobs, list):
        return jobs
    return []


def _count_via_file_id_glob(info_dict: dict) -> Optional[int]:
    """Glob {root}/{dataset}/{table}/**/{file_id}*.parquet and COUNT(*).

    Works when the filesystem destination writes files named ``{file_id}.parquet``
    (dlt layout ``{file_id}.{ext}``). Returns None when env unset or no files
    match — caller should fall through to the load_id scan.
    """
    root = os.environ.get("DBT_DATA_LAKE_PATH")
    dataset = info_dict.get("dataset_name")
    if not root or not dataset:
        return None

    root_path = Path(root)
    total = 0
    matched_any = False
    conn = duckdb.connect(":memory:")
    try:
        for pkg in info_dict.get("load_packages", []) or []:
            for job in _iter_jobs(pkg):
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
                        logger.warning("row count read failed for %s: %s", f, exc)
    finally:
        conn.close()

    return total if matched_any else None


def _count_via_load_id_scan(info_dict: dict) -> Optional[int]:
    """Scan all parquets under {root}/{dataset}/{table}/ and filter by _dlt_load_id.

    Required for Delta Lake — file_id from LoadInfo does not match on-disk
    part-file names (``part-00000-{uuid}-c000.snappy.parquet``). Every dlt row
    carries _dlt_load_id, so this always gives the accurate count.

    Performance note: O(N files) per call. At hundreds of files per table
    it's ~100ms. At tens of thousands it can reach seconds — optimize by
    filtering glob results on mtime > min(loads_ids epoch_seconds).
    """
    root = os.environ.get("DBT_DATA_LAKE_PATH")
    dataset = info_dict.get("dataset_name")
    loads_ids = info_dict.get("loads_ids") or []
    if not root or not dataset or not loads_ids:
        return None

    tables: set[str] = set()
    for pkg in info_dict.get("load_packages", []) or []:
        for job in _iter_jobs(pkg):
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
                logger.warning("load_id scan failed for %s/%s: %s",
                               dataset, table, exc)
    finally:
        conn.close()

    return total if scanned_any else None

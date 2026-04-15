"""File-drop metrics helpers for ingestion asset health reporting.

Used by file-drop assets (MISA AMIS, Shopee) to compute sha256, mtime,
and row count from xlsx source files BEFORE the run module archives them.

Public API:
    hash_and_count_xlsx(path) -> dict with keys: sha256, mtime_utc, row_count, sheet_count
    scan_drop_zone(input_dir) -> list[dict]  (one entry per xlsx, excl. _archive/)
    aggregate_file_manifest(entries) -> dict  (file_sha256, file_mtime, rows_fetched, manifest)
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from glob import glob
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CHUNK = 65_536  # 64 KB streaming chunks for sha256


def hash_and_count_xlsx(path: str) -> dict:
    """Compute sha256, mtime (UTC), and data row count for a single xlsx file.

    Row count = sum of (max_row - 1) across all worksheets, where the -1
    strips the header row. Uses openpyxl read-only mode for efficiency.

    Returns dict with keys: sha256 (str), mtime_utc (datetime), row_count (int),
    sheet_count (int). On any error, affected fields default to None and the
    exception is logged as a warning — callers must handle None gracefully.
    """
    result: dict = {
        "sha256": None,
        "mtime_utc": None,
        "row_count": None,
        "sheet_count": None,
    }

    # --- sha256 (streamed, memory-safe for large files) ---
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            while chunk := fh.read(_CHUNK):
                h.update(chunk)
        result["sha256"] = h.hexdigest()
    except Exception as exc:
        logger.warning("hash_and_count_xlsx: sha256 failed for %s — %s", path, exc)

    # --- mtime as UTC-aware datetime ---
    try:
        mtime_ts = os.path.getmtime(path)
        result["mtime_utc"] = datetime.fromtimestamp(mtime_ts, tz=timezone.utc)
    except Exception as exc:
        logger.warning("hash_and_count_xlsx: mtime failed for %s — %s", path, exc)

    # --- row count via openpyxl read-only ---
    try:
        import openpyxl  # noqa: PLC0415 — intentional lazy import

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        total_rows = 0
        for ws in wb.worksheets:
            max_r = ws.max_row or 0
            # Subtract header row; floor at 0 to handle empty sheets
            total_rows += max(0, max_r - 1)
        result["row_count"] = total_rows
        result["sheet_count"] = len(wb.worksheets)
        wb.close()
    except Exception as exc:
        logger.warning("hash_and_count_xlsx: row count failed for %s — %s", path, exc)

    return result


def scan_drop_zone(input_dir: str) -> list[dict]:
    """Return one metrics dict per xlsx in input_dir, excluding _archive/.

    Each entry merges hash_and_count_xlsx output with the file path.
    Files that have disappeared between glob and hash are silently skipped.
    """
    pattern = os.path.join(input_dir, "*.xlsx")
    files = sorted(f for f in glob(pattern) if "_archive" not in f)

    entries: list[dict] = []
    for fpath in files:
        if not os.path.exists(fpath):
            logger.warning("scan_drop_zone: file disappeared before hash: %s", fpath)
            continue
        metrics = hash_and_count_xlsx(fpath)
        entries.append({"path": fpath, **metrics})
    return entries


def aggregate_file_manifest(entries: list[dict]) -> dict:
    """Collapse per-file entries into asset-level summary fields.

    Returns:
        file_sha256  — sha256 of the sorted concatenation of individual hashes
                       (hash-of-hashes), or None if no valid hashes
        file_mtime   — max mtime_utc across files, or None
        rows_fetched — sum of row_count across files, or None if any is missing
        manifest     — list[dict] of per-file entries (for metadata_json)
    """
    valid_hashes = [e["sha256"] for e in entries if e.get("sha256")]
    valid_mtimes = [e["mtime_utc"] for e in entries if e.get("mtime_utc")]
    row_counts = [e.get("row_count") for e in entries]

    # hash-of-hashes: stable ordering via sorted sha256 strings
    combined_sha256: Optional[str] = None
    if valid_hashes:
        h = hashlib.sha256("".join(sorted(valid_hashes)).encode())
        combined_sha256 = h.hexdigest()

    max_mtime: Optional[datetime] = max(valid_mtimes) if valid_mtimes else None

    # rows_fetched: None if ANY file failed row count (conservative)
    rows_fetched: Optional[int] = None
    if row_counts and all(r is not None for r in row_counts):
        rows_fetched = sum(row_counts)  # type: ignore[arg-type]

    return {
        "file_sha256": combined_sha256,
        "file_mtime": max_mtime,
        "rows_fetched": rows_fetched,
        "manifest": entries,
    }

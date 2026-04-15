"""Shared DLT metrics helpers for ingestion asset health reporting.

Extracted from sapo_assets.py::_extract_rows_written so all DLT-based
asset modules share a single implementation (DRY).

Public API:
    extract_rows_written(info_dict) -> int | None
    extract_loaded_packages(info_dict) -> list[str]
    derive_status(load_info_or_none) -> str
"""
from __future__ import annotations

from typing import Any, Optional


def extract_rows_written(info_dict: dict) -> Optional[int]:
    """Best-effort extraction of total rows written from a DLT LoadInfo dict.

    DLT doesn't expose a single top-level row count. We walk load_packages ->
    jobs -> (job_counts | metrics.items_count) and sum. Returns None if the
    shape doesn't match any known path — caller keeps the raw dict in
    metadata_json as a fallback for later forensic inspection.
    """
    total = 0
    matched = False
    for pkg in info_dict.get("load_packages", []) or []:
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
    return total if matched else None


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

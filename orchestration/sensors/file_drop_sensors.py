"""Reactive sensors for file-drop ingestion (Shopee + MISA).

Watch input directories for new/modified .xlsx files. Fire one RunRequest
per file so each file gets its own isolated pipeline run.

Design:
  - Cursor = {"processed": ["filename.xlsx:mtime_int", ...]} — dispatched file keys.
  - Fires one RunRequest per file not yet in the cursor.
  - Failed files (still in drop zone, same mtime) are NOT auto-retried;
    re-add the file or manually trigger to retry.
  - Old cursor format {"mtime": float} migrates to empty set, re-dispatching
    any files currently in the drop zone.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from dagster import (
    DefaultSensorStatus,
    RunRequest,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

# Env var if set, otherwise Docker default (/app/var/input_source/).
# Local dev: set SHOPEE_INPUT_DIR / MISA_INPUT_DIR in .env.local.
_SHOPEE_INPUT_DIR = os.environ.get("SHOPEE_INPUT_DIR", "/app/var/input_source/shopee")
_MISA_INPUT_DIR = os.environ.get("MISA_INPUT_DIR", "/app/var/input_source/misa-amis")


def _get_drop_zone_files(input_dir: str) -> dict[str, float]:
    """Return {filepath: mtime} for *.xlsx files in dir, excluding _archive/."""
    result: dict[str, float] = {}
    p = Path(input_dir)
    if not p.exists():
        return result
    for f in p.glob("*.xlsx"):
        if "_archive" not in str(f):
            result[str(f)] = f.stat().st_mtime
    return result


def _file_key(fpath: str, mtime: float) -> str:
    return f"{os.path.basename(fpath)}:{int(mtime)}"


def _parse_cursor(raw: str | None) -> set[str]:
    """Parse cursor → set of dispatched file keys.

    Migrates old {"mtime": float} format to empty set so current files
    get re-dispatched under the new per-file scheme.
    """
    if not raw:
        return set()
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "processed" in data:
            return set(data["processed"])
        # Old mtime format or unknown — reset to re-dispatch current files
        return set()
    except (ValueError, TypeError):
        return set()


@sensor(
    job_name="ingest_filedrop_shopee_job",
    minimum_interval_seconds=300,
    default_status=DefaultSensorStatus.RUNNING,
    description=(
        "Watches app_data/input_source/shopee/ for new/modified .xlsx files. "
        "Fires one ingest_filedrop_shopee_job run per file."
    ),
)
def ingest_filedrop_shopee_sensor(context: SensorEvaluationContext):
    files = _get_drop_zone_files(_SHOPEE_INPUT_DIR)
    if not files:
        return SkipReason("No .xlsx files in Shopee drop zone")

    dispatched = _parse_cursor(context.cursor)
    run_requests = []
    new_dispatched = set(dispatched)

    for fpath, mtime in sorted(files.items()):
        key = _file_key(fpath, mtime)
        if key in dispatched:
            continue
        run_requests.append(RunRequest(
            run_key=f"shopee-filedrop-{key}",
            run_config={"ops": {"shopee_income_file_drop_asset": {"config": {"file_path": fpath}}}},
            tags={"source": "ingest_filedrop_shopee_sensor", "drop_file": os.path.basename(fpath)},
        ))
        new_dispatched.add(key)

    if not run_requests:
        return SkipReason("No new/modified Shopee files")

    context.update_cursor(json.dumps({"processed": list(new_dispatched)}))
    return run_requests


@sensor(
    job_name="ingest_filedrop_misa_job",
    minimum_interval_seconds=300,
    default_status=DefaultSensorStatus.RUNNING,
    description=(
        "Watches app_data/input_source/misa-amis/ for new/modified .xlsx files. "
        "Fires one ingest_filedrop_misa_job run per file."
    ),
)
def ingest_filedrop_misa_sensor(context: SensorEvaluationContext):
    files = _get_drop_zone_files(_MISA_INPUT_DIR)
    if not files:
        return SkipReason("No .xlsx files in MISA drop zone")

    dispatched = _parse_cursor(context.cursor)
    run_requests = []
    new_dispatched = set(dispatched)

    for fpath, mtime in sorted(files.items()):
        key = _file_key(fpath, mtime)
        if key in dispatched:
            continue
        run_requests.append(RunRequest(
            run_key=f"misa-filedrop-{key}",
            run_config={"ops": {"misa_amis__misa_sales_file_drop_asset": {"config": {"file_path": fpath}}}},
            tags={"source": "ingest_filedrop_misa_sensor", "drop_file": os.path.basename(fpath)},
        ))
        new_dispatched.add(key)

    if not run_requests:
        return SkipReason("No new/modified MISA files")

    context.update_cursor(json.dumps({"processed": list(new_dispatched)}))
    return run_requests

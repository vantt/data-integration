"""Factory for reactive file-drop sensors (used by the shopee and misa_amis connectors).

Watch input directories for new/modified .xlsx files. Fire one RunRequest
per file so each file gets its own isolated pipeline run.

Design:
  - Cursor = {"processed": ["filename.xlsx:mtime_int", ...]} — dispatched file keys.
  - Fires one RunRequest per file not yet in the cursor.
  - Failed files (still in drop zone, same mtime) are NOT auto-retried;
    re-add the file or manually trigger to retry.
  - Old cursor format {"mtime": float} migrates to empty set, re-dispatching
    any files currently in the drop zone.
  - Cursor is capped at CURSOR_LIMIT most-recent keys to prevent unbounded growth.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from dagster import (
    DefaultSensorStatus,
    RunRequest,
    SensorDefinition,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

# Max dispatched file keys retained in cursor. Keeps cursor JSON small and sensor
# ticks fast even after months of file-drops. Oldest keys are dropped first;
# re-dispatching an old dropped key is safe — run_key deduplication in Dagster
# prevents duplicate runs for the same file.
CURSOR_LIMIT = 500

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


def make_file_drop_sensor(
    *,
    name: str,
    job_name: str,
    input_dir: str,
    asset_op_name: str,
    run_key_prefix: str,
    source_label: str,
    drop_dir_hint: str,
) -> SensorDefinition:
    """Sensor `name` firing one `job_name` run per new/modified .xlsx in `input_dir`.

    `asset_op_name` is the op key that receives `file_path` in the run config.
    """

    @sensor(
        name=name,
        job_name=job_name,
        minimum_interval_seconds=300,
        default_status=DefaultSensorStatus.RUNNING,
        description=(
            f"Watches app_data/input_source/{drop_dir_hint}/ for new/modified .xlsx files. "
            f"Fires one {job_name} run per file."
        ),
    )
    def _sensor(context: SensorEvaluationContext):
        files = _get_drop_zone_files(input_dir)
        if not files:
            return SkipReason(f"No .xlsx files in {source_label} drop zone")

        dispatched = _parse_cursor(context.cursor)
        run_requests = []
        new_dispatched = set(dispatched)

        for fpath, mtime in sorted(files.items()):
            key = _file_key(fpath, mtime)
            if key in dispatched:
                continue
            run_requests.append(RunRequest(
                run_key=f"{run_key_prefix}-filedrop-{key}",
                run_config={"ops": {asset_op_name: {"config": {"file_path": fpath}}}},
                tags={"source": name, "drop_file": os.path.basename(fpath)},
            ))
            new_dispatched.add(key)

        if not run_requests:
            return SkipReason(f"No new/modified {source_label} files")

        # Cap cursor to most-recent CURSOR_LIMIT keys to prevent unbounded growth.
        # run_key deduplication prevents re-dispatching even if an old key is evicted.
        capped = sorted(new_dispatched)[-CURSOR_LIMIT:]
        context.update_cursor(json.dumps({"processed": capped}))
        return run_requests

    return _sensor

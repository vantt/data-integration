"""Reactive sensors for file-drop ingestion (Shopee + MISA).

Watch input directories for new/modified .xlsx files. When detected,
fire a RunRequest for the corresponding sync job that cascades:
  ingestion → dbt → serving_db

Design:
  - Cursor = max mtime of files in the drop zone (excluding _archive/).
  - Fire whenever current_mtime > prev_mtime (includes first tick with files present).
  - Sensor always runs append-only mode; --full-refresh-touched-months is CLI-only.
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

# --- Paths ---
# Env var if set, otherwise Docker default (/app/var/input_source/).
# Local dev: set SHOPEE_INPUT_DIR / MISA_INPUT_DIR in .env.local.
_SHOPEE_INPUT_DIR = os.environ.get("SHOPEE_INPUT_DIR", "/app/var/input_source/shopee")
_MISA_INPUT_DIR = os.environ.get("MISA_INPUT_DIR", "/app/var/input_source/misa-amis")


def _get_max_mtime(input_dir: str) -> float:
    """Return max mtime of *.xlsx files in dir (excluding _archive/). 0.0 if none."""
    max_mt = 0.0
    input_path = Path(input_dir)
    if not input_path.exists():
        return 0.0
    for f in input_path.glob("*.xlsx"):
        if "_archive" in str(f):
            continue
        mt = f.stat().st_mtime
        if mt > max_mt:
            max_mt = mt
    return max_mt


def _parse_cursor(raw: str | None) -> float:
    if not raw:
        return 0.0
    try:
        return float(json.loads(raw).get("mtime", 0.0))
    except (ValueError, TypeError):
        return 0.0


# Shopee sensor — ticks every 5 minutes (file drops are manual/weekly)
@sensor(
    job_name="ingest_filedrop_shopee_job",
    minimum_interval_seconds=300,
    default_status=DefaultSensorStatus.RUNNING,
    description=(
        "Watches app_data/input_source/shopee/ for new/modified .xlsx files. "
        "Fires ingest_filedrop_shopee_job on change."
    ),
)
def ingest_filedrop_shopee_sensor(context: SensorEvaluationContext):
    current_mtime = _get_max_mtime(_SHOPEE_INPUT_DIR)

    if current_mtime == 0.0:
        return SkipReason("No .xlsx files in Shopee drop zone")

    prev_mtime = _parse_cursor(context.cursor)

    if current_mtime <= prev_mtime:
        return SkipReason("No new/modified Shopee files")

    context.update_cursor(json.dumps({"mtime": current_mtime}))
    return RunRequest(
        run_key=f"shopee-file-drop-{current_mtime:.0f}",
        tags={"source": "ingest_filedrop_shopee_sensor"},
    )


# MISA sensor — ticks every 5 minutes
@sensor(
    job_name="ingest_filedrop_misa_job",
    minimum_interval_seconds=300,
    default_status=DefaultSensorStatus.RUNNING,
    description=(
        "Watches app_data/input_source/misa-amis/ for new/modified .xlsx files. "
        "Fires ingest_filedrop_misa_job on change."
    ),
)
def ingest_filedrop_misa_sensor(context: SensorEvaluationContext):
    current_mtime = _get_max_mtime(_MISA_INPUT_DIR)

    if current_mtime == 0.0:
        return SkipReason("No .xlsx files in MISA drop zone")

    prev_mtime = _parse_cursor(context.cursor)

    if current_mtime <= prev_mtime:
        return SkipReason("No new/modified MISA files")

    context.update_cursor(json.dumps({"mtime": current_mtime}))
    return RunRequest(
        run_key=f"misa-file-drop-{current_mtime:.0f}",
        tags={"source": "ingest_filedrop_misa_sensor"},
    )

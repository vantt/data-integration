"""Dagster op + job for running the platform backup script (backup.sh).

Hot backup — copies app_data + config without stopping containers.
Dagster runs inside Docker, so stopping containers would kill itself.

Config env vars:
  BACKUP_ROOT       — destination folder (required)
  BACKUP_KEEP_COUNT — rotation count, default 7
"""

import os
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dagster import op, job, OpExecutionContext, Failure

from orchestration.notifications.lark_client import send_lark_card

_ICT = timezone(timedelta(hours=7))

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKUP_SH = PROJECT_ROOT / "scripts" / "backup" / "backup.sh"

_BACKUP_TIMEOUT_SEC = 600  # 10 min max


def _run_and_log(context: OpExecutionContext, cmd: list[str], env: dict | None = None) -> None:
    """Run a subprocess, stream output to Dagster logs line-by-line, raise on failure.

    Uses Popen + stdout-stream + stderr=STDOUT + wait(timeout) pattern.
    DO NOT use capture_output=True — that pattern deadlocks when output exceeds
    the OS pipe buffer (~64 KB). backup.sh can emit large file listings or rsync
    --progress output that fills the buffer, causing a 10-min hang until timeout.
    Mirrors the pattern in orchestration/assets/serving.py _run_provisioning_script().
    """
    merged_env = {**os.environ, **(env or {})}

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # merge stderr into stdout stream
        text=True,
        bufsize=1,  # line-buffered — required for real-time streaming
        env=merged_env,
    )

    output_lines: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            output_lines.append(line)
            context.log.info(line)
        proc.wait(timeout=_BACKUP_TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise Failure(
            description=(
                f"Backup script exceeded {_BACKUP_TIMEOUT_SEC}s timeout — killed. "
                "Check for slow I/O or large backup set."
            )
        )

    if proc.returncode != 0:
        raise Failure(
            description=(
                f"Backup script exited with code {proc.returncode}. "
                f"Last output: {output_lines[-20:] if output_lines else '(empty)'}"
            )
        )


@op(
    description="Run platform hot backup (bash). Copies app_data + config files.",
    tags={
        "kind": "maintenance",
        # Acquire duckdb_lock to prevent backup from running while dbt is writing.
        # Backup copies DuckDB files — concurrent dbt write can cause WAL checkpoint stall.
        "dagster/concurrency_key": "duckdb_lock",
    },
)
def run_platform_backup(context: OpExecutionContext) -> None:
    backup_root = os.environ.get("BACKUP_ROOT")
    if not backup_root:
        raise Failure(description="BACKUP_ROOT env var is not set. Cannot run backup.")

    keep_count = os.environ.get("BACKUP_KEEP_COUNT", "7")

    if not BACKUP_SH.exists():
        raise Failure(description=f"Backup script not found: {BACKUP_SH}")

    context.log.info("Starting hot backup → %s (keep %s)", backup_root, keep_count)

    _run_and_log(context, ["bash", str(BACKUP_SH)], env={
        "BACKUP_PROJECT_ROOT": str(PROJECT_ROOT),
        "BACKUP_ROOT": backup_root,
        "BACKUP_KEEP_COUNT": keep_count,
    })

    context.log.info("Platform backup completed successfully.")
    try:
        ts = datetime.now(_ICT).strftime("%Y-%m-%d %H:%M ICT")
        send_lark_card(
            title="ChợPulse BI — ✅ Backup xong",
            color="green",
            fields={
                "Destination": backup_root,
                "Keep count": keep_count,
                "Completed at": ts,
                "Run": context.run_id[:8],
            },
        )
    except Exception:
        pass  # notification failure must never fail the job


@job(
    description="Daily platform backup (app_data + config files).",
    tags={"kind": "maintenance"},
)
def maintain_backup_platform_job():
    run_platform_backup()

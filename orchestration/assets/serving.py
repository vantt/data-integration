from dagster import asset, Output, MetadataValue, AssetExecutionContext
import os
import re
import sys
import subprocess
from .dbt import sapo_dbt_assets

# Resolve Project Root and Script Paths
# orchestration/assets/serving.py -> ../../
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "provisioning", "refresh_rolling.py")
STANDALONE_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "provisioning", "build_standalone_export.py")

# Resolve Python Executable (Try to use dlt venv if available)
# Use platform-appropriate venv path: Scripts/python.exe (Windows) vs bin/python (Linux)
if sys.platform == "win32":
    VENV_PYTHON = os.path.join(PROJECT_ROOT, "dlt", "venv", "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(PROJECT_ROOT, "dlt", "venv", "bin", "python")
PYTHON_EXE = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

# Subprocess timeout (seconds) — hard cap to prevent indefinite hangs.
# See plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md Phase 1.2
SERVING_TIMEOUT_SEC = int(os.environ.get("SERVING_TIMEOUT_SEC", "1800"))

# Severity-based warning detector — only flag explicit severity markers,
# avoid matching nominal info lines or the word 'error' in '0 errors'.
# Matches markers like: [!] Failed..., [!] WARNING..., [!] ERROR...
_WARN_MARKER_RE = re.compile(r"\[!\]\s+(Failed|WARNING|ERROR)", re.IGNORECASE)

# Hard-error marker — schema drift requires manual bootstrap of views, so the
# asset raises on this to fire run_failure_sensor → Lark alert → operator acts.
_SCHEMA_DRIFT_RE = re.compile(r"\[!\]\s+SCHEMA_DRIFT")


def _run_provisioning_script(
    context: AssetExecutionContext,
    script_path: str,
    env_label: str,
) -> list[str]:
    """Run a provisioning script as a subprocess, streaming stdout line-by-line.

    Uses Popen + stdout-stream + stderr=STDOUT + wait(timeout) pattern.
    DO NOT use capture_output=True — that pattern caused a 16h hang (L17)
    when log volume exceeded the OS pipe buffer (run 2c6d50cf).

    Args:
        context:     Dagster execution context (for structured logging).
        script_path: Absolute path to the Python script to run.
        env_label:   Short label for log messages (e.g. "refresh_rolling").

    Returns:
        List of all stdout lines (stripped), for caller to inspect.

    Raises:
        FileNotFoundError: if script_path does not exist.
        Exception: on timeout or non-zero exit code.
    """
    context.log.info(f"Starting {env_label}")
    context.log.info(f"   Script: {script_path}")
    context.log.info(f"   Python: {PYTHON_EXE}")
    context.log.info(f"   Timeout: {SERVING_TIMEOUT_SEC}s")

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")

    proc = subprocess.Popen(
        [PYTHON_EXE, script_path],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered — required for real-time streaming
    )

    output_lines: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            output_lines.append(line)
            context.log.info(line)
        proc.wait(timeout=SERVING_TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise Exception(
            f"{env_label} exceeded {SERVING_TIMEOUT_SEC}s timeout — killed. "
            "Check for DuckDB lock contention or pipeline blockage."
        )

    if proc.returncode != 0:
        raise Exception(
            f"{env_label} failed with exit code {proc.returncode}. "
            f"Last output: {output_lines[-20:] if output_lines else '(empty)'}"
        )

    return output_lines


@asset(
    deps=[sapo_dbt_assets],
    group_name="serving_layer",
    description="Generates the Serving Layer (DuckDB OLAP) from DBT Marts.",
    # serializes DuckDB writes to olap.duckdb with dbt assets
    op_tags={"dagster/concurrency_key": "duckdb_lock"},
)
def build_serving_db(context: AssetExecutionContext):
    output_lines = _run_provisioning_script(context, SCRIPT_PATH, "refresh_rolling")

    # Detect severity-tagged warnings in streamed output.
    # Script exited 0, so these are non-fatal — log but don't raise.
    warnings = [line for line in output_lines if _WARN_MARKER_RE.search(line)]
    if warnings:
        for w in warnings:
            context.log.warning(f"⚠️ {w}")

    # Schema drift — either a new table folder appeared, or an existing
    # column's TYPE changed between rolling snapshots (refresh_rolling.py
    # checks both). Raise to trigger Lark alert so an operator investigates —
    # the specific case is in the marker text itself (see `drifts` below).
    drifts = [line for line in output_lines if _SCHEMA_DRIFT_RE.search(line)]
    if drifts:
        raise Exception(
            "Schema drift detected in rolling/ — new table folder, or a "
            "column's type changed. If a new table: run `docker compose exec "
            "data_platform python scripts/provisioning/bootstrap_serving_views.py` "
            "to create its view. If a column type changed: verify the affected "
            "Metabase view/cards before trusting them. "
            f"Markers: {drifts}"
        )

    result_stdout = "\n".join(output_lines)
    return Output(
        value="Serving DB Updated",
        metadata={
            "script_output": MetadataValue.md(result_stdout),
            **({"warnings": MetadataValue.md("\n".join(warnings))} if warnings else {})
        }
    )


@asset(
    deps=[build_serving_db],
    group_name="serving_layer",
    description=(
        "Materializes all views in olap.duckdb into a self-contained standalone "
        "DuckDB file (sapo_export_<ts>.duckdb) for offline and AI analysis use."
    ),
    # Holds duckdb_lock so backup op cannot cp sapo_export_latest.duckdb
    # while this asset is writing the output file. olap.duckdb is opened
    # READ_ONLY here, but the output .duckdb is a live write — a concurrent
    # backup cp would produce a torn file.
    op_tags={"dagster/concurrency_key": "duckdb_lock"},
)
def build_standalone_export(context: AssetExecutionContext):
    output_lines = _run_provisioning_script(
        context, STANDALONE_SCRIPT, "build_standalone_export"
    )

    # Detect severity-tagged warnings (non-fatal — script exited 0).
    warnings = [line for line in output_lines if _WARN_MARKER_RE.search(line)]
    if warnings:
        for w in warnings:
            context.log.warning(f"⚠️ {w}")

    result_stdout = "\n".join(output_lines)
    return Output(
        value="Standalone Export Built",
        metadata={
            "script_output": MetadataValue.md(result_stdout),
            **({"warnings": MetadataValue.md("\n".join(warnings))} if warnings else {})
        }
    )

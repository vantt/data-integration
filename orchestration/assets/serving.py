from dagster import asset, Output, MetadataValue, AssetExecutionContext
import os
import re
import sys
import subprocess
from .dbt import sapo_dbt_assets

# Resolve Project Root and Script Path
# orchestration/assets/serving.py -> ../../
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "provisioning", "refresh_rolling.py")

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


@asset(
    deps=[sapo_dbt_assets],
    group_name="serving_layer",
    description="Generates the Serving Layer (DuckDB OLAP) from DBT Marts."
)
def sapo_serving_db(context: AssetExecutionContext):
    context.log.info(f"🚀 Starting Serving Layer Generation...")
    context.log.info(f"   Script: {SCRIPT_PATH}")
    context.log.info(f"   Python: {PYTHON_EXE}")
    context.log.info(f"   Timeout: {SERVING_TIMEOUT_SEC}s")

    if not os.path.exists(SCRIPT_PATH):
        raise FileNotFoundError(f"Serving script not found at {SCRIPT_PATH}")

    # Stream subprocess output line-by-line to avoid OS pipe buffer deadlock.
    # Merging stderr into stdout eliminates the classic two-pipe deadlock.
    # Previously: subprocess.run(capture_output=True, check=True) — no timeout, buffered —
    # caused the 16h hang on run 2c6d50cf when log volume exceeded pipe buffer.
    proc = subprocess.Popen(
        [PYTHON_EXE, SCRIPT_PATH],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered
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
            f"Serving script exceeded {SERVING_TIMEOUT_SEC}s timeout — killed. "
            f"Check for DuckDB lock contention or pipeline blockage."
        )

    if proc.returncode != 0:
        raise Exception(
            f"Serving script failed with exit code {proc.returncode}. "
            f"Last output: {output_lines[-20:] if output_lines else '(empty)'}"
        )

    # Detect severity-tagged warnings in streamed output.
    # Script exited 0, so these are non-fatal — log but don't raise.
    warnings = [line for line in output_lines if _WARN_MARKER_RE.search(line)]
    if warnings:
        for w in warnings:
            context.log.warning(f"⚠️ {w}")

    # Schema drift — new table folder appeared. Raise to trigger Lark alert
    # so operator knows to run bootstrap_serving_views.py manually.
    drifts = [line for line in output_lines if _SCHEMA_DRIFT_RE.search(line)]
    if drifts:
        raise Exception(
            "Schema drift detected — new table folders in rolling/. "
            "Run `docker compose exec data_platform python "
            "scripts/provisioning/bootstrap_serving_views.py` to create views. "
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

import os
import subprocess
import sys

from dagster import AssetExecutionContext, MetadataValue, Output, asset

from .serving import sapo_serving_db

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "provisioning", "publish_rill_assets.py")
PYTHON_EXE = sys.executable
RILL_TIMEOUT_SEC = int(os.environ.get("RILL_PUBLISH_TIMEOUT_SEC", "900"))


@asset(
    deps=[sapo_serving_db],
    group_name="reporting_layer",
    description="Publishes curated Parquet assets for the local Rill project.",
)
def sapo_rill_publish(context: AssetExecutionContext):
    context.log.info("Publishing curated Rill assets...")
    context.log.info(f"   Script: {SCRIPT_PATH}")
    context.log.info(f"   Python: {PYTHON_EXE}")
    context.log.info(f"   Timeout: {RILL_TIMEOUT_SEC}s")

    if not os.path.exists(SCRIPT_PATH):
        raise FileNotFoundError(f"Rill publish script not found at {SCRIPT_PATH}")

    proc = subprocess.Popen(
        [PYTHON_EXE, SCRIPT_PATH],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            output_lines.append(line)
            context.log.info(line)
        proc.wait(timeout=RILL_TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise Exception(
            f"Rill publish script exceeded {RILL_TIMEOUT_SEC}s timeout and was killed."
        )

    if proc.returncode != 0:
        raise Exception(
            f"Rill publish script failed with exit code {proc.returncode}. "
            f"Last output: {output_lines[-20:] if output_lines else '(empty)'}"
        )

    result_stdout = "\n".join(output_lines)
    return Output(
        value="Rill assets published",
        metadata={"script_output": MetadataValue.md(result_stdout)},
    )


from dagster import asset, Output, MetadataValue, AssetExecutionContext
import os
import sys
import subprocess
from .dbt import sapo_dbt_assets

# Resolve Project Root and Script Path
# orchestration/assets/serving.py -> ../../
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "provisioning", "generate_serving_db.py")

# Resolve Python Executable (Try to use dlt venv if available)
VENV_PYTHON = os.path.join(PROJECT_ROOT, "dlt", "venv", "Scripts", "python.exe")
PYTHON_EXE = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

@asset(
    deps=[sapo_dbt_assets],
    group_name="serving_layer",
    description="Generates the Serving Layer (DuckDB OLAP) from DBT Marts."
)
def sapo_serving_db(context: AssetExecutionContext):
    context.log.info(f"🚀 Starting Serving Layer Generation...")
    context.log.info(f"   Script: {SCRIPT_PATH}")
    context.log.info(f"   Python: {PYTHON_EXE}")

    if not os.path.exists(SCRIPT_PATH):
        raise FileNotFoundError(f"Serving script not found at {SCRIPT_PATH}")

    # Run the provisioner script
    try:
        # We run from PROJECT_ROOT to ensure any relative path assumptions in the script (if any remain) are safe,
        # though the script is robust with __file__.
        result = subprocess.run(
            [PYTHON_EXE, SCRIPT_PATH],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        context.log.info(result.stdout)
    except subprocess.CalledProcessError as e:
        context.log.error(f"Serving script failed: {e.stderr}")
        raise e

    return Output(
        value="Serving DB Updated",
        metadata={
            "script_output": MetadataValue.md(result.stdout)
        }
    )

"""
Dagster Serving Asset Template

Wrap supporting script (generate_serving_db.py, hoặc custom script) thành Dagster asset.

Đặt trong: orchestration/assets/serving.py (đã có sẵn sapo_serving_db)
Hoặc tạo asset mới cho custom serving script.

Pattern:
  - subprocess wrap standalone script (giữ script chạy được ngoài Dagster)
  - deps=[upstream_assets] để đảm bảo thứ tự
  - Auto-detect venv python (Windows vs Linux)
  - Check stdout warnings cho partial failures
"""

from dagster import asset, Output, MetadataValue, AssetExecutionContext
import os
import sys
import subprocess

# ─── Resolve paths ────────────────────────────────────────────────────────────
# orchestration/assets/serving.py → project root is ../../
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))

# Đường dẫn script (thay theo script bạn muốn wrap)
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "provisioning", "generate_serving_db.py")

# ─── Resolve Python executable ────────────────────────────────────────────────
# Ưu tiên venv trong dlt/, fallback về sys.executable
if sys.platform == "win32":
    VENV_PYTHON = os.path.join(PROJECT_ROOT, "dlt", "venv", "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(PROJECT_ROOT, "dlt", "venv", "bin", "python")

PYTHON_EXE = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable


# ─── Import upstream dbt assets ───────────────────────────────────────────────
from .dbt import sapo_dbt_assets  # thay thế nếu tên khác


@asset(
    deps=[sapo_dbt_assets],               # Bắt buộc serving chạy SAU dbt
    group_name="serving_layer",
    description="Generates Serving Layer (DuckDB OLAP) from dbt Marts rolling snapshots.",
    # Nếu serving asset ghi vào DuckDB có concurrent readers, thêm:
    # op_tags={"dagster/concurrency_key": "duckdb_lock"},
)
def {source}_serving_db(context: AssetExecutionContext):
    """
    Chạy generate_serving_db.py để:
      1. Scan rolling/{model}/ tìm latest parquet
      2. Create/update Smart Views trong serving/olap.duckdb
      3. Garbage collect các parquet file cũ
    """
    context.log.info(f"Starting Serving Layer Generation...")
    context.log.info(f"  Script: {SCRIPT_PATH}")
    context.log.info(f"  Python: {PYTHON_EXE}")

    if not os.path.exists(SCRIPT_PATH):
        raise FileNotFoundError(f"Serving script not found at {SCRIPT_PATH}")

    # Chạy subprocess
    try:
        result = subprocess.run(
            [PYTHON_EXE, SCRIPT_PATH],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        context.log.info(result.stdout)
    except subprocess.CalledProcessError as e:
        context.log.error(f"Serving script failed: {e.stderr}")
        raise

    # Partial failure detection
    # Script exit 0 kể cả khi có warning ("Empty folder", DB locked, ...)
    # Kiểm tra stdout markers để escalate nếu cần
    stdout_lower = result.stdout.lower()
    warnings = []
    if "error" in stdout_lower and "empty folder" not in stdout_lower:
        warnings.append("stdout contains 'error' — some models may have failed")
    if "[!]" in result.stdout:
        warnings.append("Script reported warnings (see [!] markers)")

    if warnings:
        for w in warnings:
            context.log.warning(f"WARNING: {w}")
        # Chỉ raise nếu có real error, không raise cho empty folder
        if any("error" in w.lower() for w in warnings):
            raise Exception(f"Serving DB generation halted: {'; '.join(warnings)}")

    return Output(
        value="Serving DB Updated",
        metadata={
            "script_output": MetadataValue.md(result.stdout),
            **({"warnings": MetadataValue.md("\n".join(warnings))} if warnings else {}),
        },
    )

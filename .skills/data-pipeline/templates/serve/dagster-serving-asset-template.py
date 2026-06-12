"""
Dagster Serving Asset Template

Wrap supporting script (generate_serving_db.py, hoặc custom script) thành Dagster asset.

Đặt trong: orchestration/assets/serving.py (đã có sẵn build_serving_db)
Hoặc tạo asset mới cho custom serving script.

Pattern:
  - Popen + streaming read + stderr merged → tránh pipe deadlock (Lesson L17)
  - Hard timeout bắt buộc → tránh hang vô hạn
  - deps=[upstream_assets] để đảm bảo thứ tự
  - Auto-detect venv python (Windows vs Linux)
  - Regex-based severity marker detection cho partial failures

QUAN TRỌNG (L17, 2026-04-08):
  KHÔNG bao giờ dùng `subprocess.run(capture_output=True)` cho script có thể in nhiều log.
  OS pipe buffer (~64 KB) đầy → child block trên print → parent block trên wait → deadlock 16h.
  Pattern dưới đây stream line-by-line + stderr=STDOUT + wait(timeout=...) = an toàn.
"""

from dagster import asset, Output, MetadataValue, AssetExecutionContext
import os
import re
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

# Hard timeout — bắt buộc để tránh hang vô hạn. Override qua env nếu cần.
SERVING_TIMEOUT_SEC = int(os.environ.get("SERVING_TIMEOUT_SEC", "1800"))

# Severity marker regex — chỉ flag explicit markers, tránh match chữ "error" trong "0 errors".
_WARN_MARKER_RE = re.compile(r"\[!\]\s+(Failed|WARNING|ERROR)", re.IGNORECASE)


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
      2. Create/update Rolling Self-Refresh Views trong serving/olap.duckdb
      3. Garbage collect các parquet file cũ
    """
    context.log.info(f"Starting Serving Layer Generation...")
    context.log.info(f"  Script: {SCRIPT_PATH}")
    context.log.info(f"  Python: {PYTHON_EXE}")
    context.log.info(f"  Timeout: {SERVING_TIMEOUT_SEC}s")

    if not os.path.exists(SCRIPT_PATH):
        raise FileNotFoundError(f"Serving script not found at {SCRIPT_PATH}")

    # Stream subprocess output line-by-line để tránh OS pipe buffer deadlock.
    # Merge stderr vào stdout → loại 2-pipe deadlock. Line-buffered + for-loop read
    # đảm bảo buffer không bao giờ đầy.
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
            f"Check for pipeline blockage or infinite loop."
        )

    if proc.returncode != 0:
        raise Exception(
            f"Serving script failed with exit code {proc.returncode}. "
            f"Last output: {output_lines[-20:] if output_lines else '(empty)'}"
        )

    # Severity-tagged warning detection — script exit 0 nên không raise,
    # chỉ log warning. Regex tránh false-positive trên chữ 'error' thường.
    warnings = [line for line in output_lines if _WARN_MARKER_RE.search(line)]
    if warnings:
        for w in warnings:
            context.log.warning(f"⚠️ {w}")

    result_stdout = "\n".join(output_lines)
    return Output(
        value="Serving DB Updated",
        metadata={
            "script_output": MetadataValue.md(result_stdout),
            **({"warnings": MetadataValue.md("\n".join(warnings))} if warnings else {}),
        },
    )

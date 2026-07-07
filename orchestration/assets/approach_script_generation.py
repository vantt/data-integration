"""approach_script_generation.py — Nightly auto-gen approach-script cho cohort actionable.

Bỏ hẳn bước người duyệt (user quyết 2026-07-06): subprocess gọi
scripts/generate_approach_scripts.py --cohort-from-queue --auto-load-url ...
trong chính data_platform (có codex CLI + scripts/ mount + crm_data:ro).
Linter máy (approach_script_lint) vẫn là gate duy nhất trước khi ghi vào CRM.

Fire-and-forget: lỗi generate/load KHÔNG red nightly job — log warning, để
_failed/ cho người soi sau (giống triết lý crm_sync.crm_cache_refresh).

Provider = codex tạm thời (user chốt 2026-07-07) — .env.docker chưa có
ANTHROPIC_API_KEY thật. Đổi qua Anthropic chỉ cần set
APPROACH_SCRIPT_AUTOGEN_PROVIDER=anthropic, không sửa code.
"""
import os
import subprocess
import sys

from dagster import AssetExecutionContext, Output, asset

from . import crm_sync

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "generate_approach_scripts.py")

PROVIDER = os.environ.get("APPROACH_SCRIPT_AUTOGEN_PROVIDER", "codex")
# Model KHÔNG chọn được với ChatGPT-subscription login (khoá cứng gpt-5.5,
# verified 2026-07-07) — reasoning effort là đòn bẩy chi phí duy nhất còn lại.
REASONING_EFFORT = os.environ.get("APPROACH_SCRIPT_AUTOGEN_REASONING_EFFORT", "low")
LOAD_URL = os.environ.get("APPROACH_SCRIPT_LOAD_URL", "http://crm:8090/admin/approach-scripts/load")
# Nhỏ ban đầu (đo cost/chất lượng thật) — mở rộng qua env khi đã tin tưởng.
LIMIT = os.environ.get("APPROACH_SCRIPT_AUTOGEN_LIMIT", "10")
TIMEOUT_SEC = int(os.environ.get("APPROACH_SCRIPT_AUTOGEN_TIMEOUT_SEC", "1800"))
CRM_DB_PATH = os.environ.get("CRM_DB_PATH", "/app/var/crm_data/crm.db")


def _run_fire_and_forget(context: AssetExecutionContext, cmd: list[str], timeout: int) -> tuple[int | None, list[str]]:
    """Popen + stream stdout (KHÔNG dùng capture_output=True — tránh pipe-buffer
    hang, xem lesson ở orchestration/assets/serving.py). Không raise; caller
    quyết định log warning vs coi là thành công."""
    proc = subprocess.Popen(
        cmd, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        lines.append(line)
        context.log.info(line)
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return None, lines
    return proc.returncode, lines


@asset(
    deps=[crm_sync.crm_cache_refresh],
    group_name="approach_script_autogen",
    description=(
        "Sinh + tự nạp approach-script cho cohort actionable (wh_sku_action_queue) "
        "mỗi đêm, không qua người duyệt (chỉ linter máy). Fire-and-forget: lỗi "
        "không chặn nightly job."
    ),
)
def approach_script_autogen(context: AssetExecutionContext) -> Output:
    cmd = [
        sys.executable, SCRIPT_PATH,
        "--cohort-from-queue",
        "--provider", PROVIDER,
        "--reasoning-effort", REASONING_EFFORT,
        "--auto-load-url", LOAD_URL,
        "--crm-db", CRM_DB_PATH,
        "--limit", str(LIMIT),
    ]
    context.log.info("approach_script_autogen: %s", " ".join(cmd))
    returncode, lines = _run_fire_and_forget(context, cmd, TIMEOUT_SEC)
    tail = "\n".join(lines[-30:])

    if returncode is None:
        context.log.warning("approach_script_autogen: timeout sau %ss — bỏ qua đêm nay (ignored)", TIMEOUT_SEC)
        return Output(value="timeout (ignored)", metadata={"status": "timeout"})
    if returncode != 0:
        context.log.warning(
            "approach_script_autogen: exit code %d (ignored, không chặn nightly job)", returncode)
        return Output(value="failed (ignored)", metadata={"status": "error", "returncode": returncode, "tail": tail})

    return Output(value="ok", metadata={"status": "ok", "tail": tail})

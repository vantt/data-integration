"""codex_cli_provider.py — codex CLI headless adapter (subscription OAuth, thủ công/dry-run mặc định)."""
from __future__ import annotations

import shlex
import subprocess

from .errors import ApproachScriptCompletionError

# `-` cuối = đọc prompt từ stdin (codex exec hỗ trợ). --skip-git-repo-check:
# generator chạy từ repo nhưng không cần codex đụng git.
DEFAULT_CODEX_CMD = "codex exec --skip-git-repo-check -"


class CodexCliCompletionProvider:
    """Gọi `codex exec` headless, prompt qua stdin.

    Auth là subscription OAuth (named volume agent_codex_config, không phải API
    key) — cần `docker compose exec data_platform codex login` một lần.

    Model KHÔNG chọn được: `-m/--model` bất kỳ ngoài default đều bị 400
    "not supported when using Codex with a ChatGPT account" (verified 2026-07-07,
    plan gốc/OAuth subscription khoá cứng model gpt-5.5). Đòn bẩy chi phí duy nhất
    còn lại là reasoning_effort (`-c model_reasoning_effort=<level>`).
    """

    name = "codex"

    def __init__(self, codex_cmd: str = DEFAULT_CODEX_CMD, reasoning_effort: str | None = None):
        self.codex_cmd = codex_cmd
        self.reasoning_effort = reasoning_effort

    def _build_argv(self) -> list[str]:
        argv = shlex.split(self.codex_cmd)
        if self.reasoning_effort:
            # Chèn ngay sau 'exec' (index 1) — an toàn bất kể --codex-cmd tuỳ biến
            # thêm bớt gì ở cuối (vd token stdin '-').
            insert_at = 2 if len(argv) > 1 and argv[1] == "exec" else len(argv)
            argv[insert_at:insert_at] = ["-c", f"model_reasoning_effort={self.reasoning_effort}"]
        return argv

    @property
    def model_label(self) -> str:
        base = self.codex_cmd.split()[0]
        return f"{base}(reasoning={self.reasoning_effort})" if self.reasoning_effort else base

    def complete(self, prompt: str, timeout: int) -> str:
        try:
            proc = subprocess.run(
                self._build_argv(),
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise ApproachScriptCompletionError(f"timeout sau {timeout}s") from exc
        except FileNotFoundError as exc:
            raise ApproachScriptCompletionError(
                f"Không chạy được lệnh {self.codex_cmd!r} — codex không có trong PATH "
                f"của shell này? Chạy trong terminal có codex, hoặc chỉnh --codex-cmd/CODEX_CMD."
            ) from exc

        stdout = proc.stdout.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")
            raise ApproachScriptCompletionError(
                f"codex rc={proc.returncode}: {stderr.strip()[:200]}"
            )
        return stdout

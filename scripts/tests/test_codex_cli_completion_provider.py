"""test_codex_cli_completion_provider.py — subprocess behavior of CodexCliCompletionProvider.

Uses `python -c ...` in place of the real codex binary (not assumed to be on
PATH in CI/dev shells) to exercise the same subprocess/timeout/rc code paths.

Run:
  python -m pytest scripts/tests/test_codex_cli_completion_provider.py -q
"""
from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from approach_script_completion.codex_cli_provider import CodexCliCompletionProvider  # noqa: E402
from approach_script_completion.errors import ApproachScriptCompletionError  # noqa: E402

_PY = shlex.quote(sys.executable)


def test_complete_returns_stdout_on_success():
    provider = CodexCliCompletionProvider(codex_cmd=f"{_PY} -c \"import sys; print('{{}}'); sys.exit(0)\"")
    assert provider.complete("prompt", timeout=10).strip() == "{}"


def test_complete_raises_on_nonzero_exit():
    provider = CodexCliCompletionProvider(codex_cmd=f"{_PY} -c \"import sys; sys.exit(1)\"")
    with pytest.raises(ApproachScriptCompletionError, match="rc=1"):
        provider.complete("prompt", timeout=10)


def test_complete_raises_on_missing_binary():
    provider = CodexCliCompletionProvider(codex_cmd="this-binary-does-not-exist-xyz")
    with pytest.raises(ApproachScriptCompletionError, match="không có trong PATH"):
        provider.complete("prompt", timeout=10)


def test_model_label_is_first_token_of_codex_cmd():
    provider = CodexCliCompletionProvider(codex_cmd="codex exec --skip-git-repo-check -")
    assert provider.model_label == "codex"

"""test_approach_script_completion_factory.py — factory + provider unit tests.

Covers phase-04 acceptance:
  - get_completion_provider("codex") -> CodexCliCompletionProvider
  - get_completion_provider("anthropic") -> AnthropicCompletionProvider
  - unknown name -> ValueError
  - AnthropicCompletionProvider raises ApproachScriptCompletionError without an API key

Run:
  python -m pytest scripts/tests/test_approach_script_completion_factory.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from approach_script_completion.anthropic_provider import AnthropicCompletionProvider  # noqa: E402
from approach_script_completion.codex_cli_provider import CodexCliCompletionProvider  # noqa: E402
from approach_script_completion.errors import ApproachScriptCompletionError  # noqa: E402
from approach_script_completion.factory import get_completion_provider  # noqa: E402


def test_factory_returns_codex_provider():
    provider = get_completion_provider("codex")
    assert isinstance(provider, CodexCliCompletionProvider)
    assert provider.name == "codex"


def test_factory_forwards_kwargs_to_codex_provider():
    provider = get_completion_provider("codex", codex_cmd="echo hi")
    assert provider.codex_cmd == "echo hi"
    assert provider.model_label == "echo"


def test_factory_returns_anthropic_provider(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-test-key")
    provider = get_completion_provider("anthropic")
    assert isinstance(provider, AnthropicCompletionProvider)
    assert provider.name == "anthropic"


def test_factory_unknown_provider_raises_value_error():
    with pytest.raises(ValueError):
        get_completion_provider("gemini")


def test_anthropic_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ApproachScriptCompletionError):
        AnthropicCompletionProvider()

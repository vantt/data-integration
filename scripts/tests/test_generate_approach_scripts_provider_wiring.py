"""test_generate_approach_scripts_provider_wiring.py — provider hexagon wiring in generate_approach_scripts.py.

Covers phase-04 acceptance:
  - --dry-run unchanged: writes prompt files only, never constructs/calls a provider
  - --provider anthropic: generate_approach_scripts.py resolves AnthropicCompletionProvider via
    the factory and calls provider.complete(prompt, timeout); JSON/lint pipeline downstream
    (meta.model/meta.generator, lint, output file) is unchanged.
  - a provider failure (ApproachScriptCompletionError) routes the customer to the _failed/ dir
    instead of crashing the batch.

cohort/history/template are stubbed (no duckdb/crm.db access needed for this test).

Run:
  python -m pytest scripts/tests/test_generate_approach_scripts_provider_wiring.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import generate_approach_scripts as gen  # noqa: E402
from approach_script_completion.anthropic_provider import AnthropicCompletionProvider  # noqa: E402
from approach_script_completion.errors import ApproachScriptCompletionError  # noqa: E402

_VALID_SCRIPT = {
    "profile_read": "test profile",
    "value_assessment": {"tier": "SILVER"},
    "opportunity": {"headline": "test"},
    "risk": {"headline": "test"},
    "approach": {"recommended": True, "primary_channel": "phone"},
    "confidence": "medium",
    "data_gaps": [],
}


def _fake_customer():
    return {"customer_id": "123", "is_margin_negative": False,
            "avg_order_contribution_margin_pct": 10.0, "customer_type": "RETAIL"}


@pytest.fixture(autouse=True)
def _stub_cohort(monkeypatch):
    monkeypatch.setattr(gen, "fetch_cohort", lambda args: [_fake_customer()])
    monkeypatch.setattr(gen, "fetch_history", lambda customers, args: {})
    monkeypatch.setattr(gen, "load_template", lambda: "{{customer_json}} at {{data_as_of}}")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-test-key")


def _run(monkeypatch, tmp_path, extra_args):
    monkeypatch.setattr(sys, "argv", [
        "generate_approach_scripts.py", "--ids", "123", "--out", str(tmp_path), *extra_args,
    ])
    gen.main()


def test_dry_run_never_touches_provider(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(AnthropicCompletionProvider, "complete",
                         lambda self, prompt, timeout: calls.append(1) or "unused")

    _run(monkeypatch, tmp_path, ["--dry-run", "--provider", "anthropic"])

    assert (tmp_path / "123.prompt.txt").exists()
    assert not (tmp_path / "123.json").exists()
    assert not calls


def test_anthropic_provider_success_wires_meta_and_output(tmp_path, monkeypatch):
    captured = {}

    def _fake_complete(self, prompt, timeout):
        captured["prompt"] = prompt
        captured["timeout"] = timeout
        return json.dumps(_VALID_SCRIPT)

    monkeypatch.setattr(AnthropicCompletionProvider, "complete", _fake_complete)

    _run(monkeypatch, tmp_path, ["--provider", "anthropic", "--timeout", "42"])

    assert captured["timeout"] == 42
    assert '"customer_id": "123"' in captured["prompt"]

    out_file = tmp_path / "123.json"
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert data["meta"]["generator"] == "anthropic"
    assert data["meta"]["model"] == "claude-sonnet-5"
    assert not (tmp_path / "_failed").exists()


def test_provider_completion_error_routes_to_failed_dir(tmp_path, monkeypatch):
    def _raise(self, prompt, timeout):
        raise ApproachScriptCompletionError("boom")

    monkeypatch.setattr(AnthropicCompletionProvider, "complete", _raise)

    _run(monkeypatch, tmp_path, ["--provider", "anthropic"])

    assert not (tmp_path / "123.json").exists()
    failed_file = tmp_path / "_failed" / "123.stdout.txt"
    assert failed_file.exists()
    assert "boom" in failed_file.read_text(encoding="utf-8")

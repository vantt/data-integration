"""approach_script_autogen obeys the tenant switch APPROACH_SCRIPT_AUTOGEN_ENABLED."""
from __future__ import annotations

import pytest
from dagster import build_asset_context

from orchestration.packs.sales_playbook import approach_script_generation as gen
from orchestration.tenants.fine_japan import config as fine_japan


def test_fine_japan_has_autogen_off(monkeypatch):
    monkeypatch.delenv("APPROACH_SCRIPT_AUTOGEN_ENABLED", raising=False)
    assert fine_japan.APPROACH_SCRIPT_AUTOGEN_ENABLED == "false"
    assert gen.autogen_enabled() is False


def test_disabled_returns_without_running_the_generator(monkeypatch):
    monkeypatch.setenv("APPROACH_SCRIPT_AUTOGEN_ENABLED", "false")

    def must_not_run(*args, **kwargs):
        raise AssertionError("the generator ran while autogen is disabled")

    monkeypatch.setattr(gen, "_run_fire_and_forget", must_not_run)
    out = gen.approach_script_autogen(build_asset_context())
    assert out.value == "disabled"
    assert out.metadata["status"].value == "disabled"


@pytest.mark.parametrize("value", ["true", "TRUE", " 1 ", "yes", "on"])
def test_enabled_runs_the_generator(monkeypatch, value):
    monkeypatch.setenv("APPROACH_SCRIPT_AUTOGEN_ENABLED", value)
    calls = []

    def fake_run(context, cmd, timeout):
        calls.append(cmd)
        return 0, ["done"]

    monkeypatch.setattr(gen, "_run_fire_and_forget", fake_run)
    out = gen.approach_script_autogen(build_asset_context())
    assert out.value == "ok"
    assert len(calls) == 1 and "--cohort-from-queue" in calls[0]


@pytest.mark.parametrize("value", ["false", "0", "", "off", "no"])
def test_other_values_disable(monkeypatch, value):
    monkeypatch.setenv("APPROACH_SCRIPT_AUTOGEN_ENABLED", value)
    assert gen.autogen_enabled() is False

"""Every connector and pack schedule runs on Vietnam time.

A ScheduleDefinition without execution_timezone reads its cron in UTC: crm_backup_schedule
("0 2 * * *") ran at 09:00 ICT for that reason.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

ORCH = Path(__file__).resolve().parents[2]
JOB_MODULES = sorted(
    f"orchestration.{p.parent.parent.name}.{p.parent.name}.jobs"
    for kind in ("connectors", "packs")
    for p in (ORCH / kind).glob("*/jobs.py")
)


def test_job_modules_found():
    assert "orchestration.packs.crm.jobs" in JOB_MODULES


@pytest.mark.parametrize("module_name", JOB_MODULES)
def test_schedules_run_on_vietnam_time(module_name):
    module = importlib.import_module(module_name)
    for schedule in getattr(module, "SCHEDULES", []):
        assert schedule.execution_timezone == "Asia/Ho_Chi_Minh", (
            f"{module_name}: {schedule.name} has execution_timezone={schedule.execution_timezone!r}")


def test_crm_backup_runs_at_two_am_vietnam_time():
    from orchestration.packs.crm.jobs import crm_backup_schedule

    assert crm_backup_schedule.cron_schedule == "0 2 * * *"
    assert crm_backup_schedule.execution_timezone == "Asia/Ho_Chi_Minh"

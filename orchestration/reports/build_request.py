"""Ask the report site builder (container `evidence`) for a new build.

The builder polls `<REPORT_BUILD_DIR>/request.json` and builds every area once per `request_id`
(evidence/scripts/build-areas.sh). Two ways to ask:

- automatically, when `pipeline_batch_nightly_job` succeeds (sensor from `make_after_nightly_sensor`);
- by hand, by launching `report_site_build_job` (for example after a page change was deployed).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dagster import (
    DagsterRunStatus,
    DefaultSensorStatus,
    RunRequest,
    RunStatusSensorContext,
    job,
    op,
    run_status_sensor,
)

DEFAULT_BUILD_DIR = "/app/var/data_lake/report_build"


def build_dir() -> Path:
    return Path(os.getenv("REPORT_BUILD_DIR", DEFAULT_BUILD_DIR))


def write_request(request_id: str, trigger: str, directory: Path | None = None) -> Path:
    """Write request.json atomically (the builder must never read a half-written file)."""
    directory = directory or build_dir()
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "request_id": request_id,
        "requested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trigger": trigger,
    }
    tmp = directory / "request.json.tmp"
    tmp.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    os.replace(tmp, directory / "request.json")
    return directory / "request.json"


@op
def request_report_build(context) -> None:
    trigger = context.run.tags.get("report_build_trigger", "manual")
    path = write_request(context.run_id, trigger)
    context.log.info(f"report site build requested ({trigger}): {path}")


@job(tags={"report_site": "build_request"})
def report_site_build_job():
    request_report_build()


def make_after_nightly_sensor(nightly_job):
    @run_status_sensor(
        name="report_site_build_after_nightly_sensor",
        run_status=DagsterRunStatus.SUCCESS,
        monitored_jobs=[nightly_job],
        request_job=report_site_build_job,
        minimum_interval_seconds=60,
        default_status=DefaultSensorStatus.RUNNING,  # on after deploy; it only writes request.json
    )
    def report_site_build_after_nightly_sensor(context: RunStatusSensorContext):
        return RunRequest(
            run_key=f"after-nightly-{context.dagster_run.run_id}",
            tags={"report_build_trigger": f"nightly:{context.dagster_run.run_id}"},
        )

    return report_site_build_after_nightly_sensor

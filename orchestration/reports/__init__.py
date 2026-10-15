"""Report site: build requests after the nightly run, build monitoring, summary messages.

Kernel module (like ops/ and sensors/): definitions.py calls `definitions(nightly_job)`.
Design and runbook: orchestration/reports/README.md.
"""
from __future__ import annotations

from orchestration.reports.build_request import make_after_nightly_sensor, report_site_build_job
from orchestration.reports.build_status import report_site_build_status_sensor
from orchestration.reports.summary_message import report_summary_message_job


def definitions(nightly_job) -> dict:
    """Jobs and sensors of the report site; `nightly_job` triggers the build request."""
    return {
        "jobs": [report_site_build_job, report_summary_message_job],
        "sensors": [make_after_nightly_sensor(nightly_job), report_site_build_status_sensor],
    }

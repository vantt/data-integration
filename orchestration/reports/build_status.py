"""Watch the report site builder: alert on failure or delay, then trigger due summary messages.

Reads `<REPORT_BUILD_DIR>/request.json` (written by build_request.py) and `status.json` (written by
evidence/scripts/build-areas.sh). The sensor cursor remembers what was already alerted and sent, so
each event produces one card / one run.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dagster import DefaultSensorStatus, RunRequest, SensorEvaluationContext, SkipReason, sensor

from orchestration.notifications.lark_client import send_lark_card
from orchestration.reports.build_request import build_dir
from orchestration.reports.summary_message import due_reports, report_summary_message_job, tenant_profile

OVERDUE_AFTER = timedelta(hours=2)


def _read(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError):
        return None  # being written; next tick


def evaluate(request: dict | None, status: dict | None, cursor: dict, profile: dict, now: datetime,
             alert=send_lark_card) -> tuple[list[RunRequest], dict]:
    """Pure decision step (tested without Dagster): returns run requests and the new cursor."""
    cursor = dict(cursor)
    runs: list[RunRequest] = []
    rid = (request or {}).get("request_id")
    srid = (status or {}).get("request_id")

    if status and srid and not status.get("ok") and cursor.get("alerted_failure") != srid:
        failed = {a: v.get("error", "") for a, v in status.get("areas", {}).items() if not v.get("ok")}
        alert("Report site: build lỗi (trang giữ bản trước)",
              {"Request": srid, **{f"Khu vực {a}": (e or "lỗi")[:300] for a, e in failed.items()}}, color="red")
        cursor["alerted_failure"] = srid

    if rid and srid != rid and cursor.get("alerted_overdue") != rid:
        requested = datetime.fromisoformat(request["requested_at"])
        if now - requested > OVERDUE_AFTER:
            alert("Report site: chưa build xong", {"Request": rid, "Yêu cầu lúc": request["requested_at"],
                                                   "Trạng thái": f"chưa có kết quả sau {OVERDUE_AFTER}"},
                  color="orange")
            cursor["alerted_overdue"] = rid

    if status and status.get("ok") and status.get("as_of"):
        as_of = date.fromisoformat(status["as_of"])
        local_today = now.astimezone(ZoneInfo(profile["locale"]["timezone"])).date()
        if as_of == local_today - timedelta(days=1):  # only fresh data is announced
            sent = set(cursor.get("summaries", []))
            for due in due_reports(profile, now):
                key = f"{due.report}@{as_of.isoformat()}"
                if key in sent:
                    continue
                runs.append(RunRequest(
                    run_key=f"summary-{key}",
                    run_config={"ops": {"send_report_summary": {"config": {"report": due.report, "as_of": as_of.isoformat()}}}},
                ))
                sent.add(key)
            cursor["summaries"] = sorted(sent)[-50:]
    return runs, cursor


@sensor(
    name="report_site_build_status_sensor",
    job=report_summary_message_job,
    minimum_interval_seconds=300,
    default_status=DefaultSensorStatus.RUNNING,  # summaries stay dry-run until REPORT_MESSAGE_DRY_RUN=0
)
def report_site_build_status_sensor(context: SensorEvaluationContext):
    directory = build_dir()
    cursor = json.loads(context.cursor) if context.cursor else {}
    runs, new_cursor = evaluate(_read(directory / "request.json"), _read(directory / "status.json"),
                                cursor, tenant_profile(), datetime.now(timezone.utc))
    context.update_cursor(json.dumps(new_cursor, sort_keys=True))
    if not runs:
        return SkipReason("report site: nothing to announce")
    return runs

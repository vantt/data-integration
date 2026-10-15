"""Summary message of a report after a successful build: KPI tiles + link to the page, sent to Lark.

Channels and schedules come from the tenant profile (`message` in
tenants/<t>/analytics/profile.yml); each channel names the environment variables of its webhook and
secret. The message is only logged unless REPORT_MESSAGE_DRY_RUN=0 (default 1), and a channel whose
webhook variable is unset is skipped: it never falls back to the alert webhook. Failures are logged
and never fail the run. Tiles that show costs are dropped for channels with `can_view_cost: false`.
"""

# No `from __future__ import annotations`: Dagster resolves the op's Config annotation at import.
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dagster import Config, OpExecutionContext, job, op

from analytics.compiler.loader import CATALOG_FILE, load_catalog, load_profile, load_registry, profile_path
from analytics.renderers.message import report_entry, report_link, summary_card, summary_tiles
from orchestration.module_registry import enabled_ids
from orchestration.notifications.lark_client import send_lark_card

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def tenant_profile() -> dict[str, Any]:
    return load_profile(profile_path(enabled_ids("tenants")[0]))


@dataclass(frozen=True)
class Due:
    report: str
    channels: tuple[str, ...]


def due_reports(profile: dict[str, Any], now: datetime) -> list[Due]:
    """Reports whose message is due at `now` (weekday and not_before in the tenant time zone)."""
    local = now.astimezone(ZoneInfo(profile["locale"]["timezone"]))
    out = []
    for entry in (profile.get("message") or {}).get("reports", []):
        if WEEKDAYS[local.weekday()] not in entry["weekdays"]:
            continue
        if entry.get("not_before") and local.strftime("%H:%M") < entry["not_before"]:
            continue
        out.append(Due(entry["report"], tuple(entry["channels"])))
    return out


def _query_rows(tiles, olap_db: str) -> dict[str, dict[str, Any]]:
    """Run the tile SQL read-only on a private copy of the serving catalog (views over parquet)."""
    import duckdb

    with tempfile.TemporaryDirectory(prefix="report-summary-") as tmp:
        copy = Path(tmp) / "olap.duckdb"
        shutil.copyfile(olap_db, copy)
        con = duckdb.connect(str(copy), read_only=True)
        try:
            rows = {}
            for tile in tiles:
                cur = con.execute(tile.sql)
                names = [d[0] for d in cur.description]
                row = cur.fetchone()
                rows[tile.card_id] = dict(zip(names, row)) if row else {}
            return rows
        finally:
            con.close()


def send_summary(report_id: str, as_of: date, log, olap_db: str | None = None,
                 profile: dict[str, Any] | None = None) -> dict[str, str]:
    """Build and send (or log) the message for every channel of the report. Returns channel -> outcome."""
    profile = profile or tenant_profile()
    reg, catalog = load_registry(), load_catalog(CATALOG_FILE)
    report = report_entry(catalog, report_id)
    entry = next(e for e in profile["message"]["reports"] if e["report"] == report_id)
    channels = {c["id"]: c for c in profile["message"]["channels"]}
    dry_run = os.getenv("REPORT_MESSAGE_DRY_RUN", "1") != "0"
    olap_db = olap_db or os.getenv("OLAP_DB_PATH", "/app/var/data_lake/serving/olap.duckdb")
    outcome = {}
    for channel_id in entry["channels"]:
        channel = channels[channel_id]
        try:
            tiles = summary_tiles(reg, profile, catalog, CATALOG_FILE, report_id, as_of, channel["can_view_cost"])
            title, fields = summary_card(report, tiles, _query_rows(tiles, olap_db), as_of, report_link(profile, report))
        except Exception as exc:  # a broken message must not fail the run
            log.error(f"summary {report_id} -> {channel_id}: cannot build the message: {exc}")
            outcome[channel_id] = "error"
            continue
        webhook = os.getenv(channel["env_webhook"], "")
        if dry_run or not webhook:
            why = "dry run (REPORT_MESSAGE_DRY_RUN=0 to send)" if dry_run else f"{channel['env_webhook']} is not set"
            log.info(f"summary {report_id} -> {channel_id}: not sent, {why}: {title} :: {fields}")
            outcome[channel_id] = "logged"
            continue
        secret = os.getenv(channel.get("env_secret", ""), "") or None
        ok = send_lark_card(title, fields, color="blue", webhook=webhook, secret=secret)
        (log.info if ok else log.error)(f"summary {report_id} -> {channel_id}: {'sent' if ok else 'send failed'}")
        outcome[channel_id] = "sent" if ok else "error"
    return outcome


class SummaryConfig(Config):
    report: str
    as_of: str  # YYYY-MM-DD, the as_of of the build


@op
def send_report_summary(context: OpExecutionContext, config: SummaryConfig) -> None:
    outcome = send_summary(config.report, date.fromisoformat(config.as_of), context.log)
    context.log.info(f"summary {config.report}: {outcome}")


@job(tags={"report_site": "summary"})
def report_summary_message_job():
    send_report_summary()

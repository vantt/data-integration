"""Sheets modified sensor — detect edits in Google Sheets via content hash.

Polls the public CSV export URL of each tracked sheet every N minutes,
computes a sha256 of the response body, and compares to a cursor of
last-known hashes. When any hash changes, fires a RunRequest for
`ingest_sheets_sync_job` (which cascades downstream into dbt + serving_db).

Design rationale (why content hash, not Drive API `modifiedTime`):
  - These sheets are published as "anyone with link can view" and are
    already fetched anonymously via the CSV export endpoint. No service
    account or OAuth credential is wired up for them today.
  - Content hash needs zero new auth, zero new Python deps, and is
    immune to false positives from cell-format-only edits (format changes
    do NOT alter exported CSV bytes, whereas `modifiedTime` bumps on
    every touch including format/sort/rename).
  - Cost: ~10 KB per poll × 2 sheets × every 5 min ≈ 5.7 MB/day. Trivial.

Cursor format (JSON): `{"targets": "<sha256>", "marketing_spend": "<sha256>"}`.
On first tick (empty cursor) the sensor records hashes but does NOT fire —
we only want to trigger on CHANGE, not on cold start.

Alerts: failures propagate naturally — `health_alert_failure_sensor` will fire if
`ingest_sheets_sync_job` fails, and `health_alert_stuckrun_sensor` catches hangs. No extra
logic here.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

import requests
from dagster import (
    DefaultSensorStatus,
    RunRequest,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

from ingestion.src.gsheet_auth import spreadsheet_url

# Tracked sheets: {cursor name: (SOURCES__SPREADSHEET_URL__<NAME>, tab gid or None)}. The URL
# comes from the same env variable the ingestion reader uses (ingestion/src/gsheet_*.py), so
# each sheet URL is declared in one place. A tab gid polls that tab; None polls the first tab.
# The URL is read per tick: a missing variable fails this sensor's tick with
# SpreadsheetUrlNotConfigured, not the whole code location.
TRACKED_SHEETS = {
    "targets": ("TARGETS", None),
    "marketing_spend": ("MARKETING_SPEND", None),
    # US Shipment price changes are infrequent but high-impact; detect immediately.
    # gid = the price list tab read by ingestion/src/gsheet_us_shipment_prices.py (_SHEET_GID).
    "us_shipment_prices": ("US_SHIPMENT_PRICES", "304875363"),
}

_SHEET_PATH_RE = re.compile(r"^(/spreadsheets/d/[A-Za-z0-9_-]+)")


def csv_export_url(sheet_url: str, gid: str | None) -> str:
    """Public CSV export URL of one tab of the Google Sheet at `sheet_url` (edit/share link).

    `https://<host>/spreadsheets/d/<id>/edit?...` -> `https://<host>/spreadsheets/d/<id>/export?format=csv[&gid=<gid>]`.
    Query and fragment of the input (usp=sharing, gid=...) are ignored: the tab is `gid`."""
    parts = urlsplit(sheet_url)
    match = _SHEET_PATH_RE.match(parts.path)
    if not (parts.scheme and parts.netloc and match):
        raise ValueError(f"not a Google Sheet URL (expected .../spreadsheets/d/<id>/...): {sheet_url!r}")
    query = "format=csv" + (f"&gid={gid}" if gid else "")
    return urlunsplit((parts.scheme, parts.netloc, f"{match.group(1)}/export", query, ""))


def sheet_urls() -> dict[str, str]:
    """{sheet name: CSV export URL}; raises SpreadsheetUrlNotConfigured when a variable is missing."""
    return {
        name: csv_export_url(spreadsheet_url(env_name), gid)
        for name, (env_name, gid) in TRACKED_SHEETS.items()
    }


# HTTP timeout per sheet fetch. Sheets are tiny but the Google edge can
# occasionally be slow; keep this short so a stuck tick never blocks the
# sensor daemon for long.
_HTTP_TIMEOUT_SEC = 15


def _fetch_sheet_hash(url: str) -> Optional[str]:
    """Download CSV export and return sha256 hex digest. None on any error.

    Errors are swallowed and logged-by-None because a transient network
    hiccup should skip the tick, not page the operator. Real outages will
    show up as repeated None across ticks — add explicit alerting later
    only if that becomes a pain point.
    """
    try:
        resp = requests.get(url, timeout=_HTTP_TIMEOUT_SEC, allow_redirects=True)
        resp.raise_for_status()
        return hashlib.sha256(resp.content).hexdigest()
    except Exception:
        return None


def _parse_cursor(raw: Optional[str]) -> dict[str, str]:
    if not raw:
        return {}
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else {}
    except (ValueError, TypeError):
        return {}


# Ticks every 5 minutes. Trade-off: sheets are edited a few times per week;
# 5 min latency is imperceptible to analysts waiting for dashboard refresh,
# and the polling cost is a rounding error against the Google CSV endpoint.
# Lower to 60s only if user feedback demands it.
@sensor(
    job_name="ingest_sheets_sync_job",
    minimum_interval_seconds=300,
    default_status=DefaultSensorStatus.RUNNING,  # auto-start on deploy
    description=(
        "Polls Google Sheets CSV exports via content hash. Fires "
        "ingest_sheets_sync_job only when a sheet's bytes actually change. "
        "See lessons-learned L21."
    ),
)
def ingest_sheets_modified_sensor(context: SensorEvaluationContext):
    """Detect sheet edits by comparing CSV content hashes to a cursor."""
    prev = _parse_cursor(context.cursor)
    current: dict[str, str] = {}
    errors: list[str] = []

    for name, url in sheet_urls().items():
        digest = _fetch_sheet_hash(url)
        if digest is None:
            errors.append(name)
            # Preserve prior hash so we don't fire spuriously once the
            # fetch recovers — we want a fire only on a real byte change.
            if name in prev:
                current[name] = prev[name]
            continue
        current[name] = digest

    # Cold start: record baseline, skip firing. This avoids a flood of
    # runs on first deploy or after cursor is cleared manually.
    if not prev:
        context.update_cursor(json.dumps(current))
        return SkipReason(
            f"Cold start — recorded baseline for {sorted(current.keys())}"
        )

    changed = [
        name
        for name, digest in current.items()
        if prev.get(name) != digest
    ]

    if not changed:
        if errors:
            return SkipReason(
                f"No changes; fetch errors for: {errors} (will retry next tick)"
            )
        return SkipReason("No sheet changes detected")

    # Always update cursor before firing — if the RunRequest is somehow
    # lost we still record the new hash and will re-fire on the next edit
    # rather than loop forever on the same hash.
    context.update_cursor(json.dumps(current))

    # run_key guarantees Dagster dedup: if an earlier tick already requested
    # a run with this same hash set, a duplicate is rejected silently.
    run_key = "sheets-modified-" + "-".join(
        f"{n}:{current[n][:12]}" for n in sorted(changed)
    )

    return RunRequest(
        run_key=run_key,
        tags={
            "concurrency_group": "dbt_rw",
            "source": "ingest_sheets_modified_sensor",
            "sheets_changed": ",".join(changed),
        },
    )

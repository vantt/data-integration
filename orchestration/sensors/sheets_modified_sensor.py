"""Sheets modified sensor — detect edits in Google Sheets via content hash.

Polls the public CSV export URL of each tracked sheet every N minutes,
computes a sha256 of the response body, and compares to a cursor of
last-known hashes. When any hash changes, fires a RunRequest for
`sheets_sync_job` (which cascades downstream into dbt + serving_db).

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

Alerts: failures propagate naturally — `lark_failure_sensor` will fire if
`sheets_sync_job` fails, and `stuck_run_sensor` catches hangs. No extra
logic here.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Optional

import requests
from dagster import (
    DefaultSensorStatus,
    RunRequest,
    SensorEvaluationContext,
    SkipReason,
    sensor,
)

# Public CSV export URLs — mirrored from ingestion/.dlt/config.toml
# Kept here (not re-read from dlt config) so the sensor has no hard dep on
# dlt's config resolution path. If URLs change, update both places.
_DEFAULT_TARGETS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1ZHt2iAD88OGgSRopVOkqEgusja-JpP4XqtiH4anhax4/export?format=csv"
)
_DEFAULT_MARKETING_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1wQpT4lCZWrPE7fnbRNTKiNDRFzVT2u_WhN-9uY9u3lc/export?format=csv"
)

SHEET_URLS = {
    "targets": os.environ.get("SHEETS_SENSOR_TARGETS_URL", _DEFAULT_TARGETS_URL),
    "marketing_spend": os.environ.get(
        "SHEETS_SENSOR_MARKETING_URL", _DEFAULT_MARKETING_URL
    ),
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
    job_name="sheets_sync_job",
    minimum_interval_seconds=300,
    default_status=DefaultSensorStatus.RUNNING,  # auto-start on deploy
    description=(
        "Polls Google Sheets CSV exports via content hash. Fires "
        "sheets_sync_job only when a sheet's bytes actually change. "
        "See lessons-learned L21."
    ),
)
def sheets_modified_sensor(context: SensorEvaluationContext):
    """Detect sheet edits by comparing CSV content hashes to a cursor."""
    prev = _parse_cursor(context.cursor)
    current: dict[str, str] = {}
    errors: list[str] = []

    for name, url in SHEET_URLS.items():
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
            "source": "sheets_modified_sensor",
            "sheets_changed": ",".join(changed),
        },
    )

"""Template: Dagster reactive sensor for external data source changes.

Use this when you want to trigger a job only when an external source
actually changes (e.g. Google Sheet edited, API dataset updated), without
polling the data every tick.

Pattern: content-hash polling.
  - Fetch a cheap representation of the source (CSV export, ETag, file size)
  - sha256 it
  - Compare to cursor; fire RunRequest only on change
  - run_key embeds the hash so Dagster dedupes automatic re-triggers

When NOT to use this template:
  - Source has a push webhook available — use webhook → RunRequest instead
  - Source is a file on local disk — use Dagster's file sensor
  - Source has reliable modifiedTime that is NOT bumped on cosmetic edits
    — use a metadata API call (cheaper than downloading the body)

Replace `SOURCE_URLS`, `JOB_NAME`, and `SENSOR_NAME` markers below.
See lessons-learned.md L21 for design rationale.
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

# -------- CONFIG --------

# Map friendly source name → fetch URL.
# Env var override lets operators point at a different env (staging/prod)
# without code changes.
SOURCE_URLS: dict[str, str] = {
    "source_a": os.environ.get("SENSOR_SOURCE_A_URL", "https://example.com/source-a.csv"),
    # "source_b": os.environ.get("SENSOR_SOURCE_B_URL", "..."),
}

# Short enough that a hung fetch doesn't block the sensor daemon.
# Sources should be small (< 1 MB); if larger, use a HEAD request
# with an ETag instead of downloading the body.
_HTTP_TIMEOUT_SEC = 15

# Tick interval. Trade-off: lower = faster reaction, higher = less network.
# For analyst-edited sources, 5 min is imperceptibly fast.
_TICK_INTERVAL_SEC = 300


# -------- FETCH + HASH --------


def _fetch_hash(url: str) -> Optional[str]:
    """Download URL and return sha256 hex digest. None on any error.

    Errors are deliberately swallowed into None so a transient network
    hiccup causes a SkipReason, not a sensor crash. Real outages show up
    as repeated None across ticks — add explicit alerting only if that
    becomes a pain point.
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


# -------- SENSOR --------


@sensor(
    job_name="REPLACE_WITH_YOUR_JOB_NAME",  # <<< REPLACE
    minimum_interval_seconds=_TICK_INTERVAL_SEC,
    # IMPORTANT: new sensors default to STOPPED. This line makes it
    # auto-start on deploy. Remove if you want operator to turn it on.
    default_status=DefaultSensorStatus.RUNNING,
    description=(
        "Polls external sources via content hash. Fires the target job "
        "only when a source's bytes actually change."
    ),
)
def REPLACE_WITH_SENSOR_NAME(context: SensorEvaluationContext):  # <<< REPLACE
    """Detect source changes by comparing content hashes to a cursor."""
    prev = _parse_cursor(context.cursor)
    current: dict[str, str] = {}
    errors: list[str] = []

    for name, url in SOURCE_URLS.items():
        digest = _fetch_hash(url)
        if digest is None:
            errors.append(name)
            # Preserve prior hash — error-then-recover must NOT fire
            # a spurious run if the bytes haven't actually changed.
            if name in prev:
                current[name] = prev[name]
            continue
        current[name] = digest

    # Cold start: record baseline, do NOT fire. Prevents a flood of runs
    # on first deploy or after manual cursor reset.
    if not prev:
        context.update_cursor(json.dumps(current))
        return SkipReason(f"Cold start — baseline recorded for {sorted(current.keys())}")

    changed = [name for name, digest in current.items() if prev.get(name) != digest]

    if not changed:
        if errors:
            return SkipReason(f"No changes; fetch errors: {errors} (retry next tick)")
        return SkipReason("No changes detected")

    # Update cursor BEFORE returning RunRequest — if the RunRequest is
    # somehow lost, we still recorded the new hash and won't loop forever.
    context.update_cursor(json.dumps(current))

    # run_key embeds the hash so Dagster dedupes: identical RunRequest
    # from a re-tick is silently rejected.
    run_key = "reactive-" + "-".join(
        f"{n}:{current[n][:12]}" for n in sorted(changed)
    )

    return RunRequest(
        run_key=run_key,
        tags={
            # Match your job's concurrency group so this run serializes
            # against other writers.
            "concurrency_group": "dbt_rw",
            "source": "REPLACE_WITH_SENSOR_NAME",  # <<< REPLACE
            "changed": ",".join(changed),
        },
    )

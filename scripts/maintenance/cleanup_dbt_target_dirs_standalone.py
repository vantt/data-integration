"""Purge stale transformation/target/ subdirectories, independent of Dagster.

Safety net for the accumulation that _cleanup_dbt_target_dirs() normally
handles once a day via maintain_cleanup_schedule (orchestration/ops/
purge_runs.py). That daily job runs INSIDE Dagster's code location, which
requires transformation/target/manifest.json to load — so if disk pressure
ever corrupts/deletes manifest.json, the code location fails to load and the
one job that would free disk space can't run either. Deadlock.

This script reuses the exact same _cleanup_dbt_target_dirs() logic (no
duplicated policy) but imports only orchestration.ops.purge_runs, which has
zero dependency on orchestration/definitions.py or the dbt manifest.

Two invocations, both wired into docker-compose.yml's command chain:
  1. Once, BEFORE `dbt parse` at container start — covers the case where
     manifest.json is already missing/corrupt when the container boots.
  2. As a background `--loop-seconds N` daemon started alongside `dagster
     dev` — covers the case where manifest.json goes missing WHILE the
     container keeps running for days without a restart (the Dagster-side
     daily job would stay blocked for that entire uptime otherwise; this
     loop is the only thing that self-heals it without an operator
     noticing and restarting the container).
Never raises — best-effort, like the other scripts/maintenance/*.py steps.
"""
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logging.basicConfig(level=logging.INFO, format='-> [dbt-target-cleanup] %(message)s')
log = logging.getLogger(__name__)


def cleanup_once() -> None:
    try:
        from orchestration.ops.purge_runs import _cleanup_dbt_target_dirs
    except Exception as exc:
        log.warning(f"import failed (non-fatal, skipping): {exc}")
        return

    keep_days = int(os.environ.get('PURGE_KEEP_DAYS', '1'))
    try:
        removed_count, freed_mb = _cleanup_dbt_target_dirs(keep_days, log)
        if removed_count:
            log.info(f"removed {removed_count} stale dirs, freed {freed_mb:.1f} MB")
        else:
            log.info("nothing to clean")
    except Exception as exc:
        log.warning(f"cleanup failed (non-fatal): {exc}")


def _parse_loop_seconds(argv: list[str]) -> int | None:
    for i, arg in enumerate(argv):
        if arg == "--loop-seconds" and i + 1 < len(argv):
            try:
                return int(argv[i + 1])
            except ValueError:
                return None
    return None


if __name__ == "__main__":
    loop_seconds = _parse_loop_seconds(sys.argv[1:])
    if loop_seconds is None:
        cleanup_once()
    else:
        log.info(f"running as a background loop, interval={loop_seconds}s")
        while True:
            cleanup_once()
            time.sleep(loop_seconds)

"""Purge stale transformation/target/ subdirectories at container startup.

Independent safety net for the accumulation that _cleanup_dbt_target_dirs()
normally handles once a day via maintain_purge_runs_schedule (orchestration/
ops/purge_runs.py). That daily job runs INSIDE Dagster's code location, which
requires transformation/target/manifest.json to load — so if disk pressure
ever corrupts/deletes manifest.json, the code location fails to load and the
one job that would free disk space can't run either. Deadlock.

This script reuses the exact same _cleanup_dbt_target_dirs() logic (no
duplicated policy) but imports only orchestration.ops.purge_runs, which has
zero dependency on orchestration/definitions.py or the dbt manifest — it runs
BEFORE `dbt parse` in the container command chain, so disk gets reclaimed
even when the Dagster-side daily job is itself blocked by the same disk
pressure. Never fails the container startup (best-effort, like the other
scripts/maintenance/*.py steps in docker-compose.yml's command chain).
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logging.basicConfig(level=logging.INFO, format='-> [dbt-target-cleanup] %(message)s')
log = logging.getLogger(__name__)


def cleanup() -> None:
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


if __name__ == "__main__":
    cleanup()

"""Dagster op for purging old runs and reclaiming storage."""
import os
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timedelta

from dagster import op, job, Out, Output, DagsterRunStatus


# Retry delays (seconds) for SQLite "database is locked" errors.
# 5 attempts; sleep after attempts 0-3 only (total wait 7.5s before final try).
_LOCK_RETRY_DELAYS = [0.5, 1.0, 2.0, 4.0, 8.0]


def _get_run_db_dir(instance):
    """Resolve the per-run SQLite directory from the Dagster instance.

    _base_dir IS the runs/ directory (e.g. dagster_home/history/runs/).
    Do NOT append 'runs' again.
    """
    storage = instance._event_storage
    if hasattr(storage, '_base_dir'):
        return storage._base_dir
    dagster_home = os.environ.get('DAGSTER_HOME', '')
    return os.path.join(dagster_home, 'history', 'runs')


def _get_storage_dir(instance):
    """Resolve the compute-log storage directory (stdout/stderr per run)."""
    dagster_home = os.environ.get('DAGSTER_HOME', '')
    return os.path.join(dagster_home, 'storage')


def _remove_run_db_files(instance, run_id: str) -> int:
    """Delete the per-run .db / .db-wal / .db-shm files for a given run_id."""
    run_dir = _get_run_db_dir(instance)
    removed = 0
    for ext in ('.db', '.db-wal', '.db-shm'):
        path = os.path.join(run_dir, run_id + ext)
        try:
            if os.path.exists(path):
                os.remove(path)
                removed += 1
        except OSError:
            pass
    return removed


def _remove_run_storage(instance, run_id: str) -> int:
    """Delete the storage/{run_id}/ directory (compute logs: stdout/stderr)."""
    storage_dir = _get_storage_dir(instance)
    run_storage = os.path.join(storage_dir, run_id)
    if os.path.isdir(run_storage):
        shutil.rmtree(run_storage, ignore_errors=True)
        return 1
    return 0


def _cleanup_orphans(instance, known_run_ids: set) -> tuple[int, int]:
    """Remove .db files and storage dirs with no matching run record.

    Uses the caller-supplied known_run_ids set to avoid re-querying the DB.
    """
    db_removed = 0
    storage_removed = 0

    run_dir = _get_run_db_dir(instance)
    if os.path.isdir(run_dir):
        for f in os.listdir(run_dir):
            if not f.endswith('.db') or f == 'index.db':
                continue
            run_id = f[:-3]
            if run_id in known_run_ids:
                continue
            for ext in ('.db', '.db-wal', '.db-shm'):
                path = os.path.join(run_dir, run_id + ext)
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        db_removed += 1
                except OSError:
                    pass

    storage_dir = _get_storage_dir(instance)
    if os.path.isdir(storage_dir):
        for d in os.listdir(storage_dir):
            if d not in known_run_ids and os.path.isdir(os.path.join(storage_dir, d)):
                shutil.rmtree(os.path.join(storage_dir, d), ignore_errors=True)
                storage_removed += 1

    return db_removed, storage_removed


def _cleanup_dbt_target_dirs(keep_days: int, log) -> tuple[int, float]:
    """Remove old sapo_dbt_assets-* directories from transformation/target/."""
    target_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'transformation', 'target'
    )
    if not os.path.isdir(target_dir):
        return 0, 0

    cutoff_ts = datetime.now().timestamp() - (keep_days * 86400)
    removed_count = 0
    freed_bytes = 0

    log.info(f"Scanning dbt target dirs in {target_dir}...")
    for name in os.listdir(target_dir):
        if not name.startswith('sapo_dbt_assets-'):
            continue
        dir_path = os.path.join(target_dir, name)
        if not os.path.isdir(dir_path):
            continue
        try:
            mtime = os.path.getmtime(dir_path)
            if mtime < cutoff_ts:
                dir_size = sum(
                    os.path.getsize(os.path.join(dp, f))
                    for dp, _, files in os.walk(dir_path)
                    for f in files
                )
                shutil.rmtree(dir_path, ignore_errors=True)
                removed_count += 1
                freed_bytes += dir_size
        except OSError:
            pass

    return removed_count, freed_bytes / (1024 * 1024)


def _vacuum_index_db(instance, log) -> tuple[float, float]:
    """VACUUM the per-run event log index to reclaim space after mass deletion.

    VACUUM runs in a background thread so we can emit heartbeat log events every
    30 s — without these the stuck-run alerter would kill us after 5 min of silence.
    """
    run_dir = _get_run_db_dir(instance)
    index_path = os.path.join(run_dir, 'index.db')
    if not os.path.exists(index_path):
        return 0, 0
    size_before = os.path.getsize(index_path) / (1024 * 1024)
    log.info(f"Starting VACUUM on index.db ({size_before:.1f} MB)...")

    _errors: list[Exception] = []
    _done = threading.Event()

    def _do_vacuum():
        try:
            conn = sqlite3.connect(index_path, timeout=30.0)
            conn.execute('PRAGMA busy_timeout = 30000')
            conn.execute('VACUUM')
            # Truncate WAL file to 0 bytes — VACUUM rebuilds the main file but leaves
            # the WAL on disk. TRUNCATE mode checkpoints and shrinks it to 0.
            result = conn.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            if result and result[0] == 1:
                # busy=1 is normal when the daemon has open WAL readers; SQLite's
                # auto-checkpoint will truncate on the next quiet moment.
                log.info("wal_checkpoint(TRUNCATE): active readers present, WAL will auto-truncate later")
            conn.close()
        except sqlite3.OperationalError as e:
            _errors.append(e)
        except Exception as e:
            _errors.append(e)
        finally:
            _done.set()

    t = threading.Thread(target=_do_vacuum, daemon=True)
    t.start()

    # Heartbeat: emit a log line every 30 s so the stuck-run alerter sees activity.
    elapsed = 0
    while not _done.wait(timeout=30):
        elapsed += 30
        log.info(f"VACUUM in progress... ({elapsed}s elapsed, {size_before:.1f} MB)")

    if _errors:
        e = _errors[0]
        if 'database is locked' in str(e).lower() or isinstance(e, sqlite3.OperationalError):
            log.warning(f"VACUUM skipped (database busy): {e}")
        else:
            log.warning(f"VACUUM failed: {e}")
        return size_before, size_before

    size_after = os.path.getsize(index_path) / (1024 * 1024)
    return size_before, size_after


# Only delete TERMINATED runs — never delete active/queued runs!
_TERMINATED_STATUSES = [
    DagsterRunStatus.SUCCESS,
    DagsterRunStatus.FAILURE,
    DagsterRunStatus.CANCELED,
]


def _delete_run_with_retry(instance, run_id: str, log) -> bool:
    """Delete run + events via public API, retrying on SQLite lock errors."""
    for attempt, wait in enumerate(_LOCK_RETRY_DELAYS):
        try:
            instance.delete_run(run_id)
            return True
        except Exception as e:
            if 'database is locked' not in str(e).lower():
                log.warning(f"Failed to delete run {run_id}: {e}")
                return False
            if attempt < len(_LOCK_RETRY_DELAYS) - 1:
                time.sleep(wait)
    log.warning(f"Giving up on run {run_id} after {len(_LOCK_RETRY_DELAYS)} retries (database locked)")
    return False


def _delete_events_with_retry(event_storage, run_id: str, log) -> bool:
    """Delete only event_log entries for a run_id, retrying on SQLite lock errors."""
    for attempt, wait in enumerate(_LOCK_RETRY_DELAYS):
        try:
            event_storage.delete_events(run_id)
            return True
        except Exception as e:
            if 'database is locked' not in str(e).lower():
                log.warning(f"Failed to delete events for {run_id}: {e}")
                return False
            if attempt < len(_LOCK_RETRY_DELAYS) - 1:
                time.sleep(wait)
    log.warning(f"Giving up on events for {run_id} after {len(_LOCK_RETRY_DELAYS)} retries (database locked)")
    return False


def _cleanup_orphan_event_entries(instance, known_run_ids: set, log) -> int:
    """Delete event_log rows in index.db whose run_id no longer exists in runs.db.

    This handles the partial-delete case: when delete_run() succeeded but
    delete_events() failed previously, leaving orphaned rows in index.db.
    """
    run_dir = _get_run_db_dir(instance)
    index_path = os.path.join(run_dir, 'index.db')
    if not os.path.exists(index_path):
        return 0

    # Find run_ids present in event_logs but not in runs.db.
    # DISTINCT scan on a large table can take 30–90 s — log before to show activity.
    log.info("Scanning event_logs for orphaned run_ids (may take a moment)...")
    try:
        conn = sqlite3.connect(index_path, timeout=30.0)
        conn.execute('PRAGMA busy_timeout = 30000')
        event_run_ids = set(
            row[0] for row in conn.execute('SELECT DISTINCT run_id FROM event_logs').fetchall()
        )
        conn.close()
    except sqlite3.OperationalError as e:
        log.warning(f"Could not query index.db for orphan detection: {e}")
        return 0

    orphan_ids = event_run_ids - known_run_ids
    if not orphan_ids:
        return 0

    log.info(f"Found {len(orphan_ids)} orphaned event-log run_ids, cleaning up")
    cleaned = 0
    for i, run_id in enumerate(orphan_ids):
        if _delete_events_with_retry(instance._event_storage, run_id, log):
            cleaned += 1
        if (i + 1) % 50 == 0:
            log.info(f"Orphan event cleanup progress: {i + 1}/{len(orphan_ids)}")

    log.info(f"Cleaned event_logs for {cleaned}/{len(orphan_ids)} orphaned run_ids")
    return cleaned


def _cleanup_orphan_asset_check_executions(instance, log) -> int:
    """Delete asset_check_executions rows whose run_id no longer exists in runs.db.

    Dagster's delete_run() does not touch this table, so it accumulates
    indefinitely. We join directly against runs.db to find orphans.
    """
    run_dir = _get_run_db_dir(instance)
    index_path = os.path.join(run_dir, 'index.db')
    runs_path = os.path.join(os.path.dirname(run_dir), 'runs.db')
    if not os.path.exists(index_path) or not os.path.exists(runs_path):
        return 0
    try:
        conn = sqlite3.connect(index_path, timeout=30.0)
        conn.execute('PRAGMA busy_timeout = 30000')
        conn.execute(f"ATTACH DATABASE '{runs_path}' AS runsdb")
        log.info("Cleaning orphaned asset_check_executions rows (cross-db DELETE)...")
        conn.execute("""
            DELETE FROM asset_check_executions
            WHERE run_id NOT IN (SELECT run_id FROM runsdb.runs)
        """)
        conn.commit()
        deleted = conn.execute("SELECT changes()").fetchone()[0]
        conn.close()
    except Exception as e:
        log.warning(f"asset_check_executions cleanup failed: {e}")
        return 0
    if deleted:
        log.info(f"Cleaned {deleted:,} orphaned asset_check_executions rows")
    return deleted


@op(out=Out(dict))
def maintain_purge_runs_op(context) -> dict:
    """Purge Dagster runs older than keep_days and reclaim storage."""
    keep_days = int(os.environ.get('PURGE_KEEP_DAYS', '1'))
    if keep_days < 1:
        keep_days = 1
        context.log.warning("PURGE_KEEP_DAYS < 1 is not allowed, using 1")
    cutoff_date = datetime.now() - timedelta(days=keep_days)

    # Log WAL size as an early warning — a large WAL (> 100 MB) means a previous
    # run was stuck or killed mid-operation and left the WAL uncheckpointed.
    run_dir = _get_run_db_dir(context.instance)
    wal_path = os.path.join(run_dir, 'index.db-wal')
    if os.path.exists(wal_path):
        wal_mb = os.path.getsize(wal_path) / (1024 * 1024)
        if wal_mb > 100:
            context.log.warning(f"index.db-wal is {wal_mb:.0f} MB — previous run may have been interrupted")
        else:
            context.log.info(f"index.db-wal: {wal_mb:.1f} MB (normal)")

    context.log.info(f"Purging runs older than {keep_days} days (cutoff: {cutoff_date})")

    from dagster import RunsFilter
    filters = RunsFilter(created_before=cutoff_date, statuses=_TERMINATED_STATUSES)
    records = context.instance.get_run_records(filters=filters, ascending=True)
    count = len(records)

    # Snapshot current known run IDs once — used by orphan cleanup below.
    # limit=10000 is a safe upper bound: at ~650 runs/day with 1-day keep window,
    # steady-state is ~1300 runs. 10K prevents OOM on an unexpected backlog.
    known_run_ids = set(
        r.run_id for r in context.instance.get_runs(limit=10000)
    )

    if count == 0:
        context.log.info("No runs to purge")
        orphan_db, orphan_storage = _cleanup_orphans(context.instance, known_run_ids)
        orphan_events = _cleanup_orphan_event_entries(context.instance, known_run_ids, context.log)
        orphan_checks = _cleanup_orphan_asset_check_executions(context.instance, context.log)
        size_before, size_after = _vacuum_index_db(context.instance, context.log)
        dbt_dirs_removed, dbt_mb_freed = _cleanup_dbt_target_dirs(keep_days, context.log)
        if dbt_dirs_removed:
            context.log.info(f"Cleaned {dbt_dirs_removed} dbt target dirs, freed {dbt_mb_freed:.1f} MB")
        return {
            "deleted_runs": 0,
            "db_files_removed": orphan_db,
            "storage_dirs_removed": orphan_storage,
            "orphan_event_entries_cleaned": orphan_events,
            "orphan_check_executions_cleaned": orphan_checks,
            "index_mb_before": size_before,
            "index_mb_after": size_after,
            "dbt_dirs_removed": dbt_dirs_removed,
            "dbt_mb_freed": dbt_mb_freed,
        }

    context.log.info(f"Found {count} runs to delete")

    deleted_count = 0
    db_files_removed = 0
    storage_dirs_removed = 0

    for i, rec in enumerate(records):
        run_id = rec.dagster_run.run_id
        if _delete_run_with_retry(context.instance, run_id, context.log):
            deleted_count += 1
            db_files_removed += _remove_run_db_files(context.instance, run_id)
            storage_dirs_removed += _remove_run_storage(context.instance, run_id)

        if (i + 1) % 50 == 0:
            context.log.info(f"Progress: {i + 1}/{count}")

    context.log.info(f"Deleted {deleted_count} runs, {db_files_removed} db files, {storage_dirs_removed} storage dirs")

    # Re-fetch known IDs after deletions for accurate orphan detection
    known_run_ids = set(
        r.run_id for r in context.instance.get_runs(limit=10000)
    )

    orphan_db, orphan_storage = _cleanup_orphans(context.instance, known_run_ids)
    if orphan_db or orphan_storage:
        db_files_removed += orphan_db
        storage_dirs_removed += orphan_storage
        context.log.info(f"Cleaned {orphan_db} orphan db files, {orphan_storage} orphan storage dirs")

    orphan_events = _cleanup_orphan_event_entries(context.instance, known_run_ids, context.log)
    orphan_checks = _cleanup_orphan_asset_check_executions(context.instance, context.log)

    size_before, size_after = _vacuum_index_db(context.instance, context.log)
    context.log.info(f"VACUUM index.db: {size_before:.1f} MB -> {size_after:.1f} MB")

    dbt_dirs_removed, dbt_mb_freed = _cleanup_dbt_target_dirs(keep_days, context.log)
    if dbt_dirs_removed:
        context.log.info(f"Cleaned {dbt_dirs_removed} dbt target dirs, freed {dbt_mb_freed:.1f} MB")

    return {
        "deleted_runs": deleted_count,
        "db_files_removed": db_files_removed,
        "storage_dirs_removed": storage_dirs_removed,
        "orphan_event_entries_cleaned": orphan_events,
        "orphan_check_executions_cleaned": orphan_checks,
        "index_mb_before": size_before,
        "index_mb_after": size_after,
        "dbt_dirs_removed": dbt_dirs_removed,
        "dbt_mb_freed": dbt_mb_freed,
    }


@job
def maintain_purge_runs_job():
    """Job that purges old Dagster runs. Configured via PURGE_KEEP_DAYS env var (default: 1)."""
    maintain_purge_runs_op()

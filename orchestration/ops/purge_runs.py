"""Dagster op for purging old runs and reclaiming storage."""
import os
import shutil
import sqlite3
from datetime import datetime, timedelta

from dagster import op, job, Out, Output, DagsterRunStatus


def _get_run_db_dir(instance):
    """Resolve the per-run SQLite directory from the Dagster instance."""
    storage = instance._event_storage
    if hasattr(storage, '_base_dir'):
        return os.path.join(storage._base_dir, 'runs')
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


def _cleanup_orphans(instance) -> tuple[int, int]:
    """Remove .db files and storage dirs with no matching run record."""
    known_ids = set(r.run_id for r in instance.get_runs(limit=999999))
    db_removed = 0
    storage_removed = 0

    run_dir = _get_run_db_dir(instance)
    if os.path.isdir(run_dir):
        for f in os.listdir(run_dir):
            if not f.endswith('.db') or f == 'index.db':
                continue
            run_id = f[:-3]
            if run_id in known_ids:
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
            if d not in known_ids and os.path.isdir(os.path.join(storage_dir, d)):
                shutil.rmtree(os.path.join(storage_dir, d), ignore_errors=True)
                storage_removed += 1

    return db_removed, storage_removed


def _vacuum_index_db(instance, log) -> tuple[float, float]:
    """VACUUM the per-run event log index to reclaim space after mass deletion."""
    run_dir = _get_run_db_dir(instance)
    index_path = os.path.join(run_dir, 'index.db')
    if not os.path.exists(index_path):
        return 0, 0
    size_before = os.path.getsize(index_path) / (1024 * 1024)
    try:
        conn = sqlite3.connect(index_path, timeout=10.0)
        conn.execute('VACUUM')
        conn.close()
    except sqlite3.OperationalError as e:
        log.warning(f"VACUUM skipped (database busy): {e}")
        return size_before, size_before
    except Exception as e:
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


@op(out=Out(dict))
def maintain_purge_runs_op(context) -> dict:
    """Purge Dagster runs older than keep_days and reclaim storage."""
    keep_days = int(os.environ.get('PURGE_KEEP_DAYS', '1'))
    if keep_days < 1:
        keep_days = 1
        context.log.warning("PURGE_KEEP_DAYS < 1 is not allowed, using 1")
    cutoff_date = datetime.now() - timedelta(days=keep_days)

    context.log.info(f"Purging runs older than {keep_days} days (cutoff: {cutoff_date})")

    from dagster import RunsFilter
    filters = RunsFilter(created_before=cutoff_date, statuses=_TERMINATED_STATUSES)
    records = context.instance.get_run_records(filters=filters, ascending=True)
    count = len(records)

    if count == 0:
        context.log.info("No runs to purge")
        orphan_db, orphan_storage = _cleanup_orphans(context.instance)
        size_before, size_after = _vacuum_index_db(context.instance, context.log)
        return {
            "deleted_runs": 0,
            "db_files_removed": orphan_db,
            "storage_dirs_removed": orphan_storage,
            "index_mb_before": size_before,
            "index_mb_after": size_after,
        }

    context.log.info(f"Found {count} runs to delete")

    deleted_count = 0
    db_files_removed = 0
    storage_dirs_removed = 0

    for i, rec in enumerate(records):
        run_id = rec.dagster_run.run_id
        try:
            context.instance._run_storage.delete_run(run_id)
            try:
                context.instance._event_storage.delete_events(run_id)
            except TypeError:
                pass
            deleted_count += 1
            db_files_removed += _remove_run_db_files(context.instance, run_id)
            storage_dirs_removed += _remove_run_storage(context.instance, run_id)

            if (i + 1) % 100 == 0:
                context.log.info(f"Progress: {i + 1}/{count}")
        except Exception as e:
            context.log.warning(f"Failed to delete run {run_id}: {e}")

    context.log.info(f"Deleted {deleted_count} runs, {db_files_removed} db files, {storage_dirs_removed} storage dirs")

    orphan_db, orphan_storage = _cleanup_orphans(context.instance)
    if orphan_db or orphan_storage:
        db_files_removed += orphan_db
        storage_dirs_removed += orphan_storage
        context.log.info(f"Cleaned {orphan_db} orphan db files, {orphan_storage} orphan storage dirs")

    size_before, size_after = _vacuum_index_db(context.instance, context.log)
    context.log.info(f"VACUUM index.db: {size_before:.1f} MB → {size_after:.1f} MB")

    return {
        "deleted_runs": deleted_count,
        "db_files_removed": db_files_removed,
        "storage_dirs_removed": storage_dirs_removed,
        "index_mb_before": size_before,
        "index_mb_after": size_after,
    }


@job
def maintain_purge_runs_job():
    """Job that purges old Dagster runs. Configured via PURGE_KEEP_DAYS env var (default: 1)."""
    maintain_purge_runs_op()

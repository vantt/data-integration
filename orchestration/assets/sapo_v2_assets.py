"""Dagster assets for Sapo ingestion via DLT batch runners.

Writes to ingestion_health via orchestration.ops.ingestion_health on every run.

CWD contract: each asset calls os.chdir(DLT_DIR) before invoking the DLT run
module, then restores the original CWD in a finally block. This is safe because
Dagster's multiprocess executor runs each step in an isolated child process.
NEVER switch these assets to in_process_executor — shared process CWD would
create races between concurrently executing in-process assets.
"""
from dagster import asset, Output, MetadataValue
import sys
import os
import time
import threading
from datetime import datetime, timezone
from orchestration.assets.utils import load_dlt_configuration, DLT_DIR
from orchestration.ops.ingestion_health import record_run as _record_health
from orchestration.ops.dlt_metrics import extract_rows_written, extract_loaded_packages

# How often (seconds) to emit a heartbeat log while a long-running dlt pipeline
# is blocking. Keeps the Dagster event log fresh so the stuck-run watchdog
# (INACTIVITY_THRESHOLD=5 min) does not false-positive kill the step.
_HEARTBEAT_INTERVAL_SEC = 120

# Add dlt dir to path
if DLT_DIR not in sys.path:
    sys.path.append(DLT_DIR)

try:
    import run_sapo_v2_orders_batch
    import run_sapo_v2_history_log
    import run_sapo_v2_webhook_consumer
    import run_sapo_v2_customers_batch
    import run_sapo_v2_accounts_batch
    import run_sapo_v2_products_batch
    import run_sapo_v2_inventory_transactions_batch
except ImportError as e:
    raise ImportError(f"Could not import dlt scripts from {DLT_DIR}. Error: {e}")


def _run_dlt_with_heartbeat(run_fn, log_fn, label: str):
    """Run a blocking dlt pipeline in a daemon thread, emitting heartbeat logs.

    dlt's run() can block for minutes without producing any Dagster events.
    When other steps in the same run finish first, the watchdog sees stale
    last-event-time and kills the run as stuck. Heartbeat logs keep the
    event log fresh so the watchdog (INACTIVITY_THRESHOLD=5 min) stays silent.
    """
    result: list = [None]
    error: list = [None]

    def _worker():
        try:
            result[0] = run_fn()
        except Exception as exc:
            error[0] = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    start = time.monotonic()
    while thread.is_alive():
        thread.join(timeout=_HEARTBEAT_INTERVAL_SEC)
        if thread.is_alive():
            elapsed = int(time.monotonic() - start)
            log_fn(f"[heartbeat] {label} still running ({elapsed}s elapsed)...")

    if error[0] is not None:
        raise error[0]
    return result[0]


def _build_metadata(loaded_packages: list, rows_written) -> dict:
    """Shared Dagster metadata dict for DLT batch assets."""
    records_status = "Data loaded" if loaded_packages else "0 new records"
    return {
        "fetch_status": MetadataValue.text(records_status),
        "packages_loaded": MetadataValue.int(len(loaded_packages)),
        "rows_written": (
            MetadataValue.int(rows_written)
            if rows_written is not None
            else MetadataValue.text("unknown")
        ),
    }


@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def ingest_sapo_v2_orders_batch_asset(context):
    """Daily batch sync for Sapo Orders.

    Captures 'modified_on' updates.
    When triggered by nightly reconciliation (tag full_refresh=true), resets cursor to scan all.
    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "sapo/ingest_sapo_v2_orders_batch_asset"
    started = datetime.now(timezone.utc)
    is_full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--reset-cursor"] if is_full_refresh else []
    context.log.info(f"Starting Sapo Orders Batch Sync... (full_refresh={is_full_refresh})")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    info_dict: dict = {}
    rows_written = None
    load_info = None
    try:
        try:
            os.chdir(DLT_DIR)
            load_info = run_sapo_v2_orders_batch.run(argv=argv)
        finally:
            os.chdir(cwd)

        info_dict = load_info.asdict() if hasattr(load_info, "asdict") else {}
        loaded_packages = extract_loaded_packages(info_dict)
        rows_written = extract_rows_written(info_dict)
        status = "success" if loaded_packages else "skipped"
        context.log.info(f"Orders Batch Sync Finished. Info: {load_info}")
        return Output(
            value="Orders Batch Sync Completed",
            metadata={
                **_build_metadata(loaded_packages, rows_written),
                "load_info": MetadataValue.text(str(load_info)),
            },
        )
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=rows_written,
                metadata={"full_refresh": is_full_refresh, "load_info": info_dict},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def ingest_sapo_v2_customers_batch_asset(context):
    """Daily batch sync for Sapo Customers.

    When triggered by nightly reconciliation (tag full_refresh=true), resets cursor to scan all.
    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "sapo/ingest_sapo_v2_customers_batch_asset"
    started = datetime.now(timezone.utc)
    is_full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--reset-cursor"] if is_full_refresh else []
    context.log.info(f"Starting Sapo Customers Batch Sync... (full_refresh={is_full_refresh})")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    info_dict: dict = {}
    rows_written = None
    try:
        try:
            os.chdir(DLT_DIR)
            load_info = run_sapo_v2_customers_batch.run(argv=argv)
        finally:
            os.chdir(cwd)

        info_dict = load_info.asdict() if hasattr(load_info, "asdict") else {}
        loaded_packages = extract_loaded_packages(info_dict)
        rows_written = extract_rows_written(info_dict)
        status = "success" if loaded_packages else "skipped"
        context.log.info(f"Customers Batch Sync Finished. Info: {load_info}")
        return Output(
            value="Customers Batch Sync Completed",
            metadata={
                **_build_metadata(loaded_packages, rows_written),
                "load_info": MetadataValue.text(str(load_info)),
            },
        )
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=rows_written,
                metadata={"full_refresh": is_full_refresh, "load_info": info_dict},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def ingest_sapo_v2_accounts_batch_asset(context):
    """Daily batch sync for Sapo Accounts (Staff).

    When triggered by nightly reconciliation (tag full_refresh=true), resets cursor to scan all.
    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "sapo/ingest_sapo_v2_accounts_batch_asset"
    started = datetime.now(timezone.utc)
    is_full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--reset-cursor"] if is_full_refresh else []
    context.log.info(f"Starting Sapo Accounts Batch Sync... (full_refresh={is_full_refresh})")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    info_dict: dict = {}
    rows_written = None
    try:
        try:
            os.chdir(DLT_DIR)
            load_info = run_sapo_v2_accounts_batch.run(argv=argv)
        finally:
            os.chdir(cwd)

        info_dict = load_info.asdict() if hasattr(load_info, "asdict") else {}
        loaded_packages = extract_loaded_packages(info_dict)
        rows_written = extract_rows_written(info_dict)
        status = "success" if loaded_packages else "skipped"
        context.log.info(f"Accounts Batch Sync Finished. Info: {load_info}")
        return Output(
            value="Accounts Batch Sync Completed",
            metadata={
                **_build_metadata(loaded_packages, rows_written),
                "load_info": MetadataValue.text(str(load_info)),
            },
        )
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=rows_written,
                metadata={"full_refresh": is_full_refresh, "load_info": info_dict},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def ingest_sapo_v2_products_batch_asset(context):
    """Daily batch sync for Sapo Products.

    Captures 'modified_on' updates.
    When triggered by nightly reconciliation (tag full_refresh=true), resets cursor to scan all.
    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "sapo/ingest_sapo_v2_products_batch_asset"
    started = datetime.now(timezone.utc)
    is_full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--reset-cursor"] if is_full_refresh else []
    context.log.info(f"Starting Sapo Products Batch Sync... (full_refresh={is_full_refresh})")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    info_dict: dict = {}
    rows_written = None
    try:
        try:
            os.chdir(DLT_DIR)
            load_info = run_sapo_v2_products_batch.run(argv=argv)
        finally:
            os.chdir(cwd)

        info_dict = load_info.asdict() if hasattr(load_info, "asdict") else {}
        loaded_packages = extract_loaded_packages(info_dict)
        rows_written = extract_rows_written(info_dict)
        status = "success" if loaded_packages else "skipped"
        context.log.info(f"Products Batch Sync Finished. Info: {load_info}")
        return Output(
            value="Products Batch Sync Completed",
            metadata={
                **_build_metadata(loaded_packages, rows_written),
                "load_info": MetadataValue.text(str(load_info)),
            },
        )
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=rows_written,
                metadata={"full_refresh": is_full_refresh, "load_info": info_dict},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def ingest_sapo_v2_history_log_asset(context):
    """Incremental poll of Sapo History Logs. Runs every 10 minutes to capture events.

    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "sapo/ingest_sapo_v2_history_log_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting History Log Poll...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    info_dict: dict = {}
    rows_written = None
    try:
        try:
            os.chdir(DLT_DIR)
            # Run dlt in a thread with heartbeat logs so the stuck-run watchdog
            # does not false-positive kill the step during long API polls.
            load_info = _run_dlt_with_heartbeat(
                run_fn=lambda: run_sapo_v2_history_log.run(argv=[]),
                log_fn=context.log.info,
                label="History Log Poll",
            )
        finally:
            os.chdir(cwd)

        info_dict = load_info.asdict() if hasattr(load_info, "asdict") else {}
        loaded_packages = extract_loaded_packages(info_dict)
        rows_written = extract_rows_written(info_dict)
        status = "success" if loaded_packages else "skipped"
        context.log.info(f"History Log Finished. Info: {load_info}")
        return Output(
            value="History Log Completed",
            metadata={
                **_build_metadata(loaded_packages, rows_written),
                "load_info": MetadataValue.text(str(load_info)),
            },
        )
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=rows_written,
                metadata={"load_info": info_dict},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def ingest_sapo_v2_inventory_transactions_asset(context):
    """Hourly batch sync for Sapo Inventory Transactions V2.

    Window is controlled by the 'inventory_window' run tag (default: 'hour').
    Nightly/fullrefresh jobs set inventory_window='day' to scan the full ICT day.
    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "sapo/ingest_sapo_v2_inventory_transactions_asset"
    started = datetime.now(timezone.utc)
    window = context.run.tags.get("inventory_window", "hour")
    argv = ["--window", window]
    context.log.info(f"Starting Sapo Inventory Transactions V2 Sync... (window={window})")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    info_dict: dict = {}
    rows_written = None
    load_info = None
    try:
        try:
            os.chdir(DLT_DIR)
            load_info = run_sapo_v2_inventory_transactions_batch.run(argv=argv)
        finally:
            os.chdir(cwd)

        info_dict = load_info.asdict() if hasattr(load_info, "asdict") else {}
        loaded_packages = extract_loaded_packages(info_dict)
        rows_written = extract_rows_written(info_dict)
        status = "success" if loaded_packages else "skipped"
        context.log.info(f"Inventory Transactions V2 Sync Finished. Info: {load_info}")
        return Output(
            value="Inventory Transactions V2 Sync Completed",
            metadata={
                **_build_metadata(loaded_packages, rows_written),
                "load_info": MetadataValue.text(str(load_info)),
            },
        )
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=rows_written,
                metadata={"inventory_window": window, "load_info": info_dict},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def ingest_sapo_v2_webhook_consumer_asset(context):
    """High-frequency poll of Cloudflare D1 Webhooks. Runs every minute.

    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "sapo/ingest_sapo_v2_webhook_consumer_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting Webhook Consumer One-Off Run...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    info_dict: dict = {}
    rows_written = None
    load_info = None
    try:
        try:
            os.chdir(DLT_DIR)
            load_info = run_sapo_v2_webhook_consumer.run(argv=["--once"])
        finally:
            os.chdir(cwd)

        info_dict = load_info.asdict() if load_info and hasattr(load_info, "asdict") else {}
        loaded_packages = extract_loaded_packages(info_dict)
        rows_written = extract_rows_written(info_dict)
        status = "success" if loaded_packages else "skipped"
        context.log.info(f"Webhook Poll Finished. Info: {load_info}")
        return Output(
            value="Webhook Poll Completed",
            metadata={
                **_build_metadata(loaded_packages, rows_written),
                "load_info": MetadataValue.text(str(load_info) if load_info else "No Data"),
            },
        )
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=rows_written,
                metadata={"load_info": info_dict},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")

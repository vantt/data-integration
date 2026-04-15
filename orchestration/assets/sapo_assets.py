from dagster import asset, Output, MetadataValue
import sys
import os
from datetime import datetime, timezone
from orchestration.assets.utils import load_dlt_configuration, DLT_DIR
from orchestration.ops.ingestion_health import record_run as _record_health

# Add dlt dir to path
if DLT_DIR not in sys.path:
    sys.path.append(DLT_DIR)

try:
    import run_orders_batch
    import run_history_log
    import run_webhook_consumer
    import run_customers_batch
    import run_customers_batch
    import run_accounts_batch
    import run_products_batch
    # removed gsheet imports
except ImportError as e:
    raise ImportError(f"Could not import dlt scripts from {DLT_DIR}. Error: {e}")

def _extract_rows_written(info_dict: dict) -> int | None:
    """Best-effort extraction of total rows written from a DLT LoadInfo dict.

    DLT doesn't expose a single top-level row count. We walk load_packages →
    jobs → (job_counts | metrics.items_count) and sum. Returns None if the
    shape doesn't match any known path — caller keeps the raw dict in
    metadata_json as a fallback for later forensic inspection.
    """
    total = 0
    matched = False
    for pkg in info_dict.get("load_packages", []) or []:
        jobs = pkg.get("jobs")
        if isinstance(jobs, dict):
            job_list = jobs.get("completed_jobs", []) or []
        elif isinstance(jobs, list):
            job_list = jobs
        else:
            job_list = []
        for job in job_list:
            metrics = job.get("metrics") if isinstance(job, dict) else None
            if isinstance(metrics, dict):
                n = metrics.get("items_count") or metrics.get("row_count")
                if isinstance(n, int):
                    total += n
                    matched = True
    return total if matched else None


@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_orders_batch_asset(context):
    """
    Daily batch sync for Sapo Orders.
    Captures 'modified_on' updates.
    When triggered by nightly reconciliation (tag full_refresh=true), resets cursor to scan all.
    """
    asset_key_str = "sapo/sapo_orders_batch_asset"
    started = datetime.now(timezone.utc)
    is_full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--full-refresh"] if is_full_refresh else []
    context.log.info(f"Starting Sapo Orders Batch Sync... (full_refresh={is_full_refresh})")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    info_dict: dict = {}
    rows_written: int | None = None
    try:
        try:
            os.chdir(DLT_DIR)
            load_info = run_orders_batch.run(argv=argv)
        finally:
            os.chdir(cwd)

        info_dict = load_info.asdict() if hasattr(load_info, 'asdict') else {}
        loaded_packages = info_dict.get('loads_ids', [])
        rows_written = _extract_rows_written(info_dict)
        status = "success" if loaded_packages else "skipped"
        records_status = "Data loaded" if len(loaded_packages) > 0 else "0 new records"
        context.log.info(f"Orders Batch Sync Finished. Info: {load_info}")
        return Output(
            value="Orders Batch Sync Completed",
            metadata={
                "fetch_status": MetadataValue.text(records_status),
                "packages_loaded": MetadataValue.int(len(loaded_packages)),
                "rows_written": MetadataValue.int(rows_written) if rows_written is not None else MetadataValue.text("unknown"),
                "load_info": MetadataValue.text(str(load_info))
            }
        )
    finally:
        # Best-effort health write — NEVER raise from here.
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=rows_written,
                metadata={
                    "full_refresh": is_full_refresh,
                    "load_info": info_dict,
                },
            )
        except Exception as _e:  # pragma: no cover
            context.log.warning(f"ingestion_health record_run failed: {_e}")

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_customers_batch_asset(context):
    """
    Daily batch sync for Sapo Customers.
    When triggered by nightly reconciliation (tag full_refresh=true), resets cursor to scan all.
    """
    is_full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--full-refresh"] if is_full_refresh else []
    context.log.info(f"Starting Sapo Customers Batch Sync... (full_refresh={is_full_refresh})")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_customers_batch.run(argv=argv)
    finally:
        os.chdir(cwd)
        
    info_dict = load_info.asdict() if hasattr(load_info, 'asdict') else {}
    loaded_packages = info_dict.get('loads_ids', [])
    records_status = "Data loaded" if len(loaded_packages) > 0 else "0 new records"

    context.log.info(f"Customers Batch Sync Finished. Info: {load_info}")
    return Output(
        value="Customers Batch Sync Completed", 
        metadata={
            "fetch_status": MetadataValue.text(records_status),
            "packages_loaded": MetadataValue.int(len(loaded_packages)),
            "load_info": MetadataValue.text(str(load_info))
        }
    )

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_accounts_batch_asset(context):
    """
    Daily batch sync for Sapo Accounts (Staff).
    When triggered by nightly reconciliation (tag full_refresh=true), resets cursor to scan all.
    """
    is_full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--full-refresh"] if is_full_refresh else []
    context.log.info(f"Starting Sapo Accounts Batch Sync... (full_refresh={is_full_refresh})")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_accounts_batch.run(argv=argv)
    finally:
        os.chdir(cwd)
        
    info_dict = load_info.asdict() if hasattr(load_info, 'asdict') else {}
    loaded_packages = info_dict.get('loads_ids', [])
    records_status = "Data loaded" if len(loaded_packages) > 0 else "0 new records"

    context.log.info(f"Accounts Batch Sync Finished. Info: {load_info}")
    return Output(
        value="Accounts Batch Sync Completed", 
        metadata={
            "fetch_status": MetadataValue.text(records_status),
            "packages_loaded": MetadataValue.int(len(loaded_packages)),
            "load_info": MetadataValue.text(str(load_info))
        }
    )

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_products_batch_asset(context):
    """
    Daily batch sync for Sapo Products.
    Captures 'modified_on' updates.
    When triggered by nightly reconciliation (tag full_refresh=true), resets cursor to scan all.
    """
    is_full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--full-refresh"] if is_full_refresh else []
    context.log.info(f"Starting Sapo Products Batch Sync... (full_refresh={is_full_refresh})")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_products_batch.run(argv=argv)
    finally:
        os.chdir(cwd)

    info_dict = load_info.asdict() if hasattr(load_info, 'asdict') else {}
    loaded_packages = info_dict.get('loads_ids', [])
    records_status = "Data loaded" if len(loaded_packages) > 0 else "0 new records"

    context.log.info(f"Products Batch Sync Finished. Info: {load_info}")
    return Output(
        value="Products Batch Sync Completed",
        metadata={
            "fetch_status": MetadataValue.text(records_status),
            "packages_loaded": MetadataValue.int(len(loaded_packages)),
            "load_info": MetadataValue.text(str(load_info))
        }
    )

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_history_log_asset(context):
    """
    Incremental poll of Sapo History Logs.
    Runs every 10 minutes to capture events.
    """
    context.log.info("Starting History Log Poll...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_history_log.run(argv=[])
    finally:
        os.chdir(cwd)
        
    info_dict = load_info.asdict() if hasattr(load_info, 'asdict') else {}
    loaded_packages = info_dict.get('loads_ids', [])
    records_status = "Data loaded" if len(loaded_packages) > 0 else "0 new records"

    context.log.info(f"History Log Finished. Info: {load_info}")
    return Output(
        value="History Log Completed",
        metadata={
            "fetch_status": MetadataValue.text(records_status),
            "packages_loaded": MetadataValue.int(len(loaded_packages)),
            "load_info": MetadataValue.text(str(load_info))
        }
    )

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_webhook_consumer_asset(context):
    """
    High-frequency poll of Cloudflare D1 Webhooks.
    Runs every minute.
    """
    context.log.info("Starting Webhook Consumer One-Off Run...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        # Use --once flag
        load_info = run_webhook_consumer.run(argv=['--once'])
    finally:
        os.chdir(cwd)
        
    info_dict = load_info.asdict() if load_info and hasattr(load_info, 'asdict') else {}
    loaded_packages = info_dict.get('loads_ids', [])
    records_status = "Data loaded" if len(loaded_packages) > 0 else "0 new records"

    context.log.info(f"Webhook Poll Finished. Info: {load_info}")
    return Output(
        value="Webhook Poll Completed",
        metadata={
            "fetch_status": MetadataValue.text(records_status),
            "packages_loaded": MetadataValue.int(len(loaded_packages)),
            "load_info": MetadataValue.text(str(load_info) if load_info else "No Data")
        }
    )

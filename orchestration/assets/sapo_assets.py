from dagster import asset, Output, MetadataValue
import sys
import os
from orchestration.assets.utils import load_dlt_configuration, DLT_DIR

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

@asset(group_name="sapo_ingestion", key_prefix=["sapo"])
def sapo_orders_batch_asset(context):
    """
    Daily batch sync for Sapo Orders.
    Captures 'modified_on' updates.
    When triggered by nightly reconciliation (tag full_refresh=true), resets cursor to scan all.
    """
    is_full_refresh = context.run.tags.get("full_refresh") == "true"
    argv = ["--full-refresh"] if is_full_refresh else []
    context.log.info(f"Starting Sapo Orders Batch Sync... (full_refresh={is_full_refresh})")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_orders_batch.run(argv=argv)
    finally:
        os.chdir(cwd)
        
    info_dict = load_info.asdict() if hasattr(load_info, 'asdict') else {}
    loaded_packages = info_dict.get('loads_ids', [])
    records_status = "Data loaded" if len(loaded_packages) > 0 else "0 new records"

    context.log.info(f"Orders Batch Sync Finished. Info: {load_info}")
    return Output(
        value="Orders Batch Sync Completed", 
        metadata={
            "fetch_status": MetadataValue.text(records_status),
            "packages_loaded": MetadataValue.int(len(loaded_packages)),
            "load_info": MetadataValue.text(str(load_info))
        }
    )

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

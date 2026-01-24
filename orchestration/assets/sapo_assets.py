from dagster import asset, Output, MetadataValue
import sys
import os

# Add dlt dir to path
# orchestration/assets/sapo_assets.py -> ../../dlt
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DLT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../dlt"))

if DLT_DIR not in sys.path:
    sys.path.append(DLT_DIR)

try:
    import run_orders_batch
    import run_history_log
    import run_webhook_consumer
    import run_customers_batch
    import run_accounts_batch
except ImportError as e:
    raise ImportError(f"Could not import dlt scripts from {DLT_DIR}. Error: {e}")

@asset(group_name="sapo_ingestion")
def sapo_orders_batch_asset(context):
    """
    Daily batch sync for Sapo Orders.
    Captures 'modified_on' updates.
    """
    context.log.info("Starting Sapo Orders Batch Sync...")
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_orders_batch.run()
    finally:
        os.chdir(cwd)
    context.log.info(f"Orders Batch Sync Finished. Info: {load_info}")
    return Output(
        value="Orders Batch Sync Completed", 
        metadata={
            "load_info": str(load_info)
        }
    )

@asset(group_name="sapo_ingestion")
def sapo_customers_batch_asset(context):
    """
    Daily batch sync for Sapo Customers.
    """
    context.log.info("Starting Sapo Customers Batch Sync...")
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_customers_batch.run()
    finally:
        os.chdir(cwd)
    context.log.info(f"Customers Batch Sync Finished. Info: {load_info}")
    return Output(
        value="Customers Batch Sync Completed", 
        metadata={
            "load_info": str(load_info)
        }
    )

@asset(group_name="sapo_ingestion")
def sapo_accounts_batch_asset(context):
    """
    Daily batch sync for Sapo Accounts (Staff).
    """
    context.log.info("Starting Sapo Accounts Batch Sync...")
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_accounts_batch.run()
    finally:
        os.chdir(cwd)
    context.log.info(f"Accounts Batch Sync Finished. Info: {load_info}")
    return Output(
        value="Accounts Batch Sync Completed", 
        metadata={
            "load_info": str(load_info)
        }
    )

@asset(group_name="sapo_ingestion")
def sapo_history_log_asset(context):
    """
    Incremental poll of Sapo History Logs.
    Runs every 10 minutes to capture events.
    """
    context.log.info("Starting History Log Poll...")
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_history_log.run()
    finally:
        os.chdir(cwd)
    context.log.info(f"History Log Finished. Info: {load_info}")
    return Output(
        value="History Log Completed",
        metadata={
            "load_info": str(load_info)
        }
    )

@asset(group_name="sapo_ingestion")
def sapo_webhook_consumer_asset(context):
    """
    High-frequency poll of Cloudflare D1 Webhooks.
    Runs every minute.
    """
    context.log.info("Starting Webhook Consumer One-Off Run...")
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        load_info = run_webhook_consumer.run_once()
    finally:
        os.chdir(cwd)
    context.log.info(f"Webhook Poll Finished. Info: {load_info}")
    return Output(
        value="Webhook Poll Completed",
        metadata={
            "load_info": str(load_info) if load_info else "No Data"
        }
    )

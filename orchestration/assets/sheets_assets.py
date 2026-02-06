from dagster import asset, Output
import sys
import os
from orchestration.assets.utils import load_dlt_configuration, DLT_DIR

# Add dlt dir to path (redundant but safe)
if DLT_DIR not in sys.path:
    sys.path.append(DLT_DIR)

try:
    import gsheet_targets
    import gsheet_marketing_spend
except ImportError as e:
    raise ImportError(f"Could not import dlt scripts from {DLT_DIR}. Error: {e}")

@asset(group_name="sheets_ingestion", key_prefix=["sheets"])
def sheets_targets_asset(context):
    """
    Manual/Scheduled sync for Google Sheet Targets.
    """
    context.log.info("Starting Google Sheet Targets Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        gsheet_targets.run()
        load_info = "Success"
    except Exception as e:
        context.log.error(f"Error: {e}")
        raise e
    finally:
        os.chdir(cwd)
    
    context.log.info(f"Targets Sync Finished.")
    return Output(
        value="Targets Sync Completed", 
        metadata={
            "status": "Success"
        }
    )

@asset(group_name="sheets_ingestion", key_prefix=["sheets"])
def sheets_marketing_spend_asset(context):
    """
    Manual/Scheduled sync for Google Sheet Marketing Spend.
    """
    context.log.info("Starting Google Sheet Marketing Spend Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        gsheet_marketing_spend.run()
        load_info = "Success"
    except Exception as e:
        context.log.error(f"Error: {e}")
        raise e
    finally:
        os.chdir(cwd)
    
    context.log.info(f"Marketing Spend Sync Finished.")
    return Output(
        value="Marketing Spend Sync Completed", 
        metadata={
            "status": "Success"
        }
    )

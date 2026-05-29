"""Dagster assets for Google Sheets ingestion via DLT gsheet runners.

Writes to ingestion_health via orchestration.ops.ingestion_health on every run.
rows_written=None for all Sheets assets: gsheet_* runners do not currently
surface row counts. TODO: update gsheet_targets.run() / gsheet_marketing_spend.run()
to return a count so this can be populated in a follow-up.
"""
from dagster import asset, Output, MetadataValue
import sys
import os
from datetime import datetime, timezone
from orchestration.assets.utils import load_dlt_configuration, DLT_DIR
from orchestration.ops.ingestion_health import record_run as _record_health

# Add dlt dir to path (redundant but safe)
if DLT_DIR not in sys.path:
    sys.path.append(DLT_DIR)

try:
    import gsheet_targets
    import gsheet_marketing_spend
    import gsheet_team_config
    import gsheet_us_shipment_prices
except ImportError as e:
    raise ImportError(f"Could not import dlt scripts from {DLT_DIR}. Error: {e}")


@asset(group_name="sheets_ingestion", key_prefix=["sheets"])
def sheets_targets_asset(context):
    """Manual/Scheduled sync for Google Sheet Targets.

    Writes to ingestion_health via orchestration.ops.ingestion_health.
    rows_written is None — gsheet runner does not expose count yet.
    """
    asset_key_str = "sheets/sheets_targets_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting Google Sheet Targets Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    try:
        try:
            os.chdir(DLT_DIR)
            gsheet_targets.run()
        finally:
            os.chdir(cwd)

        status = "success"
        context.log.info("Targets Sync Finished.")
        return Output(
            value="Targets Sync Completed",
            metadata={
                "status": MetadataValue.text("Success"),
                # TODO: surface row count from gsheet_targets.run() in a follow-up
                "rows_written": MetadataValue.text("unknown"),
            },
        )
    except Exception as e:
        context.log.error(f"Error: {e}")
        raise
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=None,  # gsheet runner doesn't surface count yet
                metadata={"gsheet_row_count": None},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


@asset(group_name="sheets_ingestion", key_prefix=["sheets"])
def sheets_marketing_spend_asset(context):
    """Manual/Scheduled sync for Google Sheet Marketing Spend.

    Writes to ingestion_health via orchestration.ops.ingestion_health.
    rows_written is None — gsheet runner does not expose count yet.
    """
    asset_key_str = "sheets/sheets_marketing_spend_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting Google Sheet Marketing Spend Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    try:
        try:
            os.chdir(DLT_DIR)
            gsheet_marketing_spend.run()
        finally:
            os.chdir(cwd)

        status = "success"
        context.log.info("Marketing Spend Sync Finished.")
        return Output(
            value="Marketing Spend Sync Completed",
            metadata={
                "status": MetadataValue.text("Success"),
                # TODO: surface row count from gsheet_marketing_spend.run() in a follow-up
                "rows_written": MetadataValue.text("unknown"),
            },
        )
    except Exception as e:
        context.log.error(f"Error: {e}")
        raise
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=None,  # gsheet runner doesn't surface count yet
                metadata={"gsheet_row_count": None},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


@asset(group_name="sheets_ingestion", key_prefix=["sheets"])
def sheets_team_config_asset(context):
    """Manual/Scheduled sync for Google Sheet Team Configuration.

    Ingests 2 tabs: teams (definitions) and team_members (SCD2 membership).
    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "sheets/sheets_team_config_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting Google Sheet Team Config Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    try:
        try:
            os.chdir(DLT_DIR)
            gsheet_team_config.run()
        finally:
            os.chdir(cwd)

        status = "success"
        context.log.info("Team Config Sync Finished.")
        return Output(
            value="Team Config Sync Completed",
            metadata={
                "status": MetadataValue.text("Success"),
                "rows_written": MetadataValue.text("unknown"),
            },
        )
    except Exception as e:
        context.log.error(f"Error: {e}")
        raise
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=None,
                metadata={"gsheet_row_count": None},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


@asset(group_name="sheets_ingestion", key_prefix=["sheets"])
def sheets_us_shipment_prices_asset(context):
    """Daily sync for US Shipment Price List Google Sheet.

    Ingests SKU-level US export prices with effective_from date versioning.
    Used to enrich US CrossBorder orders whose Sapo net_revenue is 0.
    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "sheets/sheets_us_shipment_prices_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting Google Sheet US Shipment Prices Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    try:
        try:
            os.chdir(DLT_DIR)
            gsheet_us_shipment_prices.run()
        finally:
            os.chdir(cwd)

        status = "success"
        context.log.info("US Shipment Prices Sync Finished.")
        return Output(
            value="US Shipment Prices Sync Completed",
            metadata={
                "status": MetadataValue.text("Success"),
                "rows_written": MetadataValue.text("unknown"),
            },
        )
    except Exception as e:
        context.log.error(f"Error: {e}")
        raise
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=None,
                metadata={"gsheet_row_count": None},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")

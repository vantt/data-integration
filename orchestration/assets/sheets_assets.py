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
    import gsheet_overhead_classification
    import gsheet_budget_sync
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


@asset(group_name="sheets_ingestion", key_prefix=["sheets"])
def sheets_overhead_classification_asset(context):
    """Nightly sync for Overhead Account Classification Google Sheet.

    Ingests MISA overhead sub-account classification rules (treatment, pool_id,
    base_metric) that control how each account is allocated in the P&L.
    Overwrites a full snapshot parquet on each run — the sheet is the live master.
    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "sheets/sheets_overhead_classification_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting Google Sheet Overhead Classification Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    try:
        try:
            os.chdir(DLT_DIR)
            gsheet_overhead_classification.run()
        finally:
            os.chdir(cwd)

        status = "success"
        context.log.info("Overhead Classification Sync Finished.")
        return Output(
            value="Overhead Classification Sync Completed",
            metadata={
                "status": MetadataValue.text("Success"),
                # TODO: surface row count from gsheet_overhead_classification.run() in a follow-up
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
def budget_sheet_sync_asset(context):
    """Daily sync for the Budget Sheet (BUDGET_ITEMS + ALLOCATION_POLICY tabs).

    Unlike the other sheets_* assets, this does NOT write to the gsheet_raw data lake —
    it writes directly to 2 dbt seed CSVs (transformation/seeds/seed_cashflow_budget.csv,
    seed_cash_allocation_policy.csv) so the nightly `dbt build` picks them up. Scheduled at
    02:30 ICT, 30 min before the nightly dbt build (03:00 ICT).

    Runs refresh_ref_accounts() FIRST — regenerates the hidden __REF tab's account-based
    dropdown rows from dim_gl_account/fact_cash_movement (phase-02) — so the BUDGET_ITEMS
    read below validates against the freshest account list. A refresh failure aborts the whole
    asset before touching BUDGET_ITEMS (fail loud, not silently stale).

    Validation is strict and fails loud: any bad sheet structure, a recurring line not
    found in the hidden __REF tab, or an ALLOCATION_POLICY gap/overlap/missing-remainder
    aborts the whole sync — neither seed file is touched. Writes to ingestion_health via
    orchestration.ops.ingestion_health.
    """
    asset_key_str = "sheets/budget_sheet_sync_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting Budget Sheet Sync...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    try:
        try:
            os.chdir(DLT_DIR)
            n_ref = gsheet_budget_sync.refresh_ref_accounts(dry_run=False)
            context.log.info(f"__REF refreshed: {n_ref} row(s).")
            gsheet_budget_sync.run()
        finally:
            os.chdir(cwd)

        status = "success"
        context.log.info("Budget Sheet Sync Finished.")
        return Output(
            value="Budget Sheet Sync Completed",
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
def budget_suggestion_writeback_asset(context):
    """Monthly write-back of the 'Gợi Ý' (suggestion) column into BUDGET_ITEMS (Phase 5).

    Computes a per-item suggestion for NEXT month and writes ONLY the 'Gợi Ý' cells —
    'Budget' is never touched (enforced by an assertion in gsheet_budget_sync._assert_gio_column):
      recurring : rolling 3-completed-month avg of actual amount from fact_cash_movement
      reserve   : has-a-deadline (item_target + target_month) -> required_monthly_adj from
                  mart_cashflow_reserve_status; target-only/open-ended -> no write
      one_off   : 0, except the item's own target_month (finance enters that one manually)

    Requires GOOGLE_SHEETS_SERVICE_ACCOUNT_KEY_PATH env var pointing at the shared GCP
    service-account JSON key, with EDITOR access on this sheet specifically — a materially
    higher privilege than the read-only budget_sheet_sync_asset (Viewer access is not enough
    to write). See plans/260707-1201-google-sheets-service-account/phase-01-service-account-setup.md
    for the credential setup. This asset is intentionally safe to register/import with zero
    credentials configured — it fails loud with a clear RuntimeError only at RUNTIME (inside
    gsheet_budget_sync.write_suggestions_to_sheet), never at Dagster code-load time, so a
    missing credential cannot break the asset graph.

    Scheduled 1st of month 08:00 ICT — after ingest_monthly_job (07:00 ICT) lands fresh MISA
    account-ledger actuals, so the rolling-avg/required_monthly_adj suggestions reflect the
    latest month's real numbers.
    """
    asset_key_str = "sheets/budget_suggestion_writeback_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting Budget Suggestion Write-back...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    n_written = 0
    try:
        try:
            os.chdir(DLT_DIR)
            n_written = gsheet_budget_sync.write_suggestions_to_sheet(dry_run=False)
        finally:
            os.chdir(cwd)

        status = "success"
        context.log.info(f"Budget Suggestion Write-back Finished. {n_written} cell(s) written.")
        return Output(
            value=f"{n_written} suggestion cell(s) written",
            metadata={
                "status": MetadataValue.text("Success"),
                "cells_written": MetadataValue.int(n_written),
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
                rows_written=n_written if status == "success" else None,
                metadata={"target": "budget_sheet_suggestions"},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")

"""Dagster assets for Hug ingestion via the hug_webhook_consumer DLT runner.

Mirrors ingest_sapo_v2_webhook_consumer_asset from sapo_assets.py.
Lands events into hug_raw/ (not sapo_v2_raw/) to avoid path collision.
"""

from dagster import asset, Output, MetadataValue
import sys
import os
from datetime import datetime, timezone

from orchestration.assets.utils import load_dlt_configuration, DLT_DIR
from orchestration.ops.ingestion_health import record_run as _record_health
from orchestration.ops.dlt_metrics import extract_rows_written, extract_loaded_packages

if DLT_DIR not in sys.path:
    sys.path.append(DLT_DIR)

try:
    import run_hug_webhook_consumer
except ImportError as e:
    raise ImportError(
        f"Could not import run_hug_webhook_consumer from {DLT_DIR}. Error: {e}"
    )


def _build_metadata(loaded_packages: list, rows_written) -> dict:
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


@asset(group_name="hug_ingestion", key_prefix=["hug"])
def ingest_hug_webhook_consumer_asset(context):
    """High-frequency poll of Cloudflare D1 Hug events (scan + opt-in).

    Lands events into hug_raw/ parquet (hug_scan, hug_optin_event tables).
    Runs on the same schedule cadence as the Sapo webhook consumer.
    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    asset_key_str = "hug/ingest_hug_webhook_consumer_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting Hug Webhook Consumer One-Off Run...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    status = "failed"
    info_dict: dict = {}
    rows_written = None
    load_info = None
    try:
        try:
            os.chdir(DLT_DIR)
            load_info = run_hug_webhook_consumer.run(argv=["--once"])
        finally:
            os.chdir(cwd)

        info_dict = load_info.asdict() if load_info and hasattr(load_info, "asdict") else {}
        loaded_packages = extract_loaded_packages(info_dict)
        rows_written = extract_rows_written(info_dict)
        status = "success" if loaded_packages else "skipped"
        context.log.info(f"Hug Webhook Poll Finished. Info: {load_info}")
        return Output(
            value="Hug Webhook Poll Completed",
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

"""Dagster assets for Shopee income file-drop ingestion.

Writes to ingestion_health via orchestration.ops.ingestion_health on every run.
File-drop variant: emits file_sha256, file_mtime, rows_fetched from xlsx source
files BEFORE the run module archives them.

Implemented as @multi_asset (4 outputs, one per parquet table) so each
shopee_raw dbt source can map to a unique AssetKey in SapoDbtTranslator,
enabling proper graph edges and .downstream() selection in the sync job.
"""

import importlib.util
import os
from datetime import datetime, timezone
from pathlib import Path

from dagster import multi_asset, AssetOut, AssetKey, Output, MetadataValue
from orchestration.assets.utils import load_dlt_configuration, DLT_DIR
from orchestration.ops.ingestion_health import record_run as _record_health
from orchestration.ops.file_metrics import scan_drop_zone, aggregate_file_manifest

# Input directory for Shopee drop zone — env var with Docker default.
# Local dev: set SHOPEE_INPUT_DIR in .env.local.
_SHOPEE_INPUT_DIR = os.environ.get(
    "SHOPEE_INPUT_DIR",
    str(Path(DLT_DIR).parent / "app_data" / "input_source" / "shopee"),
)
if not os.path.isdir(_SHOPEE_INPUT_DIR):
    _SHOPEE_INPUT_DIR = "/app/var/input_source/shopee"


def _import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Lazy-load to avoid import-time side effects
_run_module = None


def _get_run_module():
    global _run_module
    if _run_module is None:
        _run_module = _import_from_file(
            "run_shopee_income_file_drop",
            os.path.join(DLT_DIR, "run-shopee-income-file-drop.py"),
        )
    return _run_module


@multi_asset(
    outs={
        "order_revenue": AssetOut(
            key=AssetKey(["shopee", "order_revenue"]),
            description="Shopee order-level revenue & fees (Doanh thu sheet, Order rows)",
        ),
        "order_revenue_items": AssetOut(
            key=AssetKey(["shopee", "order_revenue_items"]),
            description="Shopee order × product line items (Doanh thu sheet, Sku rows)",
        ),
        "order_service_fees": AssetOut(
            key=AssetKey(["shopee", "order_service_fees"]),
            description="Shopee extra service fees: infrastructure + Xtra voucher",
        ),
        "order_adjustments": AssetOut(
            key=AssetKey(["shopee", "order_adjustments"]),
            description="Shopee order-level adjustments: marketing fees, compensations",
        ),
    },
    group_name="shopee_ingestion",
)
def shopee_income_file_drop_asset(context):
    """Ingest Shopee released-income Excel files from the drop zone.

    Parses xlsx -> 4 parquet tables (order_revenue, order_revenue_items, order_service_fees, order_adjustments).
    Append-only writes; source files archived to _archive/ on success.
    Writes to ingestion_health via orchestration.ops.ingestion_health.
    """
    # Kept as a stable identifier for the health DB (backward compatible).
    asset_key_str = "shopee/shopee_income_file_drop_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting Shopee income file-drop ingestion...")
    load_dlt_configuration(context.log.info)

    # --- Scan drop zone BEFORE run module archives files ---
    file_entries: list = []
    manifest: dict = {}
    try:
        file_entries = scan_drop_zone(_SHOPEE_INPUT_DIR)
        manifest = aggregate_file_manifest(file_entries)
        context.log.info(
            f"Shopee drop zone: {len(file_entries)} file(s), "
            f"rows_fetched={manifest.get('rows_fetched')}"
        )
    except Exception as exc:
        context.log.warning(f"Shopee file metrics scan failed (non-fatal): {exc}")
        manifest = {"file_sha256": None, "file_mtime": None, "rows_fetched": None, "manifest": []}

    cwd = os.getcwd()
    status = "failed"
    try:
        try:
            os.chdir(DLT_DIR)
            _get_run_module().run(argv=[])
        finally:
            os.chdir(cwd)

        status = "success" if file_entries else "skipped"
        context.log.info("Shopee income file-drop ingestion complete.")

        output_metadata = {
            "status": MetadataValue.text("Success"),
            "files_processed": MetadataValue.int(len(file_entries)),
            "rows_fetched": (
                MetadataValue.int(manifest["rows_fetched"])
                if manifest.get("rows_fetched") is not None
                else MetadataValue.text("unknown")
            ),
            "file_sha256": MetadataValue.text(manifest.get("file_sha256") or "unknown"),
        }
        yield Output("OK", output_name="order_revenue", metadata=output_metadata)
        yield Output("OK", output_name="order_revenue_items", metadata=output_metadata)
        yield Output("OK", output_name="order_service_fees", metadata=output_metadata)
        yield Output("OK", output_name="order_adjustments", metadata=output_metadata)

    except Exception as exc:
        context.log.error(f"Shopee ingestion error: {exc}")
        raise
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_fetched=manifest.get("rows_fetched"),
                file_sha256=manifest.get("file_sha256"),
                file_mtime=manifest.get("file_mtime"),
                metadata={"file_manifest": manifest.get("manifest", [])},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")

"""Dagster assets for MISA AMIS sales ledger file-drop ingestion.

Writes to ingestion_health via orchestration.ops.ingestion_health on every run.
Sensor fires one run per file; file_path is passed via MisaFiledropConfig.
"""

import importlib.util
import os
from datetime import datetime, timezone
from pathlib import Path

from dagster import asset, Output, MetadataValue, Config
from orchestration.assets.utils import load_dlt_configuration, DLT_DIR
from orchestration.ops.ingestion_health import record_run as _record_health
from orchestration.ops.file_metrics import hash_and_count_xlsx, scan_drop_zone, aggregate_file_manifest

# Input directory for MISA AMIS drop zone — env var with Docker default.
# Local dev: set MISA_INPUT_DIR in .env.local.
_MISA_INPUT_DIR = os.environ.get(
    "MISA_INPUT_DIR",
    str(Path(DLT_DIR).parent / "app_data" / "input_source" / "misa-amis"),
)
if not os.path.isdir(_MISA_INPUT_DIR):
    _MISA_INPUT_DIR = "/app/var/input_source/misa-amis"


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
            "run_misa_sales_file_drop",
            os.path.join(DLT_DIR, "run-misa-sales-file-drop.py"),
        )
    return _run_module


class MisaFiledropConfig(Config):
    file_path: str = ""


@asset(group_name="misa_amis_ingestion", key_prefix=["misa_amis"])
def misa_sales_file_drop_asset(context, config: MisaFiledropConfig):
    """Ingest one MISA AMIS sales ledger Excel file from the drop zone.

    Sensor fires one run per file via config.file_path. When triggered
    manually without config (file_path=""), processes all files in drop zone.
    """
    asset_key_str = "misa_amis/misa_sales_file_drop_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting MISA sales ledger file-drop ingestion...")
    load_dlt_configuration(context.log.info)

    # Scan file metrics BEFORE run module archives the file
    file_entries: list = []
    manifest: dict = {}
    try:
        if config.file_path:
            if os.path.exists(config.file_path):
                metrics = hash_and_count_xlsx(config.file_path)
                file_entries = [{"path": config.file_path, **metrics}]
            else:
                context.log.warning(f"File not found: {config.file_path}")
        else:
            file_entries = scan_drop_zone(_MISA_INPUT_DIR)
        manifest = aggregate_file_manifest(file_entries)
        context.log.info(
            f"MISA drop zone: {len(file_entries)} file(s), "
            f"rows_fetched={manifest.get('rows_fetched')}"
        )
    except Exception as exc:
        context.log.warning(f"MISA file metrics scan failed (non-fatal): {exc}")
        manifest = {"file_sha256": None, "file_mtime": None, "rows_fetched": None, "manifest": []}

    run_argv = ["--file", config.file_path] if config.file_path else []
    cwd = os.getcwd()
    status = "failed"
    try:
        try:
            os.chdir(DLT_DIR)
            _get_run_module().run(argv=run_argv)
        finally:
            os.chdir(cwd)

        status = "success" if file_entries else "skipped"
        context.log.info("MISA sales ledger file-drop ingestion complete.")
        return Output(
            "OK",
            metadata={
                "status": MetadataValue.text("Success"),
                "files_processed": MetadataValue.int(len(file_entries)),
                "rows_fetched": (
                    MetadataValue.int(manifest["rows_fetched"])
                    if manifest.get("rows_fetched") is not None
                    else MetadataValue.text("unknown")
                ),
                "file_sha256": MetadataValue.text(manifest.get("file_sha256") or "unknown"),
            },
        )
    except Exception as exc:
        context.log.error(f"MISA ingestion error: {exc}")
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

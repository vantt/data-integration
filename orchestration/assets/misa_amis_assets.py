"""Dagster assets for MISA AMIS ingestion:
  - misa_sales_download_asset: Playwright browser automation downloads weekly sales ledger
  - misa_sales_file_drop_asset: parses Excel and writes parquet (sensor-triggered)
  - misa_account_ledger_file_drop_asset: parses account-ledger Excel
"""

import importlib.util
import os
from datetime import datetime, timezone
from pathlib import Path

from dagster import asset, Output, MetadataValue, Config
from orchestration.assets.utils import load_dlt_configuration, DLT_DIR
from orchestration.ops.ingestion_health import record_run as _record_health
from orchestration.ops.file_metrics import hash_and_count_xlsx, scan_drop_zone, aggregate_file_manifest

# ── Sales-ledger drop zone ─────────────────────────────────────────────────────
# Input directory for MISA sales-ledger — env var with Docker default.
# Local dev: set MISA_INPUT_DIR in .env.local.
_MISA_INPUT_DIR = os.environ.get(
    "MISA_INPUT_DIR",
    str(Path(DLT_DIR).parent / "app_data" / "input_source" / "misa-sales-ledger"),
)
if not os.path.isdir(_MISA_INPUT_DIR):
    _MISA_INPUT_DIR = "/app/var/input_source/misa-sales-ledger"

# ── Account-ledger drop zone ───────────────────────────────────────────────────
# Separate folder, separate env var — routing by folder, not content sniffing.
# Local dev: set MISA_ACCOUNT_LEDGER_INPUT_DIR in .env.local.
_MISA_ACCOUNT_LEDGER_INPUT_DIR = os.environ.get(
    "MISA_ACCOUNT_LEDGER_INPUT_DIR",
    str(Path(DLT_DIR).parent / "app_data" / "input_source" / "misa-account-ledger"),
)
if not os.path.isdir(_MISA_ACCOUNT_LEDGER_INPUT_DIR):
    _MISA_ACCOUNT_LEDGER_INPUT_DIR = "/app/var/input_source/misa-account-ledger"


def _import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Lazy-loaded run modules ────────────────────────────────────────────────────
# download module — loaded on first use to avoid importing Playwright at startup

_run_download_module = None
_run_account_ledger_download_module = None


def _get_run_download_module():
    global _run_download_module
    if _run_download_module is None:
        _run_download_module = _import_from_file(
            "run_misa_sales_download",
            os.path.join(DLT_DIR, "run-misa-sales-download.py"),
        )
    return _run_download_module


def _get_run_account_ledger_download_module():
    global _run_account_ledger_download_module
    if _run_account_ledger_download_module is None:
        _run_account_ledger_download_module = _import_from_file(
            "run_misa_account_ledger_download",
            os.path.join(DLT_DIR, "run-misa-account-ledger-download.py"),
        )
    return _run_account_ledger_download_module

_run_module = None
_run_account_ledger_module = None


def _get_run_module():
    global _run_module
    if _run_module is None:
        _run_module = _import_from_file(
            "run_misa_sales_file_drop",
            os.path.join(DLT_DIR, "run-misa-sales-file-drop.py"),
        )
    return _run_module


def _get_run_account_ledger_module():
    global _run_account_ledger_module
    if _run_account_ledger_module is None:
        _run_account_ledger_module = _import_from_file(
            "run_misa_account_ledger_file_drop",
            os.path.join(DLT_DIR, "run-misa-account-ledger-file-drop.py"),
        )
    return _run_account_ledger_module


# ── Weekly download asset ─────────────────────────────────────────────────────

@asset(group_name="misa_amis_ingestion", key_prefix=["misa_amis"])
def misa_sales_download_asset(context):
    """Download 'Sổ chi tiết bán hàng' Excel from MISA AMIS web portal.

    Runs headless Playwright, selects 'Tuần Trước', exports Excel, and drops
    the file into the misa-sales-ledger input directory. The file-drop sensor
    then picks it up and triggers misa_sales_file_drop_asset automatically.

    Scheduled weekly: Monday 07:00 ICT (previous Mon–Sun range).
    """
    asset_key_str = "misa_amis/misa_sales_download_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting MISA sales ledger weekly download...")

    status = "failed"
    rows_fetched = None
    file_sha256 = None
    saved_path = None
    try:
        cwd = os.getcwd()
        try:
            os.chdir(DLT_DIR)
            _get_run_download_module().run(argv=[])  # headless=True (default), period=tuan_truoc
        finally:
            os.chdir(cwd)

        # Scan the drop zone to get file metadata for Dagster metadata panel
        drop_files = scan_drop_zone(_MISA_INPUT_DIR)
        if drop_files:
            latest = max(drop_files, key=lambda e: e.get("file_mtime") or 0)
            saved_path = latest.get("path")
            rows_fetched = latest.get("rows_fetched")
            file_sha256 = latest.get("file_sha256")

        status = "success"
        context.log.info(f"MISA download complete: {saved_path}")
        return Output(
            saved_path or "OK",
            metadata={
                "status": MetadataValue.text("Success"),
                "saved_path": MetadataValue.text(str(saved_path) if saved_path else "unknown"),
                "file_sha256": MetadataValue.text(file_sha256 or "unknown"),
            },
        )
    except Exception as exc:
        context.log.error(f"MISA download error: {exc}")
        raise
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_fetched=rows_fetched,
                file_sha256=file_sha256,
                file_mtime=None,
                metadata={"saved_path": str(saved_path) if saved_path else None},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


class MisaAccountLedgerDownloadConfig(Config):
    account: str = "642"  # prefix: "642" → all 6421*/6422* sub-accounts


@asset(group_name="misa_amis_ingestion", key_prefix=["misa_amis"])
def misa_account_ledger_download_asset(context, config: MisaAccountLedgerDownloadConfig):
    """Download 'Sổ chi tiết tài khoản' Excel from MISA AMIS web portal.

    Searches account prefix (default '642' → all 6421*/6422*), selects ALL
    matching sub-accounts via 'Chọn tất cả tài khoản' (.row-check-all),
    exports So_chi_tiet_{account}_{YYYYMM}.xlsx into the account-ledger
    input directory. The file-drop sensor picks it up automatically.

    Scheduled monthly: 1st of each month 07:00 ICT.
    """
    asset_key_str = "misa_amis/misa_account_ledger_download_asset"
    started = datetime.now(timezone.utc)
    context.log.info(f"Starting MISA account-ledger download (account={config.account})...")

    status = "failed"
    saved_path = None
    try:
        cwd = os.getcwd()
        try:
            os.chdir(DLT_DIR)
            _get_run_account_ledger_download_module().run(argv=["--account", config.account])
        finally:
            os.chdir(cwd)

        drop_files = scan_drop_zone(_MISA_ACCOUNT_LEDGER_INPUT_DIR)
        if drop_files:
            latest = max(drop_files, key=lambda e: e.get("file_mtime") or 0)
            saved_path = latest.get("path")

        status = "success"
        context.log.info(f"MISA account-ledger download complete: {saved_path}")
        return Output(
            saved_path or "OK",
            metadata={
                "status": MetadataValue.text("Success"),
                "account": MetadataValue.text(config.account),
                "saved_path": MetadataValue.text(str(saved_path) if saved_path else "unknown"),
            },
        )
    except Exception as exc:
        context.log.error(f"MISA account-ledger download error: {exc}")
        raise
    finally:
        try:
            _record_health(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_fetched=None,
                file_sha256=None,
                file_mtime=None,
                metadata={"saved_path": str(saved_path) if saved_path else None},
            )
        except Exception as _e:
            context.log.warning(f"ingestion_health record_run failed: {_e}")


class MisaFiledropConfig(Config):
    file_path: str = ""


# ── Sales-ledger asset ─────────────────────────────────────────────────────────

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
            f"MISA sales drop zone: {len(file_entries)} file(s), "
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


# ── Account-ledger asset ───────────────────────────────────────────────────────

@asset(group_name="misa_amis_ingestion", key_prefix=["misa_amis"])
def misa_account_ledger_file_drop_asset(context, config: MisaFiledropConfig):
    """Ingest one MISA account-ledger Excel file ('Sổ chi tiết các tài khoản') from the drop zone.

    Writes to misa_raw/account_ledger (grain: journal line, partition year/month).
    Idempotency is ALWAYS ON: touched (year, month) partitions are replaced before write.
    Sensor fires one run per file via config.file_path. When triggered manually without
    config (file_path=""), processes all files in the account-ledger drop zone.
    """
    asset_key_str = "misa_amis/misa_account_ledger_file_drop_asset"
    started = datetime.now(timezone.utc)
    context.log.info("Starting MISA account-ledger file-drop ingestion...")
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
            file_entries = scan_drop_zone(_MISA_ACCOUNT_LEDGER_INPUT_DIR)
        manifest = aggregate_file_manifest(file_entries)
        context.log.info(
            f"MISA account-ledger drop zone: {len(file_entries)} file(s), "
            f"rows_fetched={manifest.get('rows_fetched')}"
        )
    except Exception as exc:
        context.log.warning(f"MISA account-ledger file metrics scan failed (non-fatal): {exc}")
        manifest = {"file_sha256": None, "file_mtime": None, "rows_fetched": None, "manifest": []}

    run_argv = ["--file", config.file_path] if config.file_path else []
    cwd = os.getcwd()
    status = "failed"
    try:
        try:
            os.chdir(DLT_DIR)
            _get_run_account_ledger_module().run(argv=run_argv)
        finally:
            os.chdir(cwd)

        status = "success" if file_entries else "skipped"
        context.log.info("MISA account-ledger file-drop ingestion complete.")
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
        context.log.error(f"MISA account-ledger ingestion error: {exc}")
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

"""Dagster assets for Shopee income file-drop ingestion."""

import importlib.util
import os
import sys

from dagster import asset, Output
from orchestration.assets.utils import load_dlt_configuration, DLT_DIR


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


@asset(group_name="shopee_ingestion", key_prefix=["shopee"])
def shopee_income_file_drop_asset(context):
    """Ingest Shopee released-income Excel files from the drop zone.

    Parses xlsx → 3 parquet tables (order_revenue, order_revenue_items, order_service_fees).
    Append-only writes; source files archived to _archive/ on success.
    """
    context.log.info("Starting Shopee income file-drop ingestion...")
    load_dlt_configuration(context.log.info)
    cwd = os.getcwd()
    try:
        os.chdir(DLT_DIR)
        _get_run_module().run(argv=[])
    except Exception as e:
        context.log.error(f"Shopee ingestion error: {e}")
        raise
    finally:
        os.chdir(cwd)

    context.log.info("Shopee income file-drop ingestion complete.")
    return Output("OK", metadata={"status": "Success"})

"""CRM pack: the warehouse side of the CRM app (crm/).

crm_writeback_assets exports CRM SQLite tables to data_lake/crm_export/ for the pack's dbt
models (transformation/models/packs/crm/); crm_sync triggers the CRM cache refresh after the
serving layer is rebuilt and runs the daily CRM backup + restore drill (jobs.py).
"""
from dagster import load_assets_from_modules

from . import crm_sync, crm_writeback_assets

_WRITEBACK_ASSETS = load_assets_from_modules([crm_writeback_assets])

ASSETS = [
    crm_sync.crm_cache_refresh,
    crm_sync.crm_backup,
    crm_sync.crm_restore_verify,
    *_WRITEBACK_ASSETS,
]

# Run after build_serving_db by every connector sync job that rebuilds serving
# (job_support.after_serving_selection()): the CRM app re-reads the refreshed serving views.
AFTER_SERVING_ASSETS = [crm_sync.crm_cache_refresh]

# Run by pipeline_batch_nightly_job / pipeline_batch_fullrefresh_job: export CRM tables before
# dbt, refresh the CRM cache after serving.
NIGHTLY_ASSETS = [*_WRITEBACK_ASSETS, crm_sync.crm_cache_refresh]

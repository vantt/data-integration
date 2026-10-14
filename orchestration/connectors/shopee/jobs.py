import os

from dagster import AssetSelection, define_asset_job

from orchestration.assets import serving
from orchestration.packs.crm import crm_sync
from orchestration.job_support import FACT_ORDER_RETURNS, SYNC_TAGS
from orchestration.sensors.file_drop_sensors import make_file_drop_sensor

from .assets import shopee_income_file_drop_asset

# 2.6 Shopee file-drop sync job
# Ingests Shopee income Excel → dbt (shopee chain only) → serving_db.
# shopee_income_file_drop_asset is a @multi_asset with 4 outputs (one per table),
# so .downstream() resolves only shopee-dependent dbt models — not the full graph.
_shopee_source = AssetSelection.assets(shopee_income_file_drop_asset)
ingest_filedrop_shopee_job = define_asset_job(
    name="ingest_filedrop_shopee_job",
    selection=(
        _shopee_source
        | _shopee_source.downstream()
        | FACT_ORDER_RETURNS
        | AssetSelection.assets(serving.build_serving_db)
        | AssetSelection.assets(crm_sync.crm_cache_refresh)
    ),
    tags=SYNC_TAGS,
)

# Env var if set, otherwise Docker default (/app/var/input_source/).
# Local dev: set SHOPEE_INPUT_DIR in .env.local.
ingest_filedrop_shopee_sensor = make_file_drop_sensor(
    name="ingest_filedrop_shopee_sensor",
    job_name="ingest_filedrop_shopee_job",
    input_dir=os.environ.get("SHOPEE_INPUT_DIR", "/app/var/input_source/shopee"),
    asset_op_name="shopee_income_file_drop_asset",
    run_key_prefix="shopee",
    source_label="Shopee",
    drop_dir_hint="shopee",
)

JOBS = [ingest_filedrop_shopee_job]
SCHEDULES = []
SENSORS = [ingest_filedrop_shopee_sensor]

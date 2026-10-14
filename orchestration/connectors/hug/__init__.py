"""Hug webhook connector (moves to the Fine Japan tenant overlay in a later step)."""
from datetime import timedelta

from .assets import ingest_hug_webhook_consumer_asset

ASSETS = [ingest_hug_webhook_consumer_asset]

# SLA key (ingestion_sla.yaml) -> asset definition the checks attach to
CHECK_ASSET_DEFS = {
    "hug/ingest_hug_webhook_consumer_asset": ingest_hug_webhook_consumer_asset,
}

# Ingest assets pipeline_batch_nightly_job / pipeline_batch_fullrefresh_job run
NIGHTLY_ASSETS = []

# Morning digest rows: (short_name, sla key, recon sla key | None)
DIGEST_ASSETS = [
    ("hug", "hug/ingest_hug_webhook_consumer_asset", None),
]
# short_name -> (label, asset_type, unit)
DIGEST_DISPLAY: dict[str, tuple[str, str, str]] = {
    "hug": ("Hug webhook consumer", "cursor", "events"),
}

# Absolute max runtime per job; stuck_run_alerter terminates runs older than this
JOB_MAX_RUNTIME: dict[str, timedelta] = {
    "pipeline_hug_realtime_job": timedelta(minutes=45),
}

# dbt source_name -> {table name: asset key}; "*" matches any other table of the source
DBT_SOURCE_KEYS = {}

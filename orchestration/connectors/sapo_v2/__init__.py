"""Sapo v2 connector: batch, history-log, inventory and webhook-consumer ingestion."""
from datetime import timedelta

from dagster import AssetKey

from .assets import (
    ingest_sapo_v2_accounts_batch_asset,
    ingest_sapo_v2_customers_batch_asset,
    ingest_sapo_v2_history_log_asset,
    ingest_sapo_v2_inventory_transactions_asset,
    ingest_sapo_v2_orders_batch_asset,
    ingest_sapo_v2_product_daily_snapshot_asset,
    ingest_sapo_v2_products_batch_asset,
    ingest_sapo_v2_webhook_consumer_asset,
)

ASSETS = [
    ingest_sapo_v2_orders_batch_asset,
    ingest_sapo_v2_customers_batch_asset,
    ingest_sapo_v2_accounts_batch_asset,
    ingest_sapo_v2_products_batch_asset,
    ingest_sapo_v2_product_daily_snapshot_asset,
    ingest_sapo_v2_history_log_asset,
    ingest_sapo_v2_inventory_transactions_asset,
    ingest_sapo_v2_webhook_consumer_asset,
]

# SLA key (ingestion_sla.yaml) -> asset definition the checks attach to
CHECK_ASSET_DEFS = {
    "sapo/ingest_sapo_v2_webhook_consumer_asset": ingest_sapo_v2_webhook_consumer_asset,
    "sapo/ingest_sapo_v2_history_log_asset": ingest_sapo_v2_history_log_asset,
    "sapo/ingest_sapo_v2_orders_batch_asset": ingest_sapo_v2_orders_batch_asset,
    "sapo/ingest_sapo_v2_customers_batch_asset": ingest_sapo_v2_customers_batch_asset,
    "sapo/ingest_sapo_v2_accounts_batch_asset": ingest_sapo_v2_accounts_batch_asset,
    "sapo/ingest_sapo_v2_products_batch_asset": ingest_sapo_v2_products_batch_asset,
    "sapo/ingest_sapo_v2_product_daily_snapshot_asset": ingest_sapo_v2_product_daily_snapshot_asset,
}

# Ingest assets pipeline_batch_nightly_job / pipeline_batch_fullrefresh_job run
NIGHTLY_ASSETS = [
    ingest_sapo_v2_orders_batch_asset,
    ingest_sapo_v2_customers_batch_asset,
    ingest_sapo_v2_accounts_batch_asset,
    ingest_sapo_v2_products_batch_asset,
    ingest_sapo_v2_product_daily_snapshot_asset,
    ingest_sapo_v2_inventory_transactions_asset,
]

# Morning digest rows: (short_name, sla key, recon sla key | None)
DIGEST_ASSETS = [
    ("sapo_webhook",   "sapo/ingest_sapo_v2_webhook_consumer_asset",    None),
    ("sapo_history",   "sapo/ingest_sapo_v2_history_log_asset",         None),
    ("sapo_orders",    "sapo/ingest_sapo_v2_orders_batch_asset",        "recon/sapo_orders_daily"),
    ("sapo_customers", "sapo/ingest_sapo_v2_customers_batch_asset",     "recon/sapo_customers_daily"),
    ("sapo_products",  "sapo/ingest_sapo_v2_products_batch_asset",      None),
    ("sapo_product_snapshot", "sapo/ingest_sapo_v2_product_daily_snapshot_asset", None),
    ("sapo_accounts",  "sapo/ingest_sapo_v2_accounts_batch_asset",      None),
    ("sapo_inventory", "sapo/ingest_sapo_v2_inventory_transactions_asset", None),
]
# short_name -> (label, asset_type, unit)
DIGEST_DISPLAY: dict[str, tuple[str, str, str]] = {
    "sapo_webhook":   ("Sapo webhook (realtime events)",          "cursor",    "events"),
    "sapo_history":   ("Sapo lịch sử (audit log)",                "cursor",    "dòng"),
    "sapo_orders":    ("Sapo đơn hàng (batch)",                   "batch",     "đơn"),
    "sapo_customers": ("Sapo khách hàng",                         "batch",     "khách"),
    "sapo_products":  ("Sapo sản phẩm",                           "batch",     "sản phẩm"),
    "sapo_product_snapshot": ("Sapo ảnh chụp giá/tồn",            "batch",     "sản phẩm"),
    "sapo_accounts":  ("Sapo tài khoản",                          "batch",     "tài khoản"),
    "sapo_inventory": ("Sapo tồn kho (hourly)",                   "cursor",    "giao dịch"),
}

# Absolute max runtime per job; stuck_run_alerter terminates runs older than this
JOB_MAX_RUNTIME: dict[str, timedelta] = {
    "pipeline_sapo_v2_realtime_job": timedelta(minutes=45),
    "pipeline_sapo_v2_incremental_job": timedelta(minutes=45),
    "pipeline_sapo_v2_hourly_job": timedelta(minutes=45),
}

# dbt source_name -> {table name: asset key}; "*" matches any other table of the source
DBT_SOURCE_KEYS = {
    "sapo_v2_raw": {
        "order": AssetKey(["sapo", "ingest_sapo_v2_orders_batch_asset"]),
        "customer": AssetKey(["sapo", "ingest_sapo_v2_customers_batch_asset"]),
        "account": AssetKey(["sapo", "ingest_sapo_v2_accounts_batch_asset"]),
        "product": AssetKey(["sapo", "ingest_sapo_v2_products_batch_asset"]),
        "inventory_transaction_v2": AssetKey(["sapo", "ingest_sapo_v2_inventory_transactions_asset"]),
    },
}

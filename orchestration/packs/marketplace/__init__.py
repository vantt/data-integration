"""Marketplace pack: no Dagster code of its own. Its dbt models (transformation/models/packs/marketplace/,
Shopee order items, fees and adjustments) run inside the kernel's dbt assets; Shopee data comes
from the `shopee` connector. Listed in modules.yaml so the enabled packs match the dbt side."""
ASSETS = []
NIGHTLY_ASSETS = []
AFTER_SERVING_ASSETS = []

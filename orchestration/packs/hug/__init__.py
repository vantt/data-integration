"""HUG pack: no Dagster code of its own. Ingestion is the `hug` connector
(orchestration/connectors/hug/); the pack's dbt models (transformation/models/packs/hug/) run
inside the kernel's dbt assets. Listed in modules.yaml so the enabled packs match the dbt side."""
ASSETS = []
NIGHTLY_ASSETS = []
AFTER_SERVING_ASSETS = []

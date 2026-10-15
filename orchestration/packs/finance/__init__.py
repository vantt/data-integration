"""Finance pack: no Dagster code of its own. Its dbt models (transformation/models/packs/finance/)
run inside the kernel's dbt assets; the budget sheet sync that writes its tenant seeds is part
of the `sheets` connector. Listed in modules.yaml so the enabled packs match the dbt side."""
ASSETS = []
NIGHTLY_ASSETS = []
AFTER_SERVING_ASSETS = []

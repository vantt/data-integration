"""Facebook Messenger pack: no Dagster code of its own. Its dbt models
(transformation/models/packs/facebook_messenger/) are disabled in their own config until the
facebook_messenger connector has a Dagster asset. Listed in modules.yaml so the enabled packs
match the dbt side."""
ASSETS = []
NIGHTLY_ASSETS = []

"""Facebook Ads pack: no Dagster code of its own. Its dbt models (transformation/models/packs/facebook_ads/)
are disabled in their own config until the facebook_ads connector has a Dagster asset. Listed in
modules.yaml so the enabled packs match the dbt side."""
ASSETS = []
NIGHTLY_ASSETS = []
AFTER_SERVING_ASSETS = []

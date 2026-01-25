from dagster import AssetExecutionContext, AssetKey
from dagster_dbt import DbtCliResource, dbt_assets, DbtProject, DagsterDbtTranslator
import os
from typing import Any, Mapping

# Define the dbt project path
DBT_PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "transformation")
DBT_PROFILES_DIR = DBT_PROJECT_DIR # profiles.yml is in the same dir

# Define the dbt project resource
dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
    profiles_dir=DBT_PROFILES_DIR,
)

# dbt_project.prepare_if_dev() 
# Disabled to prevent "manifest.concurrent-update-lock" errors during Dagster code reload.
# We rely on `run_dagster.ps1` to pre-parse the manifest at startup.

class SapoDbtTranslator(DagsterDbtTranslator):
    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        # Default behavior for everything else
        return super().get_asset_key(dbt_resource_props)

    def get_upstream_asset_keys(self, dbt_resource_props: Mapping[str, Any]) -> set[AssetKey]:
        # We are manually managing dependencies via Jobs for now.
        # This keeps the assets decoupled in definition but coupled in execution.
        return super().get_upstream_asset_keys(dbt_resource_props)

@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=SapoDbtTranslator()
)
def sapo_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

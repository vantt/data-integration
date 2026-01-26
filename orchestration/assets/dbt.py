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
    # 1. Resolve Dynamic Export Path using shared Utility
    # script is in orchestration/assets/dbt.py, we need scripts/utils/version_manager
    # We added project root to sys.path in definitions.py, so we can import 'scripts.utils.version_manager'
    try:
        from scripts.utils import version_manager
    except ImportError as e:
        context.log.error(f"Failed to import version_manager: {e}")
        # Build a safe fallback path if import fails? No, better fail loud to fix.
        raise e

    # Base Export Dir (Same as in run_pipeline.ps1)
    # ProjectRoot/data_lake/export/marts
    # We can deduce project root relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__)) # orchestration/assets
    project_root = os.path.dirname(os.path.dirname(current_dir)) # orchestration/.. -> root
    export_base_dir = os.path.join(project_root, "data_lake", "export", "marts")

    context.log.info(f"Resolving new version in: {export_base_dir}")
    
    # Create + Cleanup (Keep 5)
    # Using 'create_and_cleanup' to match ps1 behavior
    try:
        # We call the python function directly instead of CLI for better control/logging
        version_manager.cleanup_old_versions(export_base_dir, keep=5)
        new_export_path = version_manager.get_new_version_path(export_base_dir)
        context.log.info(f"Target Export Path: {new_export_path}")
    except Exception as e:
        context.log.error(f"Version Manager failed: {e}")
        raise e

    # 2. Inject Environment Variable
    # dbt needs DBT_EXPORT_PATH to be set.
    # DbtCliResource.cli() doesn't accept 'env' arg, but it inherits os.environ.
    # We update os.environ for this process.
    
    os.environ["DBT_EXPORT_PATH"] = new_export_path

    yield from dbt.cli(["build"], context=context).stream()

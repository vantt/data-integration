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
        resource_type = dbt_resource_props.get("resource_type")
        source_name = dbt_resource_props.get("source_name")
        name = dbt_resource_props.get("name")

        if resource_type == "source" and source_name == "sapo_raw":
            if name == "order":
                print(f"[DEBUG] Mapping source sapo_raw.order -> sapo/sapo_orders_batch_asset")
                return AssetKey(["sapo", "sapo_orders_batch_asset"])
            elif name == "customer":
                print(f"[DEBUG] Mapping source sapo_raw.customer -> sapo/sapo_customers_batch_asset")
                return AssetKey(["sapo", "sapo_customers_batch_asset"])
            elif name == "account":
                print(f"[DEBUG] Mapping source sapo_raw.account -> sapo/sapo_accounts_batch_asset")
                return AssetKey(["sapo", "sapo_accounts_batch_asset"])
            elif name == "targets_raw":
                 return AssetKey(["sapo", "sapo_targets_asset"])

        return super().get_asset_key(dbt_resource_props)

    def get_upstream_asset_keys(self, dbt_resource_props: Mapping[str, Any]) -> set[AssetKey]:
        upstream_keys = super().get_upstream_asset_keys(dbt_resource_props)
        name = dbt_resource_props.get("name")

        # ----------------------------------------------------------------------
        # SYSTEM INSIGHT: HYBRID JOB RACE CONDITION FIX
        # ----------------------------------------------------------------------
        # Problem:
        # In `sapo_incremental_sync_job`, we run `sapo_history_log_asset` (Incremental) 
        # and `dbt_assets`. However, dbt models like `stg_sapo_orders` declare their 
        # source as `source('sapo_raw', 'order')`, which `get_asset_key` maps to 
        # `sapo_orders_batch_asset`.
        #
        # Since `sapo_orders_batch_asset` is NOT part of the incremental job, Dagster 
        # normally sees no active dependency for `stg_sapo_orders` within this job, 
        # causing dbt to start immediately in parallel with Ingestion.
        #
        # Solution:
        # We explicitly inject `sapo_history_log_asset` and `sapo_webhook_consumer_asset`
        # as upstream dependencies for the Staging Layer. This forces Dagster to wait 
        # for ALL ingestion tasks in the current job to finish before starting dbt.
        # ----------------------------------------------------------------------
        
        # Explicitly link dbt staging models to History Log and Webhook assets
        if name in [
            "stg_sapo_orders", "stg_sapo_customers", "stg_sapo_accounts",
            "src_sapo_orders", "src_sapo_customers", "src_sapo_accounts"
        ]:
            upstream_keys.add(AssetKey(["sapo", "sapo_history_log_asset"]))
            upstream_keys.add(AssetKey(["sapo", "sapo_webhook_consumer_asset"]))
            
        elif name == "stg_targets":
            upstream_keys.add(AssetKey(["sapo", "sapo_targets_asset"]))
        
        return upstream_keys

@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=SapoDbtTranslator(),
    op_tags={"dagster/concurrency_key": "duckdb_lock"}
)
def sapo_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    # Base Export Dir (Same as in run_pipeline.ps1)
    # ProjectRoot/data_lake/export/marts/rolling

    # Base Export Dir (Same as in run_pipeline.ps1)
    # ProjectRoot/data_lake/export/marts
    # We can deduce project root relative to this file
    current_dir = os.path.dirname(os.path.abspath(__file__)) # orchestration/assets
    project_root = os.path.dirname(os.path.dirname(current_dir)) # orchestration/.. -> root
    export_base_dir = os.path.join(project_root, "data_lake", "export", "marts", "rolling")
    
    # Ensure stable rolling directory exists
    if not os.path.exists(export_base_dir):
        os.makedirs(export_base_dir)

    # Pre-create subdirectories for all Marts to ensure COPY commands don't fail
    # Scan transformation/models/marts
    marts_dir = os.path.join(DBT_PROJECT_DIR, "models", "marts")
    if os.path.exists(marts_dir):
        for root, dirs, files in os.walk(marts_dir):
            for file in files:
                if file.endswith(".sql"):
                    # model name = filename without extension
                    model_name = os.path.splitext(file)[0]
                    # Create folder in export_base_dir
                    model_export_dir = os.path.join(export_base_dir, model_name)
                    os.makedirs(model_export_dir, exist_ok=True)
                    # context.log.info(f"Ensured export dir: {model_export_dir}")
        
    context.log.info(f"Target Export Path (Stable): {export_base_dir}")
    
    # 2. Inject Environment Variable
    # dbt needs DBT_EXPORT_PATH to be set.
    # We update os.environ for this process.
    os.environ["DBT_EXPORT_PATH"] = export_base_dir
    
    # No "cleanup_old_versions" here. Cleanup is now handled by the Serving Layer (GC).

    yield from dbt.cli(["build"], context=context).stream()

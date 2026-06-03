from dagster import AssetExecutionContext, AssetKey
from dagster_dbt import DbtCliResource, dbt_assets, DbtProject, DagsterDbtTranslator
import os
import threading
from typing import Any, Mapping

# Hard timeout for dbt subprocess. Prevents infinite hang when DuckDB checkpoint stalls.
# Normal runs complete in <2 min; 15 min is generous safety margin.
DBT_TIMEOUT_SEC = int(os.environ.get("DBT_TIMEOUT_SEC", "900"))

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

        if resource_type == "source":
            if source_name == "sapo_raw":
                if name == "order":
                    return AssetKey(["sapo", "sapo_orders_batch_asset"])
                elif name == "customer":
                    return AssetKey(["sapo", "sapo_customers_batch_asset"])
                elif name == "account":
                    return AssetKey(["sapo", "sapo_accounts_batch_asset"])
                elif name == "product":
                    return AssetKey(["sapo", "sapo_products_batch_asset"])
                elif name == "inventory_transaction_v2":
                    return AssetKey(["sapo", "sapo_inventory_transactions_v2_asset"])
                elif name == "targets_raw":
                    return AssetKey(["sheets", "sheets_targets_asset"])
                elif name == "marketing_spend_raw":
                    return AssetKey(["sheets", "sheets_marketing_spend_asset"])
                # Note: teams_raw and team_members_raw both come from sheets_team_config_asset
                # but cannot share the same asset key — dependency omitted by design.

            elif source_name == "misa_raw":
                # Single source table — maps cleanly to the file-drop ingestion asset
                return AssetKey(["misa_amis", "misa_sales_file_drop_asset"])

            elif source_name == "shopee_raw":
                # 4 source tables, each maps to its corresponding @multi_asset output.
                # Unique key per resource satisfies dagster-dbt's uniqueness requirement.
                return AssetKey(["shopee", name])

        return super().get_asset_key(dbt_resource_props)

@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=SapoDbtTranslator(),
    op_tags={"dagster/concurrency_key": "duckdb_lock"}
)
def sapo_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    # Base Export Dir (Same as in run_pipeline.ps1)
    # ProjectRoot/data_lake/export/marts/rolling

    # Rolling export dir — derive from DBT_EXPORT_PATH env var (set in .env.docker).
    # Do NOT hardcode /app/data_lake — Docker mounts data under /app/var/.
    dbt_export_path = os.environ.get("DBT_EXPORT_PATH", "/app/var/data_lake/export/marts")
    export_base_dir = os.path.join(dbt_export_path, "rolling")
    
    # Ensure stable rolling directory exists
    if not os.path.exists(export_base_dir):
        os.makedirs(export_base_dir)

    # Pre-create subdirectories for all models using get_rolling_location()
    # Scan both marts/ and intermediate/ (both contain external parquet models)
    for subdir in ["marts", "intermediate"]:
        scan_dir = os.path.join(DBT_PROJECT_DIR, "models", subdir)
        if os.path.exists(scan_dir):
            for root, dirs, files in os.walk(scan_dir):
                for file in files:
                    if file.endswith(".sql"):
                        model_name = os.path.splitext(file)[0]
                        model_export_dir = os.path.join(export_base_dir, model_name)
                        os.makedirs(model_export_dir, exist_ok=True)
        
    context.log.info(f"Target Export Path (Stable): {export_base_dir}")

    # DBT_EXPORT_PATH is already set via .env.docker (e.g. /app/var/data_lake/export/marts).
    # Do NOT overwrite it with export_base_dir (.../rolling) — the dbt macro
    # get_rolling_location() appends /rolling/ itself. Overwriting caused the macro
    # to need a fragile replace('/rolling','') hack.

    # Run dbt with watchdog timeout to prevent infinite hang on DuckDB checkpoint stall
    invocation = dbt.cli(["build"], context=context)

    def _kill_on_timeout():
        context.log.error(f"dbt subprocess exceeded {DBT_TIMEOUT_SEC}s timeout — killing")
        try:
            invocation.process.kill()
        except Exception as e:
            context.log.warning(f"Failed to kill dbt subprocess: {e}")

    watchdog = threading.Timer(DBT_TIMEOUT_SEC, _kill_on_timeout)
    watchdog.daemon = True
    watchdog.start()
    try:
        yield from invocation.stream()
    finally:
        watchdog.cancel()
        # Kill the subprocess on any exit path (normal, timeout, or external run
        # cancellation). Without this, external cancellation disarms the watchdog
        # via the finally block while leaving the dbt process alive — it then
        # holds the DuckDB lock and causes every subsequent run to hang.
        try:
            if invocation.process.poll() is None:
                invocation.process.kill()
        except Exception:
            pass

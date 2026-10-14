from dagster import AssetExecutionContext, AssetKey
from dagster_dbt import DbtCliResource, dbt_assets, DbtProject, DagsterDbtTranslator
import os
import subprocess
import sys
import threading
from typing import Any, Mapping

from orchestration.connectors import load_enabled

# Hard timeout for dbt subprocess. Prevents infinite hang when DuckDB checkpoint stalls.
# Normal runs complete in <2 min; 15 min is generous safety margin.
DBT_TIMEOUT_SEC = int(os.environ.get("DBT_TIMEOUT_SEC", "900"))

# Define the dbt project path
DBT_PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "transformation")
DBT_PROFILES_DIR = DBT_PROJECT_DIR # profiles.yml is in the same dir

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
REFRESH_ROLLING_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "provisioning", "refresh_rolling.py")

sys.path.insert(0, os.path.join(DBT_PROJECT_DIR, "scripts"))
from rolling_dirs import ensure_rolling_dirs, rolling_model_names  # noqa: E402

# Define the dbt project resource
dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
    profiles_dir=DBT_PROFILES_DIR,
)

# dbt_project.prepare_if_dev() 
# Disabled to prevent "manifest.concurrent-update-lock" errors during Dagster code reload.
# We rely on `run_dagster.ps1` to pre-parse the manifest at startup.

class SapoDbtTranslator(DagsterDbtTranslator):
    """Keeps default dbt asset keys except for sources a connector ingests itself.

    Those map to the connector's ingest asset: DBT_SOURCE_KEYS of every connector enabled
    in config/modules.yaml, as {source_name: {table name: AssetKey}} ("*" = any other table).
    """

    def __init__(self):
        super().__init__()
        self._source_keys: dict[str, dict[str, AssetKey]] = {}
        for connector in load_enabled():
            for source_name, tables in connector.DBT_SOURCE_KEYS.items():
                self._source_keys.setdefault(source_name, {}).update(tables)

    def get_asset_key(self, dbt_resource_props: Mapping[str, Any]) -> AssetKey:
        if dbt_resource_props.get("resource_type") == "source":
            tables = self._source_keys.get(dbt_resource_props.get("source_name"), {})
            name = dbt_resource_props.get("name")
            key = tables.get(name, tables.get("*"))
            if key is not None:
                return key
        return super().get_asset_key(dbt_resource_props)

def _gc_rolling_parquet(context: AssetExecutionContext) -> None:
    # serving_asset also calls refresh_rolling.py but only when triggered by the
    # scheduled pipeline. Running GC here guarantees cleanup on every dbt
    # materialization, including manual and selective runs.
    if not os.path.exists(REFRESH_ROLLING_SCRIPT):
        context.log.warning(f"refresh_rolling.py not found at {REFRESH_ROLLING_SCRIPT} — skipping GC")
        return
    try:
        result = subprocess.run(
            [sys.executable, REFRESH_ROLLING_SCRIPT],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.stdout:
            context.log.info(f"rolling-gc: {result.stdout.strip()}")
        if result.returncode != 0:
            context.log.warning(f"rolling-gc exited {result.returncode}: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        context.log.warning("rolling-gc timed out after 60s — skipped")
    except Exception as e:
        context.log.warning(f"rolling-gc error: {e}")


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
    context.log.info(f"Target Export Path (Stable): {export_base_dir}")

    # DBT_EXPORT_PATH is already set via .env.docker (e.g. /app/var/data_lake/export/marts).
    # Do NOT overwrite it with export_base_dir (.../rolling) — the dbt macro
    # get_rolling_location() appends /rolling/ itself. Overwriting caused the macro
    # to need a fragile replace('/rolling','') hack.

    # Regenerate manifest before build to prevent stale-manifest KeyError.
    # Manifest is pre-parsed at container start; schema.yml changes create new test node
    # IDs that don't exist in the startup manifest, causing dagster-dbt event streamer
    # to hit manifest["nodes"][unique_id] → KeyError. Parsing here ensures the manifest
    # on disk is always fresh relative to the current schema before dbt build runs.
    # Note: context is intentionally omitted — dbt parse does not accept --select,
    # and passing context causes dagster-dbt to append selection args, breaking the command.
    #
    # Concurrency note: parse runs BEFORE yield-from (i.e., before the op-level
    # duckdb_lock slot is formally acquired by Dagster's slot machinery). However,
    # parse only writes manifest.json / manifest.concurrent-update-lock — it does
    # NOT open DuckDB. Race between two simultaneous parses is benign (last writer
    # wins on manifest.json; run_dagster.ps1 cleans up stale .concurrent-update-lock
    # at startup). The authoritative guard against two dbt runs overlapping is the
    # dbt_rw=1 tag-concurrency limit in dagster.yaml — only one run with
    # concurrency_group=dbt_rw is dequeued at a time, so concurrent parse is not
    # possible in normal operation.
    dbt.cli(["parse"]).wait()

    # Pre-create rolling/<model>/ for every external model using get_rolling_location()
    # (DuckDB COPY needs the parent directory). Done after parse so models added since the
    # container started are included; the list comes from the manifest, not folder names.
    created = ensure_rolling_dirs(dbt_export_path, rolling_model_names(DBT_PROJECT_DIR))
    if created:
        context.log.info(f"Created {len(created)} rolling directories: {created}")

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
        _gc_rolling_parquet(context)

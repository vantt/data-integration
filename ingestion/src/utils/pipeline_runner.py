import os
import sys
import argparse
import dlt
from typing import Callable, Optional

def setup_dlt_env(dataset_name: str = "sapo_raw"):
    """
    Sets up the standard environment variables for file-based dlt pipelines.
    """
    # os.environ["DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT"] = "parquet" # Moved to config.toml
    # Unified layout for segregation by source - Moved to config.toml
    # os.environ["DESTINATION__FILESYSTEM__LAYOUT"] = "{table_name}/ingest_method={ingest_method}/year={year}/month={month}/{file_id}.{ext}"
    # os.environ["DESTINATION__FILESYSTEM__EXTRA_PLACEHOLDERS"] = '{"ingest_method": "text", "year": "text", "month": "text"}'

def run_pipeline(
    pipeline_name: str,
    dataset_name: str,
    source_factory: Callable,
    source_args: dict = {},
    loader_file_format: str = "parquet",
    argv: Optional[list] = None,
    **pipeline_kwargs
):
    """
    Standardized entry point for running a dlt pipeline.
    
    Args:
        pipeline_name: Name of the dlt pipeline.
        dataset_name: Target dataset name (default 'sapo_raw').
        source_factory: The dlt source function (e.g., sapo_orders_source).
        source_args: Arguments to pass to the source function.
        loader_file_format: Format for output files (default 'parquet').
        argv: Optional list of arguments to parse (overrides sys.argv).
        **pipeline_kwargs: Additional args for dlt.pipeline().
    """
    
    # 1. Parse CLI arguments
    parser = argparse.ArgumentParser(description=f"Run {pipeline_name} pipeline.")
    parser.add_argument("--full-refresh", action="store_true", help="Drop the pipeline state and load fresh.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of resources/pages (if supported by source).")
    parser.add_argument("--dev", action="store_true", help="Run in dev mode (appends _dev to dataset).")
    
    # Allow unknown args to pass through if needed, or strict parsing
    args, unknown = parser.parse_known_args(argv)
    
    # 2. Setup Environment
    final_dataset_name = dataset_name + "_dev" if args.dev else dataset_name
    setup_dlt_env(final_dataset_name)
    
    # 3. Handle Full Refresh — reset dlt pipeline STATE before initialization.
    # Strategy: use refresh="drop_sources" in pipeline.run() to drop both destination-side state
    # (incremental cursors stored in _dlt_pipeline_state) AND local state dir. This is necessary
    # because dlt restores state FROM the destination on startup, so clearing only local state
    # is insufficient — the cursor would be restored from _dlt_pipeline_state in the data lake.
    # Also clear local state dir to avoid stale schema cache that might lock file format.
    # NOTE: dlt stores local state in get_dlt_pipelines_dir() (default: /var/dlt/pipelines),
    # NOT in .dlt/pipelines/ (which is the config directory, not the runtime state dir).
    refresh_mode = None
    if args.full_refresh:
        import shutil
        from dlt.common.pipeline import get_dlt_pipelines_dir
        state_dir = os.path.join(get_dlt_pipelines_dir(), pipeline_name)
        if os.path.exists(state_dir):
            shutil.rmtree(state_dir)
            print(f"[Pipeline Runner] --full-refresh: cleared local state dir ({state_dir})")
        else:
            print(f"[Pipeline Runner] --full-refresh: no local state dir at {state_dir}, proceeding fresh.")
        refresh_mode = "drop_sources"
        source_args["full_refresh"] = True
        print(f"[Pipeline Runner] --full-refresh: will use refresh='drop_sources' to reset destination state")

    # 4. Initialize Pipeline (creates fresh state if dir was deleted by full-refresh)
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination="filesystem",
        dataset_name=final_dataset_name,
        **pipeline_kwargs
    )

    print(f"[Pipeline Runner] Initialized pipeline: {pipeline_name}")
    print(f"[Pipeline Runner] Dataset: {final_dataset_name}")

    # 5. Run Pipeline
    import time
    max_retries = 3
    run_kwargs = {"loader_file_format": loader_file_format}
    if refresh_mode:
        run_kwargs["refresh"] = refresh_mode
    for attempt in range(max_retries):
        try:
            source = source_factory(**source_args)
            info = pipeline.run(source, **run_kwargs)
            print(info)
            return info
        except Exception as e:
            print(f"[Pipeline Runner] Error running pipeline (Attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Waiting {wait_time}s before retrying...")
                time.sleep(wait_time)
            else:
                print("[Pipeline Runner] Max retries reached. Pipeline failed.")
                # We raise the error instead of sys.exit so Dagster can handle it as a failure 
                # or upper layers can catch it.
                raise e

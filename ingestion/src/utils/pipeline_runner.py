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
    
    # 3. Initialize Pipeline
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination="filesystem",
        dataset_name=final_dataset_name,
        **pipeline_kwargs
    )
    
    print(f"[Pipeline Runner] Initialized pipeline: {pipeline_name}")
    print(f"[Pipeline Runner] Dataset: {final_dataset_name}")
    
    # 4. Handle Full Refresh — SAFE: only reset incremental cursor, NEVER drop data.
    # Data is append-only; deduplication is handled by the transformation layer (dbt).
    if args.full_refresh:
        print("[Pipeline Runner] --full-refresh: resetting incremental cursor (data preserved).")
        source_args["full_refresh"] = True

    # 5. Run Pipeline
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            source = source_factory(**source_args)
            info = pipeline.run(source)
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

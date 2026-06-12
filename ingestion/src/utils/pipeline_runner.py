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
    parser.add_argument("--full-refresh", action="store_true", help="[DESTRUCTIVE] Drop all destination parquet files and reload. Requires --force.")
    parser.add_argument("--force", action="store_true", help="Required with --full-refresh to confirm destructive drop.")
    parser.add_argument("--reset-cursor", action="store_true", help="Reset incremental cursor and re-fetch from Sapo. SAFE: appends to existing parquet, never deletes.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of resources/pages (if supported by source).")
    parser.add_argument("--dev", action="store_true", help="Run in dev mode (appends _dev to dataset).")

    # Allow unknown args to pass through if needed, or strict parsing
    args, unknown = parser.parse_known_args(argv)

    # 2. Setup Environment
    final_dataset_name = dataset_name + "_dev" if args.dev else dataset_name
    setup_dlt_env(final_dataset_name)

    # 3a. GUARDRAIL: --full-refresh without --force is blocked.
    # --full-refresh calls refresh="drop_sources" which deletes ALL parquet files in the table
    # (including history_log and text partitions that cannot be re-fetched from Sapo API).
    # Always require --force as explicit confirmation of this destructive intent.
    if args.full_refresh and not args.force:
        print()
        print("=" * 70)
        print("  BLOCKED: --full-refresh requires --force to proceed.")
        print()
        print("  --full-refresh will DELETE all parquet files for this pipeline,")
        print("  including history_log and text partitions that CANNOT be")
        print("  re-fetched from the Sapo API once deleted.")
        print()
        print("  To safely re-ingest without data loss, use instead:")
        print(f"    --reset-cursor   (clears cursor only, appends to existing parquet)")
        print()
        print("  To confirm destructive drop (you know what you're doing):")
        print(f"    --full-refresh --force")
        print("=" * 70)
        print()
        sys.exit(1)

    # 3b. Handle --reset-cursor — clears incremental cursor, re-fetches from beginning.
    # SAFE: write_disposition="append" means dlt only adds new parquet files.
    # Old parquet files (history_log, text, prior batch_sync) are untouched.
    #
    # IMPLEMENTATION NOTE: Do NOT use refresh="drop_pipeline_state" — that mode also
    # triggers a DROP TABLE which deletes ALL parquet files in the table directory,
    # including other ingest_method partitions (history_log, text) that must be preserved.
    #
    # Instead, manually delete the destination-stored state JSONL files for this pipeline
    # before creating the pipeline object. This clears the cursor without touching data.
    refresh_mode = None
    if args.reset_cursor:
        import shutil
        import glob as _glob
        from dlt.common.pipeline import get_dlt_pipelines_dir
        # 1. Clear local state dir
        state_dir = os.path.join(get_dlt_pipelines_dir(), pipeline_name)
        if os.path.exists(state_dir):
            shutil.rmtree(state_dir)
            print(f"[Pipeline Runner] --reset-cursor: cleared local state dir ({state_dir})")
        else:
            print(f"[Pipeline Runner] --reset-cursor: no local state dir found.")
        # 2. Delete destination-stored state JSONL files for this pipeline.
        #    Pattern: {data_lake}/_dlt_pipeline_state/{pipeline_name}__*.jsonl
        #    This prevents dlt from restoring the old cursor on startup.
        data_lake_root = os.environ.get("DESTINATION__FILESYSTEM__BUCKET_URL", "")
        if data_lake_root:
            state_pattern = os.path.join(data_lake_root.replace("file://", ""), "_dlt_pipeline_state", f"{pipeline_name}__*.jsonl")
            state_files = _glob.glob(state_pattern)
            for sf in state_files:
                os.remove(sf)
            if state_files:
                print(f"[Pipeline Runner] --reset-cursor: deleted {len(state_files)} destination state file(s) for {pipeline_name}")
            else:
                print(f"[Pipeline Runner] --reset-cursor: no destination state files found for {pipeline_name}")
        else:
            print(f"[Pipeline Runner] --reset-cursor: DESTINATION__FILESYSTEM__BUCKET_URL not set, skipping destination state cleanup")
        source_args["full_refresh"] = True  # tells source to ignore cursor (last_value = None)
        print(f"[Pipeline Runner] --reset-cursor: cursor cleared. Will append from beginning, parquet untouched.")

    # 3c. Handle --full-refresh --force — destructive drop + full reload.
    # Strategy: use refresh="drop_sources" to drop destination-side state AND parquet files,
    # then clear local state dir to avoid stale schema cache.
    # NOTE: dlt restores state FROM the destination on startup, so clearing only local state
    # is insufficient — the cursor would be restored from _dlt_pipeline_state in the data lake.
    if args.full_refresh and args.force:
        import shutil
        from dlt.common.pipeline import get_dlt_pipelines_dir
        state_dir = os.path.join(get_dlt_pipelines_dir(), pipeline_name)
        if os.path.exists(state_dir):
            shutil.rmtree(state_dir)
            print(f"[Pipeline Runner] --full-refresh --force: cleared local state dir ({state_dir})")
        else:
            print(f"[Pipeline Runner] --full-refresh --force: no local state dir at {state_dir}, proceeding fresh.")
        refresh_mode = "drop_sources"
        source_args["full_refresh"] = True
        print(f"[Pipeline Runner] --full-refresh --force: will use refresh='drop_sources' to drop destination parquet + state")

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

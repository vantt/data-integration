import sys
import os
os.environ["DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT"] = "parquet"
os.environ["DESTINATION__FILESYSTEM__LAYOUT"] = "{table_name}/ingest_method={ingest_method}/year={year}/month={month}/{file_id}.{ext}"
os.environ["DESTINATION__FILESYSTEM__EXTRA_PLACEHOLDERS"] = '{"ingest_method": "text", "year": "text", "month": "text"}'

# Add src to path so imports work
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import dlt
from sapo.history_log import sapo_history_log_source

def run():
    # Initialize pipeline
    pipeline = dlt.pipeline(
        pipeline_name="sapo_history_log_pipeline",
        destination="filesystem",
        dataset_name="sapo_raw"
    )
    
    # Configure source
    # API limit is 20 per request for this endpoint
    source = sapo_history_log_source(
        page_size=100, 
        min_overlap_items=500,
        #limit=10,
        debug=True
    )
    
    # Run pipeline
    print("Running Sapo History Log Pipeline...")
    
    # If users want to re-load all history, they can uncomment valid full_refresh or drop state manually.
    # For now, we keep default incremental behavior.
    # To force full refresh: pipeline.drop() before running.
    
    #pipeline.drop() # Uncomment to reset state and load everything from scratch
    
    # Using default write_disposition (append) to allow incremental loading.
    load_info = pipeline.run(source, loader_file_format="parquet")
    
    print(load_info)
    return load_info


if __name__ == "__main__":
    run()

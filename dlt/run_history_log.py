import sys
import os

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
        min_overlap_items=500
    )
    
    # Run pipeline
    print("Running Sapo History Log Pipeline...")
    
    # If users want to re-load all history, they can uncomment valid full_refresh or drop state manually.
    # For now, we keep default incremental behavior.
    # To force full refresh: pipeline.drop() before running.
    
    #pipeline.drop() # Uncomment to reset state and load everything from scratch
    
    load_info = pipeline.run(source)
    
    print(load_info)

if __name__ == "__main__":
    run()

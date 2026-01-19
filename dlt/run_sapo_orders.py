import dlt
import sys
import os
os.environ["DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT"] = "parquet"

# Add src to path so imports work
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sapo import sapo_source

def run():
    """
    Run the Sapo orders pipeline.
    """
    # Configure safe layout
    from dlt.destinations import filesystem
    import os
    abs_path = os.path.abspath("data_lake")
    
    dest = filesystem(
        destination_name="filesystem",
        bucket_url=f"file:///{abs_path}"
    )
    
    pipeline = dlt.pipeline(
        pipeline_name="sapo_orders",
        dataset_name="sapo_data"
    )

    # The source returns the "orders" resource
    source = sapo_source(max_pages=1000)

    # Run the pipeline
    load_info = pipeline.run(source, destination=dest, loader_file_format="parquet")
    
    print(load_info)

if __name__ == "__main__":
    run()

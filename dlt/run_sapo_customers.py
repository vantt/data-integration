import dlt
import sys
import os
os.environ["DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT"] = "parquet"

# Add src to path so imports work
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sapo.customers import sapo_customers_source

def run():
    """
    Run the Sapo customers pipeline.
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
        pipeline_name="sapo_customers",
        dataset_name="sapo_customers"
    )

    # The source returns the "customers" resource
    source = sapo_customers_source(max_pages=1000)

    # Run the pipeline
    load_info = pipeline.run(source, destination=dest, loader_file_format="parquet")
    
    print(load_info)

if __name__ == "__main__":
    run()

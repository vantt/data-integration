import dlt
import sys
import os
os.environ["DESTINATION__FILESYSTEM__LOADER_FILE_FORMAT"] = "parquet"
os.environ["DESTINATION__FILESYSTEM__LAYOUT"] = "{table_name}/ingest_method={ingest_method}/year={year}/month={month}/{file_id}.{ext}"
os.environ["DESTINATION__FILESYSTEM__EXTRA_PLACEHOLDERS"] = '{"ingest_method": "text", "year": "text", "month": "text"}'

# Add src to path so imports work
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from sapo.orders import sapo_orders_source

def run():
    """
    Run the Sapo orders pipeline.
    """
    pipeline = dlt.pipeline(
        pipeline_name="sapo_orders_batch",
        destination="filesystem",
        dataset_name="sapo_raw"
    )

    # The source returns the "orders" resource
    source = sapo_orders_source(max_pages=1000)

    # Run the pipeline
    load_info = pipeline.run(source, loader_file_format="parquet")
    
    print(load_info)
    return load_info

if __name__ == "__main__":
    run()

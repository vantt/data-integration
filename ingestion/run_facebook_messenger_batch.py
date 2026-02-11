import dlt
import os
import json

try:
    from dlt.sources.facebook_messenger import facebook_messenger_source
except ImportError:
    # Fallback/Placeholder if source is not yet initialized via dlt init
    print("Please run `dlt init facebook_messenger duckdb` to fetch the source implementation first.")
    facebook_messenger_source = None

def run_pipeline():
    """
    Runs the Facebook Messenger ingestion pipeline for multiple pages.
    Configuration is loaded from JSON environment variable.
    """
    if not facebook_messenger_source:
        return

    # Configuration loaded from environment variables
    # Format: [{"page_id": "...", "page_name": "...", "access_token": "..."}, ...]
    pages_config_str = os.environ.get("SOURCES__FACEBOOK_MESSENGER__PAGES_CONFIG")
    
    if not pages_config_str:
        print("Missing required environment variable: SOURCES__FACEBOOK_MESSENGER__PAGES_CONFIG (JSON list of pages)")
        # Backward compatibility check for single token
        single_token = os.environ.get("SOURCES__FACEBOOK_MESSENGER__PAGE_ACCESS_TOKEN")
        if single_token:
             print("Falling back to single token legacy config.")
             pages_config = [{"page_id": "default", "page_name": "Default Page", "access_token": single_token}]
        else:
            return
    else:
        try:
            pages_config = json.loads(pages_config_str)
        except json.JSONDecodeError:
            print("Error decoding SOURCES__FACEBOOK_MESSENGER__PAGES_CONFIG. Ensure it is valid JSON.")
            return

    pipeline = dlt.pipeline(
        pipeline_name="facebook_messenger_pipeline",
        destination="duckdb", # Change to postgres/bigquery as needed
        dataset_name="raw_messenger_data"
    )

    for page in pages_config:
        page_name = page.get("page_name", "Unknown Page")
        print(f"Starting load for Page: {page_name} (ID: {page.get('page_id')})")
        
        token = page.get("access_token")
        if not token:
            print(f"Skipping page {page_name}: No access_token found.")
            continue

        # Configure source with Page Access Token
        source = facebook_messenger_source(
            page_access_token=token
        )
        
        # Run pipeline
        # dlt will merge data into the same tables. 
        # Ideally, ensure source adds 'page_id' or similar discriminator if not present.
        load_info = pipeline.run(source)
        print(f"Load info for {page_name}:")
        print(load_info)

if __name__ == "__main__":
    run_pipeline()

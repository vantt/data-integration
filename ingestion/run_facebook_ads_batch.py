import dlt
from dlt.sources.facebook_ads import facebook_ads_source

import os

# Configuration: List of Ad Account IDs to ingest
# Fetched from environment variable SOURCES__FACEBOOK_ADS__ACCOUNT_IDS (comma separated)
# Example: SOURCES__FACEBOOK_ADS__ACCOUNT_IDS="act_2209123456789,act_88888888"
accounts_env = os.environ.get("SOURCES__FACEBOOK_ADS__ACCOUNT_IDS", "")
AD_ACCOUNT_IDS = [acc.strip() for acc in accounts_env.split(",") if acc.strip()]

def load_facebook_ads():
    """
    Loads Facebook Ads data for multiple accounts into a single dataset.
    """
    if not AD_ACCOUNT_IDS:
        print("No Ad Accounts configured in SOURCES__FACEBOOK_ADS__ACCOUNT_IDS environment variable.")
        return

    # Initialize the pipeline
    # Data will be loaded into the 'facebook_ads' dataset (schema)
    pipeline = dlt.pipeline(
        pipeline_name="facebook_ads_batch_pipeline",
        destination="duckdb", # Change to 'postgres', 'bigquery', etc. as needed
        dataset_name="facebook_ads"
    )

    for account_id in AD_ACCOUNT_IDS:
        print(f"Starting load for Ad Account: {account_id}")
        
        # Initialize the source for the specific account
        # We include 'insights' to get performance metrics
        ads_source = facebook_ads_source(
            account_id=account_id,
            chunk_size=1000
        )
        
        # Run the pipeline
        # dlt handles schema evolution and data merging automatically
        load_info = pipeline.run(ads_source)
        print(f"Load info for {account_id}:")
        print(load_info)

if __name__ == "__main__":
    load_facebook_ads()

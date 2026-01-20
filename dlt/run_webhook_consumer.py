"""
Script to run the Sapo Webhook Consumer.
Polls Cloudflare D1 for webhooks and loads them into Sapo Data Lake.
"""

import dlt
import os
import time
from dlt.common.pipeline import LoadInfo
from src.sapo.webhook_consumer import sapo_webhook_source

def run():
    # Configuration
    # Ensure WORKER_URL is set in .dlt/secrets.toml or env var
    # Example: WORKER_URL = "https://my-worker.my-subdomain.workers.dev"
    worker_url = os.getenv("WORKER_URL") 
    
    if not worker_url:
        # Fallback for local testing or raise error
        print("⚠️  WORKER_URL environment variable not set. Checking dlt config/secrets...")
        # dlt will inject secrets into the source function content if defined in secrets.toml
        # But here we pass it explicitly. 
        # For better dlt integration, we could rely on dlt.secrets.value
        try:
             worker_url = dlt.secrets["sources.sapo_webhook_source.worker_url"]
        except (KeyError, dlt.common.configuration.specs.config_providers.ConfigProviderException):
             pass
        
    if not worker_url:
        print("❌ Error: WORKER_URL is missing. Please set it in .env or .dlt/secrets.toml")
        return

    poll_limit = int(os.getenv("POLL_LIMIT", "100"))
    sleep_interval = int(os.getenv("SLEEP_INTERVAL", "10"))
    
    # Initialize Pipeline
    # dataset_name="sapo_raw" to write into the unified data lake
    pipeline = dlt.pipeline(
        pipeline_name="sapo_webhook_consumer",
        destination="filesystem",
        dataset_name="sapo_raw"
    )

    print(f"🚀 Starting Webhook Consumer Pipeline...")
    print(f"   Worker URL: {worker_url}")
    print(f"   Target Dataset: sapo_raw")
    
    while True:
        try:
            # Run the pipeline
            # The source yields data (and ACKs internally currently)
            # If no data is yielded, pipeline.run returns None or empty LoadInfo
            
            # Note: We pass worker_url here. 
            source = sapo_webhook_source(worker_url=worker_url, poll_limit=poll_limit)
            
            load_info = pipeline.run(source, loader_file_format="parquet")
            
            if load_info:
                print(load_info)
            else:
                print(f"💤 No new data. Sleeping {sleep_interval}s...")
                time.sleep(sleep_interval)
                
        except KeyboardInterrupt:
            print("🛑 Consumer stopped by user.")
            break
        except Exception as e:
            print(f"❌ Pipeline Error: {e}")
            time.sleep(sleep_interval)

if __name__ == "__main__":
    run()
